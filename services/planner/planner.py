"""
Saans Swap Planner & Plan B Fallback Engine
Deterministic scheduling algorithm matching CAQM Sept 16, 2026 guidelines:
'Re-plan, don't cancel: preserve activity minutes.'
"""

import copy
from typing import List, Dict, Any, Tuple
from services.rules.rules_engine import classify_period

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

def get_class_band(class_name: str) -> str:
    """Extracts band: primary (1-5), middle (6-8), secondary (9-10), senior (11-12)."""
    digits = "".join([c for c in class_name if c.isdigit()])
    if not digits:
        return "all"
    val = int(digits)
    if val <= 5:
        return "primary"
    elif val <= 8:
        return "middle"
    elif val <= 10:
        return "secondary"
    else:
        return "senior_secondary"

def calculate_duration_minutes(start_str: str, end_str: str) -> int:
    """Calculates minutes between HH:MM and HH:MM."""
    try:
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        return max(0, (eh * 60 + em) - (sh * 60 + sm))
    except Exception:
        return 40 # Standard default period duration

def build_teacher_timetable_index(periods: List[Dict[str, Any]]) -> Dict[Tuple[str, str], str]:
    """Map of (teacher_code, period) -> class_id to detect teacher clashes."""
    index = {}
    for p in periods:
        t = p.get("teacher_code")
        prd = p.get("period")
        if t and prd:
            index[(t, prd)] = p.get("class", "")
    return index

def build_venue_timetable_index(periods: List[Dict[str, Any]]) -> Dict[Tuple[str, str], str]:
    """Map of (venue, period) -> class_id to detect double-booking of grounds."""
    index = {}
    for p in periods:
        v = p.get("venue")
        prd = p.get("period")
        if v and prd:
            index[(v, prd)] = p.get("class", "")
    return index

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


def plan_schedule(
    timetable: List[Dict[str, Any]],
    forecast: Dict[str, Any],
    ruleset: Dict[str, Any],
    declared_stage: str,
    school_jurisdiction: str = "Delhi",
    delta: float = 0.20,
    decision_id: str = "T1#2026-10-12#MORN"
) -> Dict[str, Any]:
    """
    Executes the deterministic planner:
    1. Classifies all periods.
    2. Identifies outdoor periods requiring intervention (banned, restricted).
    3. Finds optimal valid swaps (Plan A).
    4. For unswappable periods, assigns Plan B (Indoor Wellness Activity).
    5. Calculates preserved PE minutes and modelled exposure reduction.
    """
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
            "classified_periods": classified_periods
        }

    # Prepare working copies for swapping
    working_timetable = [copy.deepcopy(p) for p in timetable]
    teacher_index = build_teacher_timetable_index(working_timetable)
    venue_index = build_venue_timetable_index(working_timetable)

    plan_a_swaps = []
    plan_b_fallbacks = []
    swapped_target_slots = set() # (class, period) slots already used

    for bad_period in problematic_periods:
        cls_id = bad_period["class"]
        orig_prd_id = bad_period["period"]
        orig_row = next((p for p in working_timetable if p["class"] == cls_id and p["period"] == orig_prd_id), None)
        
        if not orig_row:
            continue
            
        pe_teacher = orig_row.get("teacher_code")
        pe_venue = orig_row.get("venue")
        orig_fc = forecast_map.get(orig_prd_id, {"nominal": 200.0, "pessimistic": 240.0})

        # Try to find valid swap partner within the same class
        class_candidates = [
            p for p in working_timetable
            if p["class"] == cls_id
            and p["period"] != orig_prd_id
            and not p.get("locked")
            and not p.get("outdoor") # Partner must be an indoor period
            and (cls_id, p["period"]) not in swapped_target_slots
        ]

        best_partner = None
        best_score = -999999

        for candidate in class_candidates:
            target_prd_id = candidate["period"]
            target_fc = forecast_map.get(target_prd_id, {"nominal": 150.0, "pessimistic": 180.0})
            
            # HARD CONSTRAINT 1: Target period MUST be permitted under nominal AND pessimistic forecast
            # Test classifying the moved outdoor session in target_prd_id
            target_classification_nom = classify_period(
                period={**orig_row, "period": target_prd_id, "start": candidate["start"], "end": candidate["end"]},
                forecast_pm25=target_fc["nominal"],
                ruleset=ruleset,
                declared_stage=declared_stage,
                school_jurisdiction=school_jurisdiction
            )
            target_classification_pess = classify_period(
                period={**orig_row, "period": target_prd_id, "start": candidate["start"], "end": candidate["end"]},
                forecast_pm25=target_fc["pessimistic"],
                ruleset=ruleset,
                declared_stage=declared_stage,
                school_jurisdiction=school_jurisdiction
            )

            # If moving outdoor to this slot would still be banned or restricted under nominal or pessimistic -> REJECT
            if target_classification_nom["label"] in ("banned", "restricted"):
                continue
            if target_classification_pess["label"] in ("banned", "restricted"):
                continue

            # HARD CONSTRAINT 2: Teacher availability
            # Check if PE teacher is free during target_prd_id in other classes
            existing_pe_teacher_busy = teacher_index.get((pe_teacher, target_prd_id))
            if existing_pe_teacher_busy and existing_pe_teacher_busy != cls_id:
                continue # Teacher is busy teaching another class!

            # Check if candidate's indoor teacher is free during orig_prd_id in other classes
            indoor_teacher = candidate.get("teacher_code")
            existing_indoor_teacher_busy = teacher_index.get((indoor_teacher, orig_prd_id))
            if existing_indoor_teacher_busy and existing_indoor_teacher_busy != cls_id:
                continue # Indoor teacher busy during original period!

            # HARD CONSTRAINT 3: Ground / Venue availability
            # Check if pe_venue is already booked by another class in target_prd_id
            existing_venue_booked = venue_index.get((pe_venue, target_prd_id))
            if existing_venue_booked and existing_venue_booked != cls_id:
                continue # Ground is double-booked!

            # HARD CONSTRAINT 4: Modelled exposure strictly decreases
            exposure_reduction = orig_fc["nominal"] - target_fc["nominal"]
            if exposure_reduction <= 0:
                continue # Must strictly reduce exposure!

            score = exposure_reduction
            if score > best_score:
                best_score = score
                best_partner = candidate

        if best_partner:
            # We found a valid swap!
            target_prd_id = best_partner["period"]
            
            # Apply swap in working copy
            # Swap subjects, teachers, venues, and outdoor flags between orig_row and best_partner
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
            plan_a_swaps.append(swap_info)
            swapped_target_slots.add((cls_id, target_prd_id))

            # Update indices to maintain mutual exclusivity
            teacher_index[(pe_teacher, target_prd_id)] = cls_id
            teacher_index[(pe_teacher, orig_prd_id)] = None
            venue_index[(pe_venue, target_prd_id)] = cls_id
            venue_index[(pe_venue, orig_prd_id)] = None

            # Mark in working copy
            orig_row["outdoor"] = False
            best_partner["outdoor"] = True
            
        else:
            # No valid swap possible -> PLAN B FALLBACK (Indoor Wellness Session)
            band = get_class_band(cls_id)
            activities = DEFAULT_INDOOR_ACTIVITIES.get(band, DEFAULT_INDOOR_ACTIVITIES["all"])
            selected_activity = activities[len(plan_b_fallbacks) % len(activities)]
            
            plan_b_fallbacks.append({
                "class": cls_id,
                "period": orig_prd_id,
                "subject": orig_row["subject"],
                "venue": orig_row.get("venue", "Ground"),
                "fallback_venue": "Indoor Hall / Classroom",
                "assigned_activity": selected_activity,
                "duration_minutes": calculate_duration_minutes(orig_row.get("start", ""), orig_row.get("end", "")),
                "reason": bad_period.get("reason", "Outdoor sports prohibited; replaced with indoor session to preserve activity minutes."),
                "rule_id": bad_period.get("rule_ids", ["r-017"])[0] if bad_period.get("rule_ids") else "r-017"
            })
            # In working copy, mark as indoor
            orig_row["outdoor"] = False

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
        "classified_periods": classified_periods
    }
