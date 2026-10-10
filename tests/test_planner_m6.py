"""
hack_win M6: planner correctness (no teacher/venue double-booking, day filtering, class-band rules,
fail-closed revalidation) and decision explanations.
"""

import unittest
from collections import Counter

import services.planner.planner as planner
from services.planner.handler import _get_demo_fixtures, lambda_handler
from services.planner.planner import find_conflicts, plan_schedule
from services.rules.rules_engine import classify_period

NO_ORDER = {"jurisdiction": "Delhi", "rules": [], "advisory_pm25": {"advisory_at": 90, "restricted_at": 100}}


def row(cls, prd, subject, teacher, venue, outdoor, start, end, day="Monday", locked=False):
    return {"class": cls, "day": day, "period": prd, "start": start, "end": end, "subject": subject,
            "teacher_code": teacher, "venue": venue, "outdoor": outdoor, "locked": locked}


def forecast(**pm):
    return {"periods": [{"period": p, "pm25_nominal": v, "pm25_pessimistic": v * 1.1} for p, v in pm.items()]}


def final_grid(timetable, plan):
    """Apply the plan's swaps to the input and return the resulting day."""
    grid = {(r["class"], r["period"]): dict(r) for r in timetable}
    for s in plan["plan_a"]:
        a, b = grid[(s["class"], s["from_period"])], grid[(s["class"], s["to_period"])]
        for f in ("subject", "teacher_code", "venue", "outdoor"):
            a[f], b[f] = b[f], a[f]
    for fb in plan["plan_b"]:
        grid[(fb["class"], fb["period"])]["outdoor"] = False
    return list(grid.values())


class TestNoDoubleBooking(unittest.TestCase):

    def setUp(self):
        # Audit repro: X and Y both have PE in P1; T_M teaches X in P2 and Y in P5.
        self.tt = [row("X", "P1", "PE", "T_PE1", "G1", True, "08:00", "08:40"),
                   row("X", "P2", "Math", "T_M", "R1", False, "08:40", "09:20"),
                   row("Y", "P1", "PE", "T_PE2", "G2", True, "08:00", "08:40"),
                   row("Y", "P2", "Eng", "T_E", "R2", False, "08:40", "09:20"),
                   row("Y", "P5", "Math", "T_M", "R2", False, "11:00", "11:40")]
        self.fc = forecast(P1=110, P2=50, P5=40)

    def test_indoor_teacher_is_never_put_in_two_classes(self):
        plan = plan_schedule(self.tt, self.fc, NO_ORDER, "I")
        grid = final_grid(self.tt, plan)
        clashes = [k for k, n in Counter((r["teacher_code"], r["period"]) for r in grid).items() if n > 1]
        self.assertEqual(clashes, [], plan["plan_a"])
        self.assertEqual(find_conflicts(grid), {})

    def test_rejected_candidate_explains_the_clash(self):
        plan = plan_schedule(self.tt, self.fc, NO_ORDER, "I")
        y = next(t for t in plan["decision_trace"] if t["class"] == "Y")
        p5 = next(c for c in y["candidates"] if c["period"] == "P5")
        self.assertEqual(p5["verdict"], "rejected")
        self.assertIn("teacher T_M would be in X, Y at once in P1", p5["reasons"][0])
        self.assertEqual(y["outcome"], {"plan": "A", "moved_to": "P2"})  # next best valid slot

    def test_demo_timetable_has_no_input_clashes_and_plans_clean(self):
        tt, fc, rs = _get_demo_fixtures()
        self.assertEqual(find_conflicts(tt), {})
        for stage in ("I", "II", "III", "IV"):
            plan = plan_schedule(tt, fc, rs, stage, day="Monday")
            self.assertEqual(find_conflicts(final_grid(tt, plan)), {}, stage)
            self.assertEqual(plan["input_conflicts"], [])


class TestDayFilter(unittest.TestCase):

    def setUp(self):
        self.tt = [row("6A", "P1", "PE", "T_PE1", "G1", True, "08:00", "08:40", day="Monday"),
                   row("6A", "P2", "Math", "T_M", "R1", False, "08:40", "09:20", day="Monday"),
                   row("6A", "P1", "Art", "T_A", "R1", False, "08:00", "08:40", day="Tuesday"),
                   row("6A", "P2", "PE", "T_PE1", "G1", True, "08:40", "09:20", day="Tuesday")]
        self.fc = forecast(P1=110, P2=50)

    def test_only_the_requested_day_is_planned(self):
        mon = plan_schedule(self.tt, self.fc, NO_ORDER, "I", day="Monday")
        self.assertEqual({c["subject"] for c in mon["classified_periods"]}, {"PE", "Math"})
        self.assertEqual([(s["from_period"], s["to_period"]) for s in mon["plan_a"]], [("P1", "P2")])
        tue = plan_schedule(self.tt, self.fc, NO_ORDER, "I", day="Tuesday")
        self.assertEqual(tue["status"], "confirmed_no_change")  # Tuesday PE is already in the clean slot

    def test_day_without_classes_closes_without_change(self):
        plan = plan_schedule(self.tt, self.fc, NO_ORDER, "I", day="Sunday")
        self.assertEqual(plan["status"], "confirmed_no_change")
        self.assertEqual(plan["message"], "No classes scheduled on Sunday.")

    def test_handler_plans_the_weekday_of_the_date(self):
        monday = lambda_handler({"stage": "III", "date": "2026-10-12"}, None)["decision"]
        self.assertEqual(len(monday["plan_b"]), 6)
        sunday = lambda_handler({"stage": "III", "date": "2026-10-11"}, None)["decision"]
        self.assertEqual((sunday["status"], sunday["day"]), ("confirmed_no_change", "Sunday"))


class TestClassBandRules(unittest.TestCase):

    RULESET = {"jurisdiction": "Delhi", "advisory_pm25": {"advisory_at": 90, "restricted_at": 120},
               "rules": [{"rule_id": "r-primary", "applies_to": ["school"], "class_band": ["primary"],
                          "condition": {"stage_at_least": "III"},
                          "action": {"outdoor_sports": "banned", "outdoor_pt": "banned"}, "source_quote": "q"}]}

    def classify(self, cls):
        return classify_period({"class": cls, "period": "P1", "outdoor": True}, 40, self.RULESET, "III")

    def test_primary_only_rule_does_not_bind_secondary(self):
        self.assertEqual(self.classify("3A")["label"], "banned")
        self.assertEqual(self.classify("9A")["label"], "allowed")

    def test_rule_for_other_sector_is_ignored(self):
        rs = {**self.RULESET, "rules": [dict(self.RULESET["rules"][0], applies_to=["outdoor_crew"], class_band=["all"])]}
        self.assertEqual(classify_period({"class": "3A", "period": "P1", "outdoor": True}, 40, rs, "IV")["label"], "allowed")


class TestExplanationsAndFailClosed(unittest.TestCase):

    def test_every_intervention_is_explained(self):
        tt, fc, rs = _get_demo_fixtures()
        plan = plan_schedule(tt, fc, rs, "II", day="Monday")
        self.assertEqual(len(plan["decision_trace"]), len(plan["plan_a"]) + len(plan["plan_b"]))
        for t in plan["decision_trace"]:
            self.assertIn("nominal", t["forecast_pm25"])
            self.assertTrue(t["reason"])
            self.assertEqual(len(t["candidates"]), 7)  # every other period of the day was considered
            for c in t["candidates"]:
                self.assertIn(c["verdict"], ("chosen", "rejected", "valid"))
                if c["verdict"] == "rejected":
                    self.assertTrue(c["reasons"])
            if t["outcome"]["plan"] == "A":
                self.assertEqual(sum(c["verdict"] == "chosen" for c in t["candidates"]), 1)

    def test_stage_ban_explains_rule_and_quote(self):
        tt, fc, rs = _get_demo_fixtures()
        t = plan_schedule(tt, fc, rs, "III", day="Monday")["decision_trace"][0]
        self.assertEqual(t["rule_ids"], ["r-017"])
        self.assertIn("All outdoor sports and physical education activities", t["reason"])
        self.assertTrue(all("banned" in c["reasons"][0] or c["reasons"][0] in ("locked period",)
                            or "outdoor" in c["reasons"][0] for c in t["candidates"]))

    def test_revalidation_fails_closed(self):
        """If the final day ever shows a new clash, swaps are undone and those classes get Plan B."""
        tt = [row("X", "P1", "PE", "T_PE1", "G1", True, "08:00", "08:40"),
              row("X", "P2", "Math", "T_M", "R1", False, "08:40", "09:20")]
        real, calls = planner.find_conflicts, []

        def flaky(periods):  # input report, baseline and the trial swap are real; the final whole-day check sees a clash
            calls.append(1)
            return real(periods) if len(calls) <= 3 else {("teacher", "T_M", "Monday", "P1"): frozenset({"X", "Z"})}

        planner.find_conflicts = flaky
        try:
            plan = plan_schedule(tt, forecast(P1=110, P2=50), NO_ORDER, "I")
        finally:
            planner.find_conflicts = real
        self.assertEqual(plan["plan_a"], [])
        self.assertEqual([(b["class"], b["period"]) for b in plan["plan_b"]], [("X", "P1")])
        self.assertEqual(plan["revalidation"]["swaps_reverted"], ["X P1->P2"])


if __name__ == "__main__":
    unittest.main()
