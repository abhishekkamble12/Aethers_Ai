"""
The 10 Mandatory Planner & Rules Tests
Verifies all hard constraints, order hierarchy, pessimistic checks, and fallback mechanisms.
"""

import unittest
from services.rules.rules_engine import (
    classify_period,
    JurisdictionMismatchError
)
from services.planner.planner import plan_schedule

# Base ruleset fixture
STAGE_II_RULESET = {
    "ruleset_version": "2026-10-08-r1",
    "jurisdiction": "Delhi",
    "declared_stage": "II",
    "rules": [
        {
            "rule_id": "r-stage2-adv",
            "applies_to": ["school"],
            "class_band": ["all"],
            "condition": { "stage_at_least": "II", "pm25_greater_than": 120 },
            "action": { "outdoor_sports": "restricted", "outdoor_pt": "restricted" },
            "source_quote": "Advise schools to limit outdoor sports during high pollution periods under Stage II."
        }
    ],
    "advisory_pm25": { "advisory_at": 90, "restricted_at": 120 }
}

STAGE_III_BANNED_RULESET = {
    "ruleset_version": "2026-10-08-r1",
    "jurisdiction": "Delhi",
    "declared_stage": "III",
    "rules": [
        {
            "rule_id": "r-017",
            "applies_to": ["school"],
            "class_band": ["all"],
            "condition": { "stage_at_least": "III" },
            "action": { "outdoor_sports": "banned", "outdoor_pt": "banned" },
            "source_quote": "All outdoor sports and physical education activities in schools shall remain strictly suspended under Stage III of GRAP."
        }
    ],
    "advisory_pm25": { "advisory_at": 90, "restricted_at": 120 }
}


class TestSaansPlanner(unittest.TestCase):

    def setUp(self):
        self.sample_forecast = {
            "periods": [
                { "period": "P1", "start": "08:30", "end": "09:10", "pm25_nominal": 70, "pm25_pessimistic": 84 },
                { "period": "P2", "start": "09:10", "end": "09:50", "pm25_nominal": 140, "pm25_pessimistic": 168 },
                { "period": "P3", "start": "10:05", "end": "10:45", "pm25_nominal": 180, "pm25_pessimistic": 216 },
                { "period": "P4", "start": "10:45", "end": "11:25", "pm25_nominal": 80, "pm25_pessimistic": 96 }
            ]
        }

    def test_01_valid_swap_exists_and_chosen(self):
        """Test 1: Valid swap exists to a clean period with available teacher and ground."""
        timetable = [
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "Math", "teacher_code": "T_MATH", "venue": "Room_101", "outdoor": False, "locked": False},
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "PT", "teacher_code": "T_PE", "venue": "Ground_A", "outdoor": True, "locked": False}
        ]
        # P2 has 140 ug/m3 (restricted). P1 has 70 ug/m3 (allowed).
        res = plan_schedule(timetable, self.sample_forecast, STAGE_II_RULESET, declared_stage="II")
        self.assertEqual(len(res["plan_a"]), 1)
        swap = res["plan_a"][0]
        self.assertEqual(swap["from_period"], "P2")
        self.assertEqual(swap["to_period"], "P1")
        self.assertGreater(res["exposure_reduction_pct"], 0)

    def test_02_best_partner_teacher_busy_next_chosen(self):
        """Test 2: Best partner's teacher is busy in another class, so next best partner is chosen."""
        forecast = {
            "periods": [
                { "period": "P1", "start": "08:30", "end": "09:10", "pm25_nominal": 60, "pm25_pessimistic": 72 }, # best clean slot
                { "period": "P2", "start": "09:10", "end": "09:50", "pm25_nominal": 75, "pm25_pessimistic": 90 }, # 2nd best clean slot
                { "period": "P3", "start": "10:05", "end": "10:45", "pm25_nominal": 160, "pm25_pessimistic": 192 } # PT slot (restricted)
            ]
        }
        timetable = [
            # 7A has PT in P3
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "English", "teacher_code": "T_ENG", "venue": "Room_101", "outdoor": False, "locked": False},
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "Math", "teacher_code": "T_MATH", "venue": "Room_101", "outdoor": False, "locked": False},
            {"class": "7A", "day": "Monday", "period": "P3", "start": "10:05", "end": "10:45", "subject": "PT", "teacher_code": "T_PE", "venue": "Ground_A", "outdoor": True, "locked": False},
            # But in class 8A, PE teacher T_PE is already teaching during P1!
            {"class": "8A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "PT", "teacher_code": "T_PE", "venue": "Ground_B", "outdoor": False, "locked": False}
        ]
        res = plan_schedule(timetable, forecast, STAGE_II_RULESET, declared_stage="II")
        # Swap for 7A should choose P2, because T_PE is busy in P1
        swaps_7a = [s for s in res["plan_a"] if s["class"] == "7A"]
        self.assertEqual(len(swaps_7a), 1)
        self.assertEqual(swaps_7a[0]["to_period"], "P2")

    def test_03_ground_double_booked_rejected(self):
        """Test 3: Ground is already booked by another class in target period, so swap is rejected."""
        timetable = [
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "Math", "teacher_code": "T_MATH1", "venue": "Room_101", "outdoor": False, "locked": False},
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "PT", "teacher_code": "T_PE1", "venue": "Ground_A", "outdoor": True, "locked": False},
            # Another class 8A has Ground_A booked in P1
            {"class": "8A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "PT", "teacher_code": "T_PE2", "venue": "Ground_A", "outdoor": True, "locked": True}
        ]
        res = plan_schedule(timetable, self.sample_forecast, STAGE_II_RULESET, declared_stage="II")
        # Cannot swap into P1 because Ground_A is occupied by 8A -> Falls back to Plan B
        self.assertEqual(len(res["plan_a"]), 0)
        self.assertEqual(len(res["plan_b"]), 1)
        self.assertIn("Indoor", res["plan_b"][0]["fallback_venue"])

    def test_04_outdoor_sports_banned_for_day_so_plan_b(self):
        """Test 4: When outdoor sports are banned (Stage III), all outdoor periods fall back to Plan B."""
        timetable = [
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "PT", "teacher_code": "T_PE", "venue": "Ground_A", "outdoor": True, "locked": False},
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "English", "teacher_code": "T_ENG", "venue": "Room_101", "outdoor": False, "locked": False}
        ]
        res = plan_schedule(timetable, self.sample_forecast, STAGE_III_BANNED_RULESET, declared_stage="III")
        self.assertEqual(len(res["plan_a"]), 0)
        self.assertEqual(len(res["plan_b"]), 1)
        self.assertIn("Indoor", res["plan_b"][0]["fallback_venue"])
        self.assertEqual(res["pe_minutes_preserved"], 100.0)

    def test_05_locked_period_never_moved(self):
        """Test 5: A locked period is never moved or chosen as a swap partner."""
        timetable = [
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "Exam/Assembly", "teacher_code": "T_EXAM", "venue": "Hall", "outdoor": False, "locked": True},
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "PT", "teacher_code": "T_PE", "venue": "Ground_A", "outdoor": True, "locked": False}
        ]
        res = plan_schedule(timetable, self.sample_forecast, STAGE_II_RULESET, declared_stage="II")
        # P1 is locked, so cannot swap -> must fallback to Plan B
        self.assertEqual(len(res["plan_a"]), 0)
        self.assertEqual(len(res["plan_b"]), 1)

    def test_06_two_proposals_conflict_revalidates_and_resolves(self):
        """Test 6: Multiple classes vying for same clean slot don't double-book teacher or ground."""
        timetable = [
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "Math", "teacher_code": "T_MATH1", "venue": "Room_101", "outdoor": False, "locked": False},
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "PT", "teacher_code": "T_PE1", "venue": "Ground_A", "outdoor": True, "locked": False},
            {"class": "7B", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "English", "teacher_code": "T_ENG2", "venue": "Room_102", "outdoor": False, "locked": False},
            {"class": "7B", "day": "Monday", "period": "P3", "start": "10:05", "end": "10:45", "subject": "PT", "teacher_code": "T_PE1", "venue": "Ground_A", "outdoor": True, "locked": False}
        ]
        # Both 7A and 7B want to swap into P1 (clean slot), but have the same T_PE1 and Ground_A!
        res = plan_schedule(timetable, self.sample_forecast, STAGE_II_RULESET, declared_stage="II")
        # One class can get the swap; the other must fall back to Plan B without conflicting!
        total_swaps = len(res["plan_a"])
        total_fallbacks = len(res["plan_b"])
        self.assertEqual(total_swaps, 1)
        self.assertEqual(total_fallbacks, 1)

    def test_07_all_periods_allowed_no_change(self):
        """Test 7: When all forecast PM2.5 readings are clean and stage is I, no change is made."""
        clean_forecast = {
            "periods": [
                { "period": "P1", "start": "08:30", "end": "09:10", "pm25_nominal": 45, "pm25_pessimistic": 54 },
                { "period": "P2", "start": "09:10", "end": "09:50", "pm25_nominal": 55, "pm25_pessimistic": 66 }
            ]
        }
        timetable = [
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "PT", "teacher_code": "T_PE", "venue": "Ground_A", "outdoor": True, "locked": False},
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "Math", "teacher_code": "T_MATH", "venue": "Room_101", "outdoor": False, "locked": False}
        ]
        clean_ruleset = {
            "ruleset_version": "2026-10-08-r1",
            "jurisdiction": "Delhi",
            "declared_stage": "I",
            "rules": [],
            "advisory_pm25": { "advisory_at": 90, "restricted_at": 120 }
        }
        res = plan_schedule(timetable, clean_forecast, clean_ruleset, declared_stage="I")
        self.assertEqual(res["status"], "confirmed_no_change")
        self.assertEqual(len(res["plan_a"]), 0)
        self.assertEqual(len(res["plan_b"]), 0)

    def test_08_fine_nominally_but_fails_pessimistic_rejected(self):
        """Test 8: Candidate period fine under nominal (110 < 120) but exceeds under pessimistic (110 * 1.2 = 132 > 120) is rejected."""
        borderline_forecast = {
            "periods": [
                { "period": "P1", "start": "08:30", "end": "09:10", "pm25_nominal": 110, "pm25_pessimistic": 132 }, # 110 is nominally < 120, but pessimistic 132 >= 120!
                { "period": "P2", "start": "09:10", "end": "09:50", "pm25_nominal": 250, "pm25_pessimistic": 300 }
            ]
        }
        timetable = [
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "Math", "teacher_code": "T_MATH", "venue": "Room_101", "outdoor": False, "locked": False},
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "PT", "teacher_code": "T_PE", "venue": "Ground_A", "outdoor": True, "locked": False}
        ]
        res = plan_schedule(timetable, borderline_forecast, STAGE_II_RULESET, declared_stage="II", delta=0.20)
        # P1 fails pessimistic check -> swap must be rejected -> falls back to Plan B
        self.assertEqual(len(res["plan_a"]), 0)
        self.assertEqual(len(res["plan_b"]), 1)

    def test_09_stage_ban_never_relaxed_by_low_pm25(self):
        """Test 9: Under Stage III ban, even if forecast PM2.5 is exceptionally low (e.g. 25 ug/m3), outdoor is banned."""
        clean_period = {"class": "7A", "period": "P1", "outdoor": True, "subject": "PT"}
        classification = classify_period(
            period=clean_period,
            forecast_pm25=25.0, # Pristine air
            ruleset=STAGE_III_BANNED_RULESET,
            declared_stage="III"
        )
        self.assertEqual(classification["label"], "banned")
        self.assertIn("Stage III", classification["reason"])

    def test_10_ruleset_for_another_jurisdiction_rejected(self):
        """Test 10: Ruleset declared for Mumbai/Maharashtra rejected when applied to Delhi school."""
        wrong_ruleset = {
            "ruleset_version": "2026-10-08-mumbai-r1",
            "jurisdiction": "Maharashtra",
            "declared_stage": "III",
            "rules": []
        }
        with self.assertRaises(JurisdictionMismatchError):
            classify_period(
                period={"class": "7A", "period": "P1", "outdoor": True},
                forecast_pm25=100.0,
                ruleset=wrong_ruleset,
                declared_stage="III",
                school_jurisdiction="Delhi"
            )


if __name__ == "__main__":
    unittest.main()
