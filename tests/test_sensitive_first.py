"""
hack_win X3: classes with students who have respiratory conditions get stricter forecast limits and
first pick of clean slots and rooms. Counts only; never in public responses or the public audit chain.
"""

import json
import os
import unittest

from services.planner.handler import (_get_school_config, lambda_handler, redact_sensitive_counts,
                                      rehearse_handler, validate_class_profiles)
from services.planner.planner import plan_schedule, sensitivity_multiplier

POLICY = {"basis": "policy", "per_student": 0.05, "floor": 0.6}
RULES = {"jurisdiction": "Delhi", "advisory_pm25": {"advisory_at": 90, "restricted_at": 120}, "rules": []}


def row(cls, prd, subject, teacher, venue, outdoor):
    return {"class": cls, "day": "Monday", "period": prd, "start": "09:00", "end": "09:40", "subject": subject,
            "teacher_code": teacher, "venue": venue, "outdoor": outdoor, "locked": False}


class TestStricterLimits(unittest.TestCase):

    def test_multiplier_policy(self):
        self.assertEqual([sensitivity_multiplier(n, POLICY) for n in (0, 1, 4, 20)], [1.0, 0.95, 0.8, 0.6])
        self.assertEqual(sensitivity_multiplier(3, {"per_student": -0.5, "floor": 0.6}), 1.0)  # never laxer

    def test_marginal_slot_is_refused_for_the_sensitive_class_only(self):
        # Both classes have PE in polluted P1. In P2 the nominal forecast (90) is under both limits, but the
        # pessimistic one (110) is over the stricter limit for a class with 4 sensitive students (96, not 120).
        tt = [row("S", "P1", "PE", "T1", "G1", True), row("S", "P2", "Math", "T2", "R1", False),
              row("N", "P1", "PE", "T3", "G2", True), row("N", "P2", "Eng", "T4", "R2", False)]
        fc = {"periods": [{"period": "P1", "pm25_nominal": 300, "pm25_pessimistic": 330},
                          {"period": "P2", "pm25_nominal": 90, "pm25_pessimistic": 110}]}
        res = plan_schedule(tt, fc, RULES, "I", sensitive_counts={"S": 4}, sensitivity_policy=POLICY)
        self.assertEqual([(s["class"], s["to_period"]) for s in res["plan_a"]], [("N", "P2")])
        self.assertEqual([b["class"] for b in res["plan_b"]], ["S"])
        trace = next(t for t in res["decision_trace"] if t["class"] == "S")
        self.assertEqual((trace["sensitivity"]["restricted_at"], trace["sensitivity"]["threshold_multiplier"]), (96.0, 0.8))
        self.assertIn("stricter threshold applied: 4 sensitive students", trace["sensitivity"]["applied"])
        p2 = next(c for c in trace["candidates"] if c["period"] == "P2")
        self.assertIn("pessimistic forecast: restricted", p2["reasons"][0])
        self.assertIn("(96.0", p2["reasons"][0])

    def test_stage_ban_is_unaffected(self):
        ban = {**RULES, "rules": [{"rule_id": "r-ban", "applies_to": ["school"], "class_band": ["all"],
                                   "condition": {"stage_at_least": "III"},
                                   "action": {"outdoor_sports": "banned", "outdoor_pt": "banned"}, "source_quote": "q"}]}
        tt = [row("S", "P1", "PE", "T1", "G1", True), row("N", "P1", "PE", "T2", "G2", True)]
        fc = {"periods": [{"period": "P1", "pm25_nominal": 10, "pm25_pessimistic": 12}]}
        res = plan_schedule(tt, fc, ban, "III", sensitive_counts={"S": 4}, sensitivity_policy=POLICY)
        self.assertEqual({c["class"]: c["label"] for c in res["classified_periods"]}, {"S": "banned", "N": "banned"})

    def test_sensitive_classes_choose_slots_first(self):
        tt = [row("N", "P1", "PE", "T1", "G1", True), row("N", "P2", "Math", "T2", "R1", False),
              row("S", "P1", "PE", "T1b", "G1b", True), row("S", "P2", "Eng", "T3", "R2", False)]
        tt[0]["teacher_code"] = tt[2]["teacher_code"] = "T_PE"  # one PE teacher: only one class can move to P2
        tt[2]["class"] = "S"
        fc = {"periods": [{"period": "P1", "pm25_nominal": 300, "pm25_pessimistic": 330},
                          {"period": "P2", "pm25_nominal": 40, "pm25_pessimistic": 50}]}
        res = plan_schedule(tt, fc, RULES, "I", sensitive_counts={"S": 2}, sensitivity_policy=POLICY)
        self.assertEqual([s["class"] for s in res["plan_a"]], ["S"])


class TestPrivacy(unittest.TestCase):

    def test_profiles_reject_anything_but_counts(self):
        for bad in ({"class": "6A", "students": 38, "sensitive_count": 1, "names": ["A"]},
                    {"class": "6A", "students": 38, "sensitive_count": 50},
                    {"class": "6A", "students": 38, "sensitive_count": -1},
                    {"class": "6A", "students": "38"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_class_profiles([bad])

    def test_public_rehearsal_redacts_counts_but_keeps_thresholds(self):
        body = json.loads(rehearse_handler({"httpMethod": "POST", "body": json.dumps({"stage": "II"})}, None)["body"])
        sens = [t["sensitivity"] for t in body["decision_trace"] if t.get("sensitivity")]
        self.assertTrue(sens)
        for sv in sens:
            self.assertEqual(sv["sensitive_count"], "redacted")
            self.assertNotRegex(sv["applied"], r"\d+ sensitive student")
            self.assertIn("restricted", sv["applied"])

    def test_admin_plan_keeps_counts(self):
        d = lambda_handler({"stage": "II", "date": "2026-10-12"}, None)["decision"]
        six_a = next(t for t in d["decision_trace"] if t["class"] == "6A")
        self.assertEqual(six_a["sensitivity"]["sensitive_count"], 4)

    def test_audit_chain_gets_policy_not_counts(self):
        from moto import mock_aws
        os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
        from services.audit.store import read_chain
        from tests.test_audit_store import make_table
        with mock_aws():
            table = make_table()
            os.environ.update(TABLE_NAME="SaansStateTable", AWS_LAMBDA_FUNCTION_NAME="local-test")
            try:
                lambda_handler({"stage": "II", "date": "2026-10-12"}, None)
            finally:
                os.environ.pop("AWS_LAMBDA_FUNCTION_NAME")
            payload = read_chain(table, "TENANT#demo")[0]["payload"]
        self.assertEqual(payload["sensitivity_policy"], {"basis": "policy", "per_student": 0.05, "floor": 0.6})
        self.assertEqual(payload["classes_with_stricter_limits"], 3)
        self.assertNotIn("sensitive_count", json.dumps(payload))

    def test_demo_config_is_valid(self):
        cfg = _get_school_config()
        self.assertEqual(cfg["sensitive_counts"]["6A"], 4)
        self.assertEqual(redact_sensitive_counts({"decision_trace": []}), {"decision_trace": []})


if __name__ == "__main__":
    unittest.main()
