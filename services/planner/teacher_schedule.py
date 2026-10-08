"""
Teacher Schedule Generator
Produces personalized schedules for PE and subject teachers following timetable re-planning.
Ensures teachers never have to improvise at short notice when bad-air orders land.
"""

from typing import List, Dict, Any

def generate_teacher_schedules(
    original_timetable: List[Dict[str, Any]],
    plan_result: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """
    Transforms the master plan into per-teacher daily rosters.
    Returns:
    {
        "T_PE1": {
            "teacher_code": "T_PE1",
            "role": "Physical Education",
            "periods": [
                {
                    "period": "P2",
                    "time": "09:10-09:50",
                    "class": "7B",
                    "status": "FALLBACK_INDOOR",
                    "activity": "Table Tennis / Carrom Inter-House League",
                    "venue": "Indoor Hall / Gymnasium",
                    "instructions": "Outdoor activities banned under Stage III. Conduct indoor tournament."
                }
            ],
            "total_active_minutes": 80
        },
        ...
    }
    """
    teacher_schedules: Dict[str, Dict[str, Any]] = {}
    
    # Map swaps and fallbacks by (class, period)
    swaps_from = {s["from_period"]: s for s in plan_result.get("plan_a", [])}
    fallbacks = {f["period"]: f for f in plan_result.get("plan_b", [])}

    # Group original timetable entries by teacher
    for p in original_timetable:
        t_code = p.get("teacher_code", "UNKNOWN")
        if t_code not in teacher_schedules:
            subj = p.get("subject", "").strip().lower()
            is_pe = (
                "pe" in subj.split()
                or "pt" in subj.split()
                or "physical education" in subj
                or "sports" in subj
                or t_code.startswith("T_PE")
                or subj in ("pe", "pt")
            )
            teacher_schedules[t_code] = {
                "teacher_code": t_code,
                "role": "Physical Education" if is_pe else "Subject Teacher",
                "periods": [],
                "total_active_minutes": 0
            }

        p_id = p.get("period")
        cls_id = p.get("class")
        time_slot = f"{p.get('start')}-{p.get('end')}"
        duration = 40 # Standard period

        # Check if this period was affected
        if p_id in fallbacks and fallbacks[p_id]["class"] == cls_id:
            fb = fallbacks[p_id]
            teacher_schedules[t_code]["periods"].append({
                "period": p_id,
                "time": time_slot,
                "class": cls_id,
                "subject": p.get("subject"),
                "status": "PLAN_B_INDOOR_SESSION",
                "venue": fb.get("fallback_venue", "Indoor Hall"),
                "activity": fb.get("assigned_activity"),
                "note": f"Outdoor sport suspended: {fb.get('reason')}"
            })
            teacher_schedules[t_code]["total_active_minutes"] += duration

        elif p_id in swaps_from and swaps_from[p_id]["class"] == cls_id:
            sw = swaps_from[p_id]
            teacher_schedules[t_code]["periods"].append({
                "period": sw.get("to_period"),
                "original_period": p_id,
                "time": time_slot,
                "class": cls_id,
                "subject": p.get("subject"),
                "status": "PLAN_A_SWAPPED",
                "venue": p.get("venue"),
                "activity": f"Swapped to Period {sw.get('to_period')} (Lower pollution window)",
                "note": sw.get("reason")
            })
            teacher_schedules[t_code]["total_active_minutes"] += duration

        else:
            teacher_schedules[t_code]["periods"].append({
                "period": p_id,
                "time": time_slot,
                "class": cls_id,
                "subject": p.get("subject"),
                "status": "STANDARD_UNMODIFIED",
                "venue": p.get("venue"),
                "activity": p.get("subject"),
                "note": "Classroom session proceeds as normal."
            })
            teacher_schedules[t_code]["total_active_minutes"] += duration

    return teacher_schedules
