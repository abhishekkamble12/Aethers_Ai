"""
Regression tests for four bugs found in review of the forecast watch and notice drafting:

1. The watch plan_summary was always zeros: it read planner keys that do not exist.
2. The teacher sentence never appeared: classes_with_stricter_limits read a key the planner never returns.
3. The hand-built replay scenario was labelled as a SAFAR-IITM model forecast.
4. The /watch promote hint pointed at POST /workflow/trigger, a route that does not exist.

Each test fails on the old code and passes on the fix.
"""

import json
import os
import pathlib
import unittest
from unittest import mock

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

from moto import mock_aws

from services.forecast.handler import watch_get_handler
from services.forecast.ingest import get_forecast, get_hourly_forecast
from services.forecast.watch import run_watch
from services.notify.drafting import draft_notice, plan_facts
from services.planner.handler import _get_demo_fixtures, _get_school_config, parse_run_input
from services.planner.planner import plan_schedule
from tests.test_audit_store import make_table

ADMIN_KEY = "regression-admin-secret-12345"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def replay_plan():
    """The real Stage III replay plan for the demo school, built exactly as the watch builds it."""
    timetable, _, ruleset = _get_demo_fixtures()
    cfg = _get_school_config()
    fc = get_forecast("2026-10-12", timetable, source="replay")
    return plan_schedule(timetable=timetable, forecast=fc, ruleset=ruleset, declared_stage="III", delta=0.20,
                         venues=cfg["venues"], indoor_air=cfg["indoor_air"], class_sizes=cfg["class_sizes"],
                         sensitive_counts=cfg["sensitive_counts"], sensitivity_policy=cfg["sensitivity_policy"])


@mock_aws
class TestWatchPlanSummary(unittest.TestCase):
    """Problem 1."""

    def test_replay_watch_summary_reports_the_rehearsed_plan(self):
        plan = replay_plan()
        watches = run_watch(table=make_table(), today="2026-10-12", source="replay")
        summary = watches[0]["plan_summary"]
        self.assertGreater(summary["problematic_count"], 0)
        self.assertEqual(summary["swaps_count"], len(plan["plan_a"]))
        self.assertEqual(summary["fallbacks_count"], len(plan["plan_b"]))
        self.assertGreater(summary["swaps_count"] + summary["fallbacks_count"], 0)


class TestTeacherSentence(unittest.TestCase):
    """Problem 2."""

    def test_classes_with_stricter_limits_counts_distinct_classes(self):
        plan = replay_plan()
        expected = {t["class"] for t in plan["decision_trace"] if t.get("sensitivity")}
        self.assertGreater(len(expected), 0, "demo data should exercise the stricter-limit path")
        self.assertEqual(plan_facts(plan)["classes_with_stricter_limits"], len(expected))

    def test_teacher_notice_includes_stricter_limit_sentence(self):
        plan = replay_plan()
        notice = draft_notice(plan, audience="teachers", language="english", force_fallback=True)
        self.assertIn("Stricter limits applied to", notice["notice_text"])

    def test_teacher_sentence_absent_when_no_class_is_stricter(self):
        notice = draft_notice({"plan_a": [], "plan_b": [], "decision_trace": []}, audience="teachers",
                              force_fallback=True)
        self.assertNotIn("Stricter limits", json.dumps(notice, ensure_ascii=False))


class TestReplayLabel(unittest.TestCase):
    """Problem 3."""

    def test_hourly_replay_does_not_claim_a_real_model(self):
        fc = get_hourly_forecast(source="replay", hours=24)
        self.assertNotIn("SAFAR", fc["model"])
        self.assertIn("not a model forecast", fc["model"])

    def test_period_replay_fixture_does_not_claim_a_real_model(self):
        data = json.loads((ROOT / "data" / "demo" / "forecast_stage3_sample.json").read_text(encoding="utf-8"))
        self.assertNotIn("SAFAR", data["model"])

    def test_live_failure_fallback_is_labelled_the_same_way(self):
        def broken(url):
            raise OSError("network down")
        fc = get_hourly_forecast(source="live", hours=24, fetch=broken)
        self.assertEqual(fc["source"], "replay")
        self.assertNotIn("SAFAR", fc["model"])


@mock_aws
class TestPromoteHint(unittest.TestCase):
    """Problem 4."""

    def test_hint_names_the_trigger_lambda_with_valid_payloads(self):
        table = make_table()
        os.environ["ADMIN_API_KEY"] = ADMIN_KEY
        run_watch(table=table, today="2026-10-12", source="replay")
        with mock.patch.dict(os.environ, {"TRIGGER_FUNCTION_NAME": "saans-TriggerFunction-abc"}), \
                mock.patch("services.forecast.handler._get_table", return_value=table):
            r = watch_get_handler({"headers": {"x-saans-admin-key": ADMIN_KEY},
                                   "queryStringParameters": {"tenant": "demo"}}, None)
        body = json.loads(r["body"])
        hint = body["promote_hint"]
        self.assertIsInstance(body["watches"][0]["plan_summary"]["fallbacks_count"], int)
        self.assertIsInstance(body["watches"][0]["peak_pm25"], (int, float))
        self.assertNotIn("/workflow/trigger", json.dumps(hint))
        self.assertEqual(hint["function_name"], "saans-TriggerFunction-abc")
        self.assertIn("saans-TriggerFunction-abc", hint["example"])
        self.assertIn("OutputKey=='TriggerFunctionName'", hint["find_function_name"])
        self.assertEqual([p["date"] for p in hint["payloads"]], ["2026-10-13", "2026-10-14"])
        for payload in hint["payloads"]:
            run = parse_run_input(payload)  # the Trigger Lambda accepts exactly this
            self.assertEqual(run["tenant_id"], "TENANT#demo")


class TestTemplateHasNoTriggerCycle(unittest.TestCase):
    """!Ref TriggerFunction from an API-backed function creates a CloudFormation dependency cycle."""

    def test_watch_api_does_not_reference_trigger_function(self):
        tpl = (ROOT / "infra" / "template.yaml").read_text(encoding="utf-8")
        watch_api = tpl.split("  WatchApiFunction:")[1].split(chr(10) + "  # ")[0]
        self.assertNotIn("!Ref TriggerFunction", watch_api)


class TestNoSecretsInScripts(unittest.TestCase):
    """The deployed admin key must never be committed in a script."""

    def test_live_api_script_reads_key_from_environment_or_secrets_file(self):
        src = (ROOT / "scripts" / "test_live_api.py").read_text(encoding="utf-8")
        self.assertNotRegex(src, r'ADMIN_KEY\s*=\s*"[A-Za-z0-9_-]{16,}"')
        self.assertIn("SAANS_ADMIN_KEY", src)


if __name__ == "__main__":
    unittest.main()
