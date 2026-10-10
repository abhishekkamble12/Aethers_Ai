"""
Saans Swap Planner & Plan B Fallback Engine
Deterministic scheduling algorithm matching CAQM Sept 16, 2026 guidelines:
'Re-plan, don't cancel: preserve activity minutes.'
"""

import copy
from typing import List, Dict, Any, Optional, Tuple
from services.rules.rules_engine import classify_period, get_class_band

# Plan B indoor sessions. Only sessions with real physical movement count as "kept active";
# a custom bank may add seated items with physical=False and they are reported as lost PE minutes.
DEFAULT_INDOOR_ACTIVITIES = {
    "primary": [
        {"name": "Indoor Yoga & Fun Posture Stories", "physical": True},
        {"name": "Rhythmic Aerobics & Coordination Drills", "physical": True},
        {"name": "Indoor Movement Games (Relay, Balance, Hopscotch)", "physical": True}
    ],
    "middle": [
        {"name": "Table Tennis Inter-House League", "physical": True},
        {"name": "Indoor Calisthenics & Core Conditioning", "physical": True},
        {"name": "Skipping & Agility Ladder Circuit", "physical": True}
    ],
    "secondary": [
        {"name": "Indoor Fitness Circuit & Flexibility Training", "physical": True},
        {"name": "Table Tennis & Badminton Footwork Drills", "physical": True},
        {"name": "Yoga & Mobility Session", "physical": True}
    ],
    "senior_secondary": [
        {"name": "Cardio-Fitness & Aerobic Stretches", "physical": True},
        {"name": "Table Tennis & Reflex Training", "physical": True},
        {"name": "Bodyweight Strength Circuit", "physical": True}
    ],
    "all": [
        {"name": "Structured Indoor Physical Wellness Session", "physical": True}
    ]
}

PE_SUBJECTS = {"physical education", "pe", "pt", "physical training", "games", "sports"}


def is_pe_period(p: Dict[str, Any]) -> bool:
    """A PE/sports period: an outdoor period, or a subject that is exactly a PE name (no substring guessing)."""
    return bool(p.get("outdoor")) or p.get("subject", "").strip().lower() in PE_SUBJECTS


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
    activity = activities[index % len(activities)]
    return {
        "class": orig_row["class"],
        "period": orig_row["period"],
        "subject": orig_row["subject"],
        "venue": orig_row.get("venue", "Ground"),
        "fallback_venue": "Indoor Hall / Classroom",
        "assigned_activity": activity["name"],
        "activity_is_physical": activity["physical"],
        "duration_minutes": calculate_duration_minutes(orig_row.get("start", ""), orig_row.get("end", "")),
        "reason": bad_period.get("reason", "Outdoor sports prohibited; replaced with indoor session to preserve activity minutes."),
        "rule_id": bad_period.get("rule_ids", ["r-017"])[0] if bad_period.get("rule_ids") else "r-017"
    }


def homeroom(timetable: List[Dict[str, Any]], cls: str, exclude=frozenset()) -> Optional[str]:
    """The indoor venue a class uses most (its classroom). `exclude` holds (class, period) slots that are
    being moved indoors: their venue is the outdoor ground they are leaving, not a classroom."""
    counts: Dict[str, int] = {}
    for p in timetable:
        if p["class"] == cls and (p["class"], p["period"]) not in exclude and not p.get("outdoor") and p.get("venue"):
            counts[p["venue"]] = counts.get(p["venue"], 0) + 1
    return max(sorted(counts), key=counts.get) if counts else None


def assign_indoor_venues(plan_b_fallbacks, final_timetable, forecast_map, venues, indoor_air, class_sizes) -> None:
    """
    X2: indoors is not automatically safe. For each Plan B session, model indoor PM2.5 in every candidate
    venue (outdoor forecast x infiltration factor for its ventilation, a labelled assumption), skip venues
    that are busy in that period, already given to another class, or too small, and pick the cleanest.
    """
    factors = indoor_air["infiltration"]
    default_vent = indoor_air.get("default_ventilation", "normal")
    taken: Dict[Tuple[str, str], str] = {}  # (venue, period) -> class, from Plan B assignments
    moving = {(b["class"], b["period"]) for b in plan_b_fallbacks}
    busy = {}
    for r in final_timetable:  # venues in use, except the outdoor slots that Plan B classes are leaving
        if (r["class"], r["period"]) not in moving and r.get("venue"):
            busy.setdefault((r["venue"], r["period"]), r["class"])

    for b in sorted(plan_b_fallbacks, key=lambda x: (x["period"], x["class"])):
        prd, cls = b["period"], b["class"]
        outdoor_pm = forecast_map.get(prd, {"nominal": 150.0})["nominal"]
        students = class_sizes.get(cls)
        candidates = [dict(v) for v in venues]
        own = homeroom(final_timetable, cls, exclude=moving)
        if own and all(v["venue_id"] != own for v in candidates):
            candidates.append({"venue_id": own, "label": f"{cls} classroom", "ventilation": default_vent,
                               "capacity": students})
        options = []
        for v in candidates:
            vent = v.get("ventilation", default_vent)
            factor = factors.get(vent, factors.get(default_vent))
            entry = {"venue_id": v["venue_id"], "label": v.get("label"), "ventilation": vent,
                     "infiltration_factor": factor, "indoor_pm25_modelled": round(outdoor_pm * factor, 1)}
            if v["venue_id"] != own and (v["venue_id"], prd) in busy:
                entry["rejected"] = f"in use by {busy[(v['venue_id'], prd)]} in {prd}"
            elif (v["venue_id"], prd) in taken:
                entry["rejected"] = f"already assigned to {taken[(v['venue_id'], prd)]} for Plan B in {prd}"
            elif students and v.get("capacity") and v["capacity"] < students:
                entry["rejected"] = f"capacity {v['capacity']} < {students} students"
            options.append(entry)
        free = sorted((o for o in options if "rejected" not in o), key=lambda o: (o["indoor_pm25_modelled"], o["venue_id"]))
        chosen = free[0] if free else None
        if chosen:
            taken[(chosen["venue_id"], prd)] = cls
        b["fallback_venue"] = chosen["venue_id"] if chosen else None
        b["venue_choice"] = {
            "outdoor_pm25_forecast": outdoor_pm,
            "chosen": chosen,
            "alternatives": [o for o in options if o is not chosen],
            "basis": indoor_air.get("basis", "assumption"),
            "assumption_note": indoor_air.get("note"),
            "why": (f"lowest modelled indoor PM2.5 among free venues ({chosen['indoor_pm25_modelled']} vs "
                    f"{outdoor_pm} outdoors)") if chosen else "no free indoor venue large enough: session cannot run",
        }


def pe_minutes_report(timetable, problematic_periods, plan_a_swaps, plan_b_fallbacks) -> Dict[str, Any]:
    """
    Measured from the timetable: where every scheduled PE minute ended up.
    kept_active = unchanged + moved to a cleaner outdoor slot + replaced by a physical indoor session.
    """
    moved = {(s["class"], s["from_period"]) for s in plan_a_swaps}
    replaced = {(b["class"], b["period"]): b for b in plan_b_fallbacks}
    flagged = {(b["class"], b["period"]) for b in problematic_periods}
    m = {"scheduled": 0, "unchanged": 0, "moved_to_cleaner_slot": 0, "replaced_indoor_active": 0, "lost": 0}
    for p in timetable:
        if not is_pe_period(p):
            continue
        mins = calculate_duration_minutes(p.get("start", ""), p.get("end", ""))
        key = (p["class"], p["period"])
        m["scheduled"] += mins
        if key in moved:
            m["moved_to_cleaner_slot"] += mins
        elif key in replaced:
            fb = replaced[key]
            has_room = fb.get("venue_choice") is None or fb["venue_choice"]["chosen"] is not None
            m["replaced_indoor_active" if fb.get("activity_is_physical") and has_room else "lost"] += mins
        elif key in flagged:
            m["lost"] += mins  # flagged but neither moved nor replaced
        else:
            m["unchanged"] += mins
    kept = m["unchanged"] + m["moved_to_cleaner_slot"] + m["replaced_indoor_active"]
    pct = round(kept / m["scheduled"] * 100.0, 1) if m["scheduled"] else 0.0
    return {
        "pe_minutes": {**m, "kept_active": kept, "basis": "measured from the timetable"},
        # Share of scheduled PE minutes that stayed physically active (outdoors in a permitted slot or a
        # physical indoor session). Exposure numbers next to it are modelled, not measured.
        "pe_minutes_preserved": pct,
    }


def plan_schedule(
    timetable: List[Dict[str, Any]],
    forecast: Dict[str, Any],
    ruleset: Dict[str, Any],
    declared_stage: str,
    school_jurisdiction: str = "Delhi",
    delta: float = 0.20,
    decision_id: str = "T1#2026-10-12#MORN",
    day: Optional[str] = None,
    venues: Optional[List[Dict[str, Any]]] = None,
    indoor_air: Optional[Dict[str, Any]] = None,
    class_sizes: Optional[Dict[str, int]] = None
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
                "exposure_reduction_pct": 0.0, **pe_minutes_report([], [], [], []),
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
            **pe_minutes_report(timetable, [], [], []),
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

    # X2: place each Plan B session in the cleanest free indoor venue (modelled, labelled assumption)
    indoor_exposure = None
    if venues is not None and indoor_air is not None:
        assign_indoor_venues(plan_b_fallbacks, working_timetable, forecast_map, venues, indoor_air, class_sizes or {})
        traces = {(t["class"], t["period"]): t for t in decision_trace}
        indoor_exposure = 0.0
        for b in plan_b_fallbacks:
            t = traces.get((b["class"], b["period"]))
            if t and t["outcome"] and t["outcome"].get("plan") == "B":
                t["outcome"]["venue"] = b["fallback_venue"]
                t["outcome"]["venue_why"] = b["venue_choice"]["why"]
            if b["venue_choice"]["chosen"]:
                indoor_exposure += b["duration_minutes"] * b["venue_choice"]["chosen"]["indoor_pm25_modelled"]

    # Calculate final exposures
    exp_after_nom, exp_after_pess = evaluate_exposure(working_timetable, forecast_map, delta)
    red_pct = 0.0
    if exp_before_nom > 0:
        red_pct = round(((exp_before_nom - exp_after_nom) / exp_before_nom) * 100.0, 1)

    return {
        "decision_id": decision_id,
        "declared_stage": declared_stage,
        "status": "pending_approval",
        "plan_a": plan_a_swaps,
        "plan_b": plan_b_fallbacks,
        "exposure_before": exp_before_nom,
        "exposure_after": exp_after_nom,
        "exposure_reduction_pct": red_pct,
        "plan_b_indoor_exposure_modelled": indoor_exposure,
        **pe_minutes_report(timetable, problematic_periods, plan_a_swaps, plan_b_fallbacks),
        "ruleset_version": ruleset.get("ruleset_version", "unknown"),
        "classified_periods": classified_periods,
        "input_conflicts": input_conflicts,
        "decision_trace": decision_trace,
        "revalidation": revalidation
    }
