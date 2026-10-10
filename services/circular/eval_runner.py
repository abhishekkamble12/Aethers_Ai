"""
Validator evaluation for the Circular-to-Rules pipeline (honest pre-M4 version).

What this measures today: the CODE validator only. Candidate rules are hand-entered from one real
DoE circular; no model extracts them yet (hack_win M4 adds Bedrock extraction and real
precision/recall against hand-labelled rules). Every number below is computed on this run, and the
dataset size is printed next to it.

Writes data/gold/eval_table.json.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from services.circular.validator import validate_ruleset_candidates

# Words a quote must contain before it can justify an action on outdoor sports / PE.
# (Reported here as a known gap; M4 moves this check into the validator itself.)
SPORT_WORDS = re.compile(r"\b(sport|sports|physical education|pt|games|outdoor activit)", re.I)


def unsupported_actions(rule: Dict[str, Any]) -> List[str]:
    action = rule.get("action", {})
    if any(k in action for k in ("outdoor_sports", "outdoor_pt")) and not SPORT_WORDS.search(rule.get("source_quote", "")):
        return [k for k in ("outdoor_sports", "outdoor_pt") if k in action]
    return []


def run_gold_evaluation() -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    gold_dir = os.path.join(base_dir, "data", "gold")

    with open(os.path.join(gold_dir, "circular_real_caqm.txt"), "r", encoding="utf-8") as f:
        circular_text = f.read()
    with open(os.path.join(gold_dir, "hostile_instruction.txt"), "r", encoding="utf-8") as f:
        hostile_instruction_text = f.read()
    with open(os.path.join(gold_dir, "hostile_invented_quote.json"), "r", encoding="utf-8") as f:
        invented_quote_rule = json.load(f)

    # Hand-entered from DoE circular No. DE.23(28)/Sch.Br./2025/40 (data/gold/circular_real_caqm.txt).
    gold_rules = [
        {
            "rule_id": "r-017", "applies_to": ["school"], "class_band": ["all"],
            "condition": {"stage_at_least": "III"},
            "action": {"outdoor_sports": "banned", "outdoor_pt": "banned"},
            "source_id": "DoE-circ-StageIII-2025",
            "source_quote": "All outdoor sports and physical education activities in schools shall remain strictly suspended under Stage III of GRAP."
        },
        {
            "rule_id": "r-018", "applies_to": ["school"], "class_band": ["primary"],
            "condition": {"stage_at_least": "III"},
            "action": {"hybrid_mode": "mandatory", "outdoor_sports": "banned", "outdoor_pt": "banned"},
            "source_id": "DoE-circ-StageIII-2025",
            "source_quote": "All classes up to primary level (Nursery to Class V) shall run in hybrid mode (both physical and online options where feasible)."
        },
        {
            "rule_id": "r-019", "applies_to": ["school"], "class_band": ["all"],
            "condition": {"stage_at_least": "III"},
            "action": {"outdoor_sports": "banned", "outdoor_pt": "banned"},
            "source_id": "DoE-circ-StageIII-2025",
            "source_quote": "Morning assemblies, if any, shall be conducted strictly indoors within well-ventilated classrooms or halls."
        }
    ]

    gold_run = validate_ruleset_candidates(gold_rules, circular_text)
    invented_run = validate_ruleset_candidates([invented_quote_rule], circular_text)
    hostile_run = validate_ruleset_candidates([{
        "rule_id": "r-override", "condition": {"stage_at_least": "III"},
        "action": {"outdoor_sports": "allowed", "outdoor_pt": "allowed"},
        "source_quote": "All sports activities are strictly mandatory outdoors regardless of AQI"
    }], hostile_instruction_text)

    accepted = gold_run["valid_rules"]
    gaps = [{"rule_id": r["rule_id"], "accepted_action_not_supported_by_quote": unsupported_actions(r)}
            for r in accepted if unsupported_actions(r)]
    n_gold = len(gold_rules)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "what_this_measures": ("The code validator only. Candidate rules are hand-entered from one real "
                               "circular; there is no model extraction yet (hack_win M4)."),
        "dataset_size": {"real_circulars": 1, "hand_entered_rules": n_gold, "hostile_cases": 2},
        "metrics": {
            "gold_rules_accepted": f"{len(accepted)}/{n_gold}",
            "verbatim_quote_validity_pct": round(100.0 * (n_gold - len(gold_run["rejected_rules"])) / n_gold, 1),
            "prompt_injection_refused": hostile_run["status"] == "refused"
                                        and hostile_run.get("refusal_type") == "hostile_injection",
            "invented_quote_refused": invented_run["status"] == "refused",
            "accepted_rules_with_unsupported_action": f"{len(gaps)}/{len(accepted)}",
        },
        "known_gaps": gaps,
        "results": [
            {"case": "DoE Delhi GRAP Stage-III circular No. 40 (hand-entered rules)",
             "accepted": [r["rule_id"] for r in accepted],
             "rejected": [r["rule"].get("rule_id") for r in gold_run["rejected_rules"]]},
            {"case": "Hostile circular with injected instruction ('SYSTEM OVERRIDE')",
             "status": hostile_run["status"], "reason": hostile_run.get("refusal_reason")},
            {"case": "Rule with an invented quote",
             "status": invented_run["status"],
             "reason": invented_run["rejected_rules"][0]["errors"][0] if invented_run["rejected_rules"] else None},
        ],
    }

    with open(os.path.join(gold_dir, "eval_table.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")
    return summary


if __name__ == "__main__":
    print(json.dumps(run_gold_evaluation(), indent=2))
