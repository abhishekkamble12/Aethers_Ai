"""
hack_win X2: indoors is not automatically safe. Plan B sessions go to the cleanest free indoor venue,
using configurable infiltration factors that are always labelled as assumptions.
"""

import copy
import unittest

from services.planner.handler import _get_demo_fixtures, _get_school_config, lambda_handler, rehearse_handler
from services.planner.planner import plan_schedule

BAN = {"jurisdiction": "Delhi", "advisory_pm25": {"advisory_at": 90, "restricted_at": 120},
       "rules": [{"rule_id": "r-ban", "applies_to": ["school"], "class_band": ["all"], "condition": {"stage_at_least": "III"},
                  "action": {"outdoor_sports": "banned", "outdoor_pt": "banned"}, "source_quote": "q"}]}
AIR = {"basis": "assumption", "note": "test", "default_ventilation": "normal",
       "infiltration": {"purifier": 0.3, "sealed": 0.5, "normal": 0.7, "open": 0.95}}
VENUES = [{"venue_id": "Hall", "ventilation": "purifier", "capacity": 90},
          {"venue_id": "Gym", "ventilation": "sealed", "capacity": 60},
          {"venue_id": "Verandah", "ventilation": "open", "capacity": 80}]


def row(cls, prd, subject, teacher, venue, outdoor):
    return {"class": cls, "day": "Monday", "period": prd, "start": "09:00", "end": "09:40", "subject": subject,
            "teacher_code": teacher, "venue": venue, "outdoor": outdoor, "locked": False}


FC = {"periods": [{"period": "P1", "pm25_nominal": 300, "pm25_pessimistic": 360},
                  {"period": "P2", "pm25_nominal": 300, "pm25_pessimistic": 360}]}


def plan(tt, venues=VENUES, air=AIR, sizes=None):
    return plan_schedule(tt, FC, BAN, "III", venues=venues, indoor_air=air, class_sizes=sizes or {"6A": 40, "7A": 40})


class TestVenueChoice(unittest.TestCase):

    def setUp(self):
        self.tt = [row("6A", "P1", "PE", "T_PE1", "Ground", True), row("6A", "P2", "Math", "T_M", "Room_6A", False)]

    def test_cleanest_free_venue_is_chosen_with_numbers_and_label(self):
        b = plan(self.tt)["plan_b"][0]
        vc = b["venue_choice"]
        self.assertEqual(b["fallback_venue"], "Hall")
        self.assertEqual(vc["chosen"]["indoor_pm25_modelled"], 90.0)  # 300 x 0.3
        self.assertEqual(vc["basis"], "assumption")
        self.assertEqual({a["venue_id"]: a["indoor_pm25_modelled"] for a in vc["alternatives"]},
                         {"Gym": 150.0, "Verandah": 285.0, "Room_6A": 210.0})
        self.assertIn("lowest modelled indoor PM2.5", vc["why"])

    def test_factors_are_configuration_not_code(self):
        air = copy.deepcopy(AIR)
        air["infiltration"]["purifier"] = 0.9  # e.g. purifiers measured as ineffective
        self.assertEqual(plan(self.tt, air=air)["plan_b"][0]["fallback_venue"], "Gym")

    def test_busy_venue_is_skipped_with_reason(self):
        tt = self.tt + [row("9A", "P1", "Assembly", "T_X", "Hall", False)]
        vc = plan(tt)["plan_b"][0]["venue_choice"]
        self.assertEqual(vc["chosen"]["venue_id"], "Gym")
        hall = next(a for a in vc["alternatives"] if a["venue_id"] == "Hall")
        self.assertEqual(hall["rejected"], "in use by 9A in P1")

    def test_two_classes_in_the_same_period_never_share_a_venue(self):
        tt = self.tt + [row("7A", "P1", "PE", "T_PE2", "Ground_B", True), row("7A", "P2", "Eng", "T_E", "Room_7A", False)]
        bs = {b["class"]: b for b in plan(tt)["plan_b"]}
        self.assertEqual((bs["6A"]["fallback_venue"], bs["7A"]["fallback_venue"]), ("Hall", "Gym"))
        hall = next(a for a in bs["7A"]["venue_choice"]["alternatives"] if a["venue_id"] == "Hall")
        self.assertIn("already assigned to 6A", hall["rejected"])

    def test_too_small_venue_is_rejected(self):
        res = plan(self.tt, sizes={"6A": 70})
        vc = res["plan_b"][0]["venue_choice"]
        self.assertEqual(vc["chosen"]["venue_id"], "Hall")
        gym = next(a for a in vc["alternatives"] if a["venue_id"] == "Gym")
        self.assertEqual(gym["rejected"], "capacity 60 < 70 students")

    def test_no_free_venue_means_minutes_are_lost_not_claimed(self):
        tiny = [{"venue_id": "Closet", "ventilation": "sealed", "capacity": 5}]
        tt = [row("6A", "P1", "PE", "T_PE1", "Ground", True)]  # no homeroom to fall back on
        res = plan(tt, venues=tiny)
        b = res["plan_b"][0]
        self.assertIsNone(b["fallback_venue"])
        self.assertIn("cannot run", b["venue_choice"]["why"])
        self.assertEqual(res["pe_minutes"]["lost"], 40)
        self.assertEqual(res["pe_minutes_preserved"], 0.0)

    def test_without_venue_data_behaviour_is_unchanged(self):
        res = plan_schedule(self.tt, FC, BAN, "III")
        self.assertEqual(res["plan_b"][0]["fallback_venue"], "Indoor Hall / Classroom")
        self.assertNotIn("venue_choice", res["plan_b"][0])
        self.assertIsNone(res["plan_b_indoor_exposure_modelled"])


class TestDemoSchool(unittest.TestCase):

    def test_stage_iii_demo_assigns_every_class_a_cleaner_room(self):
        d = lambda_handler({"stage": "III", "date": "2026-10-12"}, None)["decision"]
        self.assertEqual(len(d["plan_b"]), 6)
        used = {}
        for b in d["plan_b"]:
            ch = b["venue_choice"]["chosen"]
            self.assertIsNotNone(ch)
            self.assertLess(ch["indoor_pm25_modelled"], b["venue_choice"]["outdoor_pm25_forecast"])
            self.assertNotIn((ch["venue_id"], b["period"]), used)
            used[(ch["venue_id"], b["period"])] = b["class"]
            trace = next(t for t in d["decision_trace"] if (t["class"], t["period"]) == (b["class"], b["period"]))
            self.assertEqual(trace["outcome"]["venue"], ch["venue_id"])
        p2 = {b["class"]: b["fallback_venue"] for b in d["plan_b"] if b["period"] == "P2"}
        # X3: 7B has students with respiratory conditions, so it chooses first and gets the purifier hall.
        self.assertEqual(p2, {"7B": "Hall_A", "7A": "Gym"})

    def test_rehearsal_includes_venue_choice(self):
        import json
        body = json.loads(rehearse_handler({"httpMethod": "POST", "body": json.dumps({"stage": "IV"})}, None)["body"])
        self.assertTrue(all(b["venue_choice"]["basis"] == "assumption" for b in body["plan_b"]))

    def test_class_profiles_hold_counts_only(self):
        cfg = _get_school_config()
        self.assertTrue(all(isinstance(v, int) for v in cfg["class_sizes"].values()))
        tt, _, _ = _get_demo_fixtures()
        self.assertEqual(set(cfg["class_sizes"]), {r["class"] for r in tt})


if __name__ == "__main__":
    unittest.main()
