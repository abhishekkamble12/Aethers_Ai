"""
Saans Swap Planner & Plan B Fallback Engine
Deterministic scheduling algorithm matching CAQM Sept 16, 2026 guidelines:
'Re-plan, don't cancel: preserve activity minutes.'
"""

import copy
from typing import List, Dict, Any, Optional, Tuple
from services.rules.rules_engine import classify_period, get_class_band

DEFAULT_INDOOR_ACTIVITIES = {
    "primary": [
        "Indoor Yoga & Fun Posture Stories",
        "Rhythmic Aerobics & Coordination Drills",
        "Interactive Health & Wellness Workshop"
    ],
    "middle": [
        "Chess & Strategic Board Games Challenge",
        "Table Tennis / Carrom Inter-House League",
        "Indoor Calisthenics & Core Conditioning"
    ],
    "secondary": [
        "Chess Tournament & Tactical Analysis",
        "Indoor Fitness Circuit & Flexibility Training",
        "Sports Psychology & Strategy Audio-Visual Session"
    ],
    "senior_secondary": [
        "Cardio-Fitness & Aerobic Stretches",
        "Table Tennis & Reflex Training",
        "Sports Nutrition & Recovery Lecture"
    ],
    "all": [
        "Structured Indoor Physical Wellness Session",
        "Mindfulness & Low-Respiration Conditioning"
    ]
}

def calculate_duration_minutes(start_str: str, end_str: str) -> int:
    """Calculates minutes between HH:MM and HH:MM."""
    try:
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        return max(0, (eh * 60 + em) - (sh * 60 + sm))
    except Exception:
        return 40 # Standard default period duration

def evaluate_exposure(
    periods: List[Dict[str, Any]],
    forecast_map: Dict[str, Dict[str, float]],
    delta: float = 0.20
) -> Tuple[float, float]:
    """
    Computes (E_nominal, E_pessimistic) for the given timetable.
    E = sum(duration_minutes * pm25) for outdoor periods.
    """
    e_nominal = 0.0
    e_pessimistic = 0.0
    for p in periods:
        if p.get("outdoor"):
            prd = p.get("period")
            fc = forecast_map.get(prd, {"nominal": 150.0, "pessimistic": 180.0})
            duration = calculate_duration_minutes(p.get("start", ""), p.get("end", ""))
            pm_nom = fc.get("nominal", 150.0)
            pm_pess = fc.get("pessimistic", pm_nom * (1.0 + delta))
            e_nominal += duration * pm_nom
            e_pessimistic += duration * pm_pess
    return e_nominal, e_pessimistic


MOVABLE_FIELDS = ("subject", "teacher_code", "venue", "outdoor")


def _swap_content(a: Dict[str, Any], b: Dict[str, Any]) -> None:
    for f in MOVABLE_FIELDS:
        a[f], b[f] = b.get(f), a.get(f)


def find_conflicts(periods: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str, str], frozenset]:
    """(kind, who, day, period) -> classes, wherever one teacher or venue is in two classes at once."""
    occupancy: Dict[Tuple[str, str, str, str], set] = {}
    for p in periods:
        day, prd = p.get("day", ""), p.get("period", "")
        for kind, who in (("teacher", p.get("teacher_code")), ("venue", p.get("venue"))):
            if who:
                occupancy.setdefault((kind, who, day, prd), set()).add(p.get("class", ""))
    return {k: frozenset(v) for k, v in occupancy.items() if len(v) > 1}


def _new_conflicts(baseline, after):
    """Clashes in `after` that the input timetable did not already have."""
    return {k: v for k, v in after.items() if not (k in baseline and v <= baseline[k])}


def describe_conflict(key, classes) -> str:
    kind, who, day, prd = key
    return f"{kind} {who} would be in {', '.join(sorted(classes))} at once in {prd}" + (f" ({day})" if day else "")


def _plan_b(orig_row: Dict[str, Any], bad_period: Dict[str, Any], index: int) -> Dict[str, Any]:
    band = get_class_band(orig_row["class"])
    activities = DEFAULT_INDOOR_ACTIVITIES.get(band, DEFAULT_INDOOR_ACTIVITIES["all"])
    return {
        "class": orig_row["class"],
        "period": orig_row["period"],
        "subject": orig_row["subject"],
        "venue": orig_row.get("venue", "Ground"),
        "fallback_venue": "Indoor Hall / Classroom",
        "assigned_activity": activities[index % len(activities)],
        "duration_minutes": calculate_duration_minutes(orig_row.get("start", ""), orig_row.get("end", "")),
        "reason": bad_period.get("reason", "Outdoor sports prohibited; replaced with indoor session to preserve activity minutes."),
        "rule_id": bad_period.get("rule_ids", ["r-017"])[0] if bad_period.get("rule_ids") else "r-017"
    }


def plan_schedule(
    timetable: List[Dict[str, Any]],
    forecast: Dict[str, Any],
    ruleset: Dict[str, Any],
    declared_stage: str,
    school_jurisdiction: str = "Delhi",
    delta: float = 0.20,
    decision_id: str = "T1#2026-10-12#MORN",
    day: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the deterministic planner:
    1. Classifies all periods.
    2. Identifies outdoor periods requiring intervention (banned, restricted).
    3. Finds optimal valid swaps (Plan A).
    4. For unswappable periods, assigns Plan B (Indoor Wellness Activity).
    5. Calculates preserved PE minutes and modelled exposure reduction.
    """
    # 0. Plan one school day. Rows without a day are kept (single-day timetables).
    if day:
        timetable = [p for p in timetable if not p.get("day") or p["day"].strip().lower() == day.lower()]
        if not timetable:
            return {
                "decision_id": decision_id, "declared_stage": declared_stage, "day": day,
                "status": "confirmed_no_change", "message": f"No classes scheduled on {day}.",
                "plan_a": [], "plan_b": [], "exposure_before": 0.0, "exposure_after": 0.0,
                "exposure_reduction_pct": 0.0, "pe_minutes_preserved": 0.0,
                "ruleset_version": ruleset.get("ruleset_version", "unknown"),
                "classified_periods": [], "decision_trace": [],
                "revalidation": {"new_conflicts_found": 0, "swaps_reverted": []}
            }

    input_conflicts = [describe_conflict(k, v).replace(" would be", " is") for k, v in sorted(find_conflicts(timetable).items())]

    # 1. Build forecast lookup
    forecast_map = {}
    for fp in forecast.get("periods", []):
        forecast_map[fp["period"]] = {
            "nominal": float(fp.get("pm25_nominal", 150.0)),
            "pessimistic": float(fp.get("pm25_pessimistic", fp.get("pm25_nominal", 150.0) * (1.0 + delta)))
        }

    # 2. Classify all periods
    classified_periods = []
    for p in timetable:
        p_id = p.get("period")
        fc = forecast_map.get(p_id, {"nominal": 150.0, "pessimistic": 180.0})
        classified = classify_period(
            period=p,
            forecast_pm25=fc["nominal"],
            ruleset=ruleset,
            declared_stage=declared_stage,
            school_jurisdiction=school_jurisdiction
        )
        classified_periods.append(classified)

    # Calculate initial baseline exposure
    exp_before_nom, exp_before_pess = evaluate_exposure(timetable, forecast_map, delta)

    # Count scheduled PE minutes
    original_pe_minutes = sum(
        calculate_duration_minutes(p.get("start", ""), p.get("end", ""))
        for p in timetable
        if "pe" in p.get("subject", "").lower()
        or "physical education" in p.get("subject", "").lower()
        or "pt" in p.get("subject", "").lower()
        or bool(p.get("outdoor"))
    )

    # 3. Check for need to move
    # An outdoor period needs intervention if its label is 'banned' or 'restricted'
    problematic_periods = [
        cp for cp in classified_periods
        if cp.get("is_outdoor") and cp.get("label") in ("banned", "restricted")
    ]

    if not problematic_periods:
        # All periods allowed: no changes needed
        return {
            "decision_id": decision_id,
            "declared_stage": declared_stage,
            "status": "confirmed_no_change",
            "message": "All periods compliant under current orders and forecast.",
            "plan_a": [],
            "plan_b": [],
            "exposure_before": exp_before_nom,
            "exposure_after": exp_before_nom,
            "exposure_reduction_pct": 0.0,
            "pe_minutes_preserved": 100.0 if original_pe_minutes > 0 else 0.0,
            "ruleset_version": ruleset.get("ruleset_version", "unknown"),
            "classified_periods": classified_periods,
            "input_conflicts": input_conflicts,
            "decision_trace": [],
            "revalidation": {"new_conflicts_found": 0, "swaps_reverted": []}
        }

    # Prepare a working copy of the day. Swaps exchange the movable content of two periods of the
    # same class (subject, teacher, venue, outdoor); times stay with the slot.
    working_timetable = [copy.deepcopy(p) for p in timetable]
    baseline_conflicts = find_conflicts(working_timetable)

    plan_a_swaps = []
    plan_b_fallbacks = []
    decision_trace = []
    applied = []  # (swap_info, orig_row, partner_row) for fail-closed revalidation
    swapped_target_slots = set()  # (class, period) slots already used

    for bad_period in problematic_periods:
        cls_id = bad_period["class"]
        orig_prd_id = bad_period["period"]
        orig_row = next((p for p in working_timetable if p["class"] == cls_id and p["period"] == orig_prd_id), None)
        if not orig_row:
            continue

        orig_fc = forecast_map.get(orig_prd_id, {"nominal": 200.0, "pessimistic": 240.0})
        trace = {
            "class": cls_id, "period": orig_prd_id, "subject": orig_row.get("subject"),
            "label": bad_period["label"], "reason": bad_period["reason"], "rule_ids": bad_period.get("rule_ids", []),
            "forecast_pm25": orig_fc, "candidates": [], "outcome": None,
        }

        best_partner, best_score = None, None
        for candidate in [p for p in working_timetable if p["class"] == cls_id and p["period"] != orig_prd_id]:
            target_prd_id = candidate["period"]
            target_fc = forecast_map.get(target_prd_id, {"nominal": 150.0, "pessimistic": 180.0})
            reasons = []

            if candidate.get("locked"):
                reasons.append("locked period")
            if candidate.get("outdoor"):
                reasons.append("partner period is also outdoor")
            if (cls_id, target_prd_id) in swapped_target_slots:
                reasons.append("slot already used by another swap")

            if not reasons:
                # HARD CONSTRAINT 1: the moved outdoor session must be permitted in the target slot
                # under both the nominal and the pessimistic forecast.
                for kind in ("nominal", "pessimistic"):
                    c = classify_period(
                        period={**orig_row, "period": target_prd_id, "start": candidate["start"], "end": candidate["end"]},
                        forecast_pm25=target_fc[kind], ruleset=ruleset, declared_stage=declared_stage,
                        school_jurisdiction=school_jurisdiction
                    )
                    if c["label"] in ("banned", "restricted"):
                        reasons.append(f"{kind} forecast: {c['label']} ({c['reason']})")
                        break

            if not reasons:
                # HARD CONSTRAINT 2: modelled exposure strictly decreases
                if orig_fc["nominal"] - target_fc["nominal"] <= 0:
                    reasons.append(f"no exposure reduction ({target_fc['nominal']:.0f} vs {orig_fc['nominal']:.0f} µg/m³)")

            if not reasons:
                # HARD CONSTRAINT 3: the swapped day introduces no new teacher or venue clash
                _swap_content(orig_row, candidate)
                new = _new_conflicts(baseline_conflicts, find_conflicts(working_timetable))
                _swap_content(orig_row, candidate)  # undo the trial
                reasons.extend(describe_conflict(k, v) for k, v in sorted(new.items()))

            entry = {"period": target_prd_id, "subject": candidate.get("subject"), "forecast_pm25": target_fc,
                     "verdict": "rejected" if reasons else "valid", "reasons": reasons}
            trace["candidates"].append(entry)
            if not reasons:
                score = orig_fc["nominal"] - target_fc["nominal"]
                if best_score is None or score > best_score:
                    best_score, best_partner = score, candidate

        if best_partner:
            target_prd_id = best_partner["period"]
            for entry in trace["candidates"]:
                if entry["period"] == target_prd_id:
                    entry["verdict"] = "chosen"
            swap_info = {
                "class": cls_id,
                "from_period": orig_prd_id,
                "to_period": target_prd_id,
                "moved_subject": orig_row["subject"],
                "partner_subject": best_partner["subject"],
                "reason": f"Moved to {target_prd_id} with lower exposure ({forecast_map[target_prd_id]['nominal']} µg/m³ vs {orig_fc['nominal']} µg/m³)",
                "exposure_before": orig_fc["nominal"],
                "exposure_after": forecast_map[target_prd_id]["nominal"],
                "rule_id": bad_period.get("rule_ids", ["r-order"])[0] if bad_period.get("rule_ids") else "r-order"
            }
            _swap_content(orig_row, best_partner)
            plan_a_swaps.append(swap_info)
            applied.append((swap_info, orig_row, best_partner))
            swapped_target_slots.add((cls_id, target_prd_id))
            trace["outcome"] = {"plan": "A", "moved_to": target_prd_id}
        else:
            fallback = _plan_b(orig_row, bad_period, len(plan_b_fallbacks))
            plan_b_fallbacks.append(fallback)
            orig_row["outdoor"] = False
            trace["outcome"] = {"plan": "B", "activity": fallback["assigned_activity"],
                                "why": "no candidate period passed every hard constraint"}
        decision_trace.append(trace)

    # Whole-day revalidation, fail closed: if the final day has any clash the input did not have,
    # undo swaps (latest first) and give those classes Plan B instead.
    revalidation = {"new_conflicts_found": 0, "swaps_reverted": []}
    while applied:
        new = _new_conflicts(baseline_conflicts, find_conflicts(working_timetable))
        if not new:
            break
        revalidation["new_conflicts_found"] += len(new)
        swap_info, orig_row, partner = applied.pop()
        _swap_content(orig_row, partner)
        plan_a_swaps.remove(swap_info)
        bad = next(b for b in problematic_periods
                   if b["class"] == swap_info["class"] and b["period"] == swap_info["from_period"])
        plan_b_fallbacks.append(_plan_b(orig_row, bad, len(plan_b_fallbacks)))
        orig_row["outdoor"] = False
        revalidation["swaps_reverted"].append(f"{swap_info['class']} {swap_info['from_period']}->{swap_info['to_period']}")

    # Calculate final exposures
    exp_after_nom, exp_after_pess = evaluate_exposure(working_timetable, forecast_map, delta)
    red_pct = 0.0
    if exp_before_nom > 0:
        red_pct = round(((exp_before_nom - exp_after_nom) / exp_before_nom) * 100.0, 1)

    # Calculate preserved PE minutes:
    # All PE periods either successfully swapped into safe outdoor slots, converted to indoor sessions, or already compliant
    swapped_minutes = sum(
        calculate_duration_minutes(
            next((p["start"] for p in timetable if p["class"] == s["class"] and p["period"] == s["from_period"]), ""),
            next((p["end"] for p in timetable if p["class"] == s["class"] and p["period"] == s["from_period"]), "")
        )
        for s in plan_a_swaps
    )
    fallback_minutes = sum(
        fb.get("duration_minutes", 0) for fb in plan_b_fallbacks
    )
    unaffected_pe_minutes = sum(
        calculate_duration_minutes(p.get("start", ""), p.get("end", ""))
        for p in timetable
        if ("pe" in p.get("subject", "").lower()
            or "physical education" in p.get("subject", "").lower()
            or "pt" in p.get("subject", "").lower()
            or bool(p.get("outdoor")))
        and not any(bad["class"] == p["class"] and bad["period"] == p["period"] for bad in problematic_periods)
    )
    total_preserved_minutes = unaffected_pe_minutes + swapped_minutes + fallback_minutes
    pe_preserved_pct = round((total_preserved_minutes / original_pe_minutes) * 100.0, 1) if original_pe_minutes > 0 else 100.0

    return {
        "decision_id": decision_id,
        "declared_stage": declared_stage,
        "status": "pending_approval",
        "plan_a": plan_a_swaps,
        "plan_b": plan_b_fallbacks,
        "exposure_before": exp_before_nom,
        "exposure_after": exp_after_nom,
        "exposure_reduction_pct": red_pct,
        "pe_minutes_preserved": pe_preserved_pct,
        "ruleset_version": ruleset.get("ruleset_version", "unknown"),
        "classified_periods": classified_periods,
        "input_conflicts": input_conflicts,
        "decision_trace": decision_trace,
        "revalidation": revalidation
    }
