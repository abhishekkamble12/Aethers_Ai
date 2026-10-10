"""
Circular-to-Rules Validator & Hostile Input Refusal Module
Code validates every candidate:
1. Schema & typed enum validation
2. Verbatim quote substring check against source circular text
3. Refusal moment: Rejects hallucinated quotes and prompt injection attacks
"""

from typing import Dict, Any, List, Tuple

VALID_STAGES = {"I", "II", "III", "IV"}
VALID_CLASS_BANDS = {"primary", "middle", "secondary", "senior_secondary", "all"}
VALID_ACTIONS = {"allowed", "advisory", "restricted", "banned"}

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "system override",
    "disregard all prior",
    "ignore all safety",
    "approve outdoor activities immediately"
]

class ValidationError(Exception):
    pass

class HostileInstructionDetected(ValidationError):
    pass

class InventedQuoteError(ValidationError):
    pass


def sanitize_and_check_hostile_input(circular_text: str):
    """
    Scans untrusted circular text for malicious prompt injection attempts.
    Visibly raises HostileInstructionDetected if detected.
    """
    lower_text = circular_text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower_text:
            raise HostileInstructionDetected(
                f"SYSTEM VISIBLY REFUSED: Prompt injection attempt detected in circular text: '{pattern}'"
            )


def validate_candidate_rule(
    rule: Dict[str, Any],
    circular_text: str,
    target_jurisdiction: str = "Delhi"
) -> Tuple[bool, List[str]]:
    """
    Validates a single candidate rule extracted by the LLM.
    Returns (is_valid, error_messages).
    """
    errors = []

    # 1. Rule ID check
    if not rule.get("rule_id"):
        errors.append("Missing 'rule_id'")

    # 2. Stage enum check
    cond = rule.get("condition", {})
    min_stage = cond.get("stage_at_least")
    if min_stage and min_stage not in VALID_STAGES:
        errors.append(f"Invalid stage '{min_stage}'. Must be one of: {VALID_STAGES}")

    # 3. Class band enum check
    class_bands = rule.get("class_band", [])
    for cb in class_bands:
        if cb not in VALID_CLASS_BANDS:
            errors.append(f"Invalid class band '{cb}'. Must be one of: {VALID_CLASS_BANDS}")

    # 4. Action enum check
    action = rule.get("action", {})
    for act_key in ["outdoor_sports", "outdoor_pt"]:
        val = action.get(act_key)
        if val and val not in VALID_ACTIONS:
            errors.append(f"Invalid action '{val}' for '{act_key}'. Must be one of: {VALID_ACTIONS}")

    # 5. CRITICAL: Verbatim quote substring check
    source_quote = rule.get("source_quote", "").strip()
    if not source_quote:
        errors.append("Rule must provide a verbatim 'source_quote'.")
    else:
        # Check if source_quote is an exact substring in circular_text (ignoring minor whitespace normalize)
        clean_quote = " ".join(source_quote.split())
        clean_circ = " ".join(circular_text.split())
        if clean_quote not in clean_circ:
            errors.append(
                f"REFUSED (Invented/Hallucinated Quote): Quote '{source_quote}' was NOT found in source circular text!"
            )

    return (len(errors) == 0, errors)


def validate_ruleset_candidates(
    candidate_rules: List[Dict[str, Any]],
    circular_text: str,
    target_jurisdiction: str = "Delhi"
) -> Dict[str, Any]:
    """
    Validates an entire batch of candidate rules extracted from a circular.
    Returns:
    {
        "status": "approved" | "refused",
        "valid_rules": [...],
        "rejected_rules": [{"rule": ..., "errors": [...]}],
        "refusal_reason": None | str
    }
    """
    # First check for hostile prompt injection in circular
    try:
        sanitize_and_check_hostile_input(circular_text)
    except HostileInstructionDetected as e:
        return {
            "status": "refused",
            "refusal_type": "hostile_injection",
            "refusal_reason": str(e),
            "valid_rules": [],
            "rejected_rules": [{"rule": r, "errors": [str(e)]} for r in candidate_rules]
        }

    valid_rules = []
    rejected_rules = []

    for rule in candidate_rules:
        is_valid, errors = validate_candidate_rule(rule, circular_text, target_jurisdiction)
        if is_valid:
            valid_rules.append(rule)
        else:
            rejected_rules.append({
                "rule": rule,
                "errors": errors
            })

    status = "approved" if (len(rejected_rules) == 0 and len(valid_rules) > 0) else "partial_or_refused"
    if len(rejected_rules) > 0 and len(valid_rules) == 0:
        status = "refused"

    return {
        "status": status,
        "refusal_type": "quote_mismatch" if any("Invented/Hallucinated" in str(e) for r in rejected_rules for e in r["errors"]) else None,
        "valid_rules": valid_rules,
        "rejected_rules": rejected_rules,
        "refusal_reason": rejected_rules[0]["errors"][0] if rejected_rules else None
    }
