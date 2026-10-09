"""
Saans Rules Engine
Implements the strict decision hierarchy:
1. Orders first: Declared stage + circular rules decide 'banned' or 'restricted'.
   A stage-level ban is NEVER relaxed by a clean forecast.
2. Forecast second: Inside what orders permit, configured PM2.5 bands decide 'advisory' vs 'allowed'.
3. Humans last: Code decides and labels; humans approve.
"""

from typing import Dict, Any, List, Optional

STAGE_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4}

class RulesEngineError(Exception):
    pass

class JurisdictionMismatchError(RulesEngineError):
    pass


def validate_ruleset_jurisdiction(ruleset: Dict[str, Any], target_jurisdiction: str):
    """
    Validates that the ruleset applies to the target school's jurisdiction.
    Raises JurisdictionMismatchError if they differ.
    """
    rs_jurisdiction = ruleset.get("jurisdiction", "").strip()
    target = target_jurisdiction.strip()
    
    # Allow Delhi within Delhi-NCR or vice-versa if appropriate, but reject completely different ones like 'Maharashtra'
    allowed_mappings = {
        "Delhi": ["Delhi", "Delhi-NCR"],
        "Delhi-NCR": ["Delhi", "Delhi-NCR", "Haryana", "Uttar Pradesh", "Rajasthan"]
    }
    
    valid_targets = allowed_mappings.get(rs_jurisdiction, [rs_jurisdiction])
    if target not in valid_targets and rs_jurisdiction != target:
        raise JurisdictionMismatchError(
            f"Ruleset jurisdiction '{rs_jurisdiction}' does not match target jurisdiction '{target}'."
        )


def classify_period(
    period: Dict[str, Any],
    forecast_pm25: float,
    ruleset: Dict[str, Any],
    declared_stage: str,
    school_jurisdiction: str = "Delhi"
) -> Dict[str, Any]:
    """
    Labels a timetable period with one of: 'allowed', 'advisory', 'restricted', 'banned'.
    
    Returns ClassifiedPeriod shape:
    {
        "class": "7B",
        "period": "P2",
        "start": "09:10",
        "end": "09:50",
        "label": "banned",
        "reason": "Stage III order r-017",
        "rule_ids": ["r-017"],
        "pm25": 280,
        "is_outdoor": True
    }
    """
    validate_ruleset_jurisdiction(ruleset, school_jurisdiction)
    
    raw_outdoor = period.get("outdoor")
    is_outdoor = raw_outdoor is True or str(raw_outdoor).lower() in ("true", "1", "yes")
    period_id = period.get("period", "")
    class_id = period.get("class", "")
    
    # Default label for indoor periods
    if not is_outdoor:
        return {
            "class": class_id,
            "period": period_id,
            "start": period.get("start", ""),
            "end": period.get("end", ""),
            "subject": period.get("subject", ""),
            "teacher_code": period.get("teacher_code", ""),
            "venue": period.get("venue", ""),
            "label": "allowed",
            "reason": "Indoor period; safe under current directives",
            "rule_ids": [],
            "pm25": forecast_pm25,
            "is_outdoor": False
        }
    
    current_stage_val = STAGE_ORDER.get(declared_stage, 0)
    
    # 1. ORDER FIRST: Check circular rules for stage-based bans/restrictions
    applicable_rule_ids = []
    order_action = None
    order_reason = None
    
    rules = ruleset.get("rules", [])
    for rule in rules:
        cond = rule.get("condition", {})
        min_stage = cond.get("stage_at_least")
        pm_threshold = cond.get("pm25_greater_than")
        
        matches_stage = True
        if min_stage:
            matches_stage = current_stage_val >= STAGE_ORDER.get(min_stage, 99)
            
        matches_pm = True
        if pm_threshold is not None:
            matches_pm = forecast_pm25 > pm_threshold
            
        if matches_stage and matches_pm:
            action = rule.get("action", {})
            outdoor_sports_action = action.get("outdoor_sports", "")
            outdoor_pt_action = action.get("outdoor_pt", "")
            
            # If outdoor activities are banned or restricted by order:
            if "banned" in (outdoor_sports_action, outdoor_pt_action):
                order_action = "banned"
                order_reason = f"Stage {declared_stage} order: {rule.get('source_quote', '')}"
                applicable_rule_ids.append(rule.get("rule_id", ""))
                break # Hardest restriction takes precedence immediately
            elif "restricted" in (outdoor_sports_action, outdoor_pt_action) and order_action != "banned":
                order_action = "restricted"
                order_reason = f"Stage {declared_stage} directive: {rule.get('source_quote', '')}"
                applicable_rule_ids.append(rule.get("rule_id", ""))
    
    # If the order explicitly banned or restricted outdoor activity, this TRUMPS forecast completely
    if order_action == "banned":
        return {
            "class": class_id,
            "period": period_id,
            "start": period.get("start", ""),
            "end": period.get("end", ""),
            "subject": period.get("subject", ""),
            "teacher_code": period.get("teacher_code", ""),
            "venue": period.get("venue", ""),
            "label": "banned",
            "reason": order_reason or f"Banned under Stage {declared_stage}",
            "rule_ids": applicable_rule_ids,
            "pm25": forecast_pm25,
            "is_outdoor": True
        }
        
    if order_action == "restricted":
        return {
            "class": class_id,
            "period": period_id,
            "start": period.get("start", ""),
            "end": period.get("end", ""),
            "subject": period.get("subject", ""),
            "teacher_code": period.get("teacher_code", ""),
            "venue": period.get("venue", ""),
            "label": "restricted",
            "reason": order_reason or f"Restricted under Stage {declared_stage}",
            "rule_ids": applicable_rule_ids,
            "pm25": forecast_pm25,
            "is_outdoor": True
        }

    # 2. FORECAST SECOND: Within order permissions, check advisory thresholds
    advisory_config = ruleset.get("advisory_pm25", {"advisory_at": 90, "restricted_at": 120})
    advisory_at = advisory_config.get("advisory_at", 90)
    restricted_at = advisory_config.get("restricted_at", 120)
    
    if forecast_pm25 >= restricted_at:
        label = "restricted"
        reason = f"Forecast PM2.5 ({forecast_pm25:.0f} µg/m³) exceeds restriction threshold ({restricted_at} µg/m³)"
    elif forecast_pm25 >= advisory_at:
        label = "advisory"
        reason = f"Forecast PM2.5 ({forecast_pm25:.0f} µg/m³) exceeds advisory threshold ({advisory_at} µg/m³)"
    else:
        label = "allowed"
        reason = f"Forecast PM2.5 ({forecast_pm25:.0f} µg/m³) within acceptable bounds"

    return {
        "class": class_id,
        "period": period_id,
        "start": period.get("start", ""),
        "end": period.get("end", ""),
        "subject": period.get("subject", ""),
        "teacher_code": period.get("teacher_code", ""),
        "venue": period.get("venue", ""),
        "label": label,
        "reason": reason,
        "rule_ids": applicable_rule_ids,
        "pm25": forecast_pm25,
        "is_outdoor": True
    }
