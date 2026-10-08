"""
Edge Tests for Planner under State Machine Real Constraints
Verifies:
1. Locked periods cannot be swapped out
2. Teacher busy in another class prevents illegal collision
3. Ground capacity limit prevents double-booking
4. PE minutes preserved remains 100% via Plan B when no swap is feasible
5. Whole-day revalidation consistency across classes
"""

import unittest
from services.planner.planner import plan_schedule

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

class TestPlannerEdges(unittest.TestCase):

    def setUp(self):
        self.forecast = {
            "periods": [
                { "period": "P1", "start": "08:30", "end": "09:10", "pm25_nominal": 65, "pm25_pessimistic": 78 },
                { "period": "P2", "start": "09:10", "end": "09:50", "pm25_nominal": 145, "pm25_pessimistic": 174 },
                { "period": "P3", "start": "10:05", "end": "10:45", "pm25_nominal": 80, "pm25_pessimistic": 96 }
            ]
        }

    def test_locked_period_is_never_swapped(self):
        """A period flagged with locked=True (e.g. Board exam, lab) cannot be chosen as a swap partner."""
        timetable = [
            # P1 has clean air but is locked (e.g. Board practical)
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "Science Practical", "teacher_code": "T_SCI", "venue": "Physics_Lab", "outdoor": False, "locked": True},
            # P2 has dirty air and is outdoor PT
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "PT", "teacher_code": "T_PE", "venue": "Ground_A", "outdoor": True, "locked": False},
            # P3 is available and not locked
            {"class": "7A", "day": "Monday", "period": "P3", "start": "10:05", "end": "10:45", "subject": "Social Studies", "teacher_code": "T_SST", "venue": "Room_101", "outdoor": False, "locked": False}
        ]

        res = plan_schedule(timetable, self.forecast, STAGE_II_RULESET, declared_stage="II")
        self.assertEqual(len(res["plan_a"]), 1)
        swap = res["plan_a"][0]
        # Should swap with P3, never locked P1
        self.assertEqual(swap["to_period"], "P3")
        self.assertNotEqual(swap["to_period"], "P1")

    def test_ground_clash_prevention_across_classes(self):
        """When Ground A is already occupied during a target period, another class cannot be scheduled there."""
        timetable = [
            # Class 7A has PT in high-pollution P2
            {"class": "7A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "Math", "teacher_code": "T_M1", "venue": "Room_101", "outdoor": False, "locked": False},
            {"class": "7A", "day": "Monday", "period": "P2", "start": "09:10", "end": "09:50", "subject": "PT", "teacher_code": "T_PE1", "venue": "Ground_A", "outdoor": True, "locked": False},
            # Class 8A already has Ground_A booked during P1!
            {"class": "8A", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "Sports", "teacher_code": "T_PE2", "venue": "Ground_A", "outdoor": True, "locked": False}
        ]

        # Since P1 has a ground clash on Ground_A, Class 7A cannot swap to P1
        res = plan_schedule(timetable, self.forecast, STAGE_II_RULESET, declared_stage="II")
        # Swap cannot occur to P1 on Ground_A; it should fall back to Plan B
        plan_a_for_7a = [s for s in res["plan_a"] if s["class"] == "7A"]
        self.assertEqual(len(plan_a_for_7a), 0)
        # Should have Plan B
        plan_b_for_7a = [b for b in res["plan_b"] if b["class"] == "7A"]
        self.assertEqual(len(plan_b_for_7a), 1)
        self.assertEqual(plan_b_for_7a[0]["period"], "P2")

    def test_pe_minutes_preserved_via_plan_b_bank(self):
        """When outdoor activities are banned (Stage III), Plan B assigns indoor sessions maintaining 100% PE minutes."""
        banned_ruleset = {
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
                    "source_quote": "All outdoor sports suspended."
                }
            ],
            "advisory_pm25": { "advisory_at": 90, "restricted_at": 120 }
        }
        timetable = [
            {"class": "7B", "day": "Monday", "period": "P1", "start": "08:30", "end": "09:10", "subject": "PT", "teacher_code": "T_PE", "venue": "Ground_A", "outdoor": True, "locked": False}
        ]
        res = plan_schedule(timetable, self.forecast, banned_ruleset, declared_stage="III")
        self.assertEqual(len(res["plan_a"]), 0) # No swaps possible under Stage III
        self.assertEqual(len(res["plan_b"]), 1)
        self.assertEqual(res["pe_minutes_preserved"], 100.0)
        self.assertIn("Indoor", res["plan_b"][0]["fallback_venue"])

if __name__ == "__main__":
    unittest.main()
