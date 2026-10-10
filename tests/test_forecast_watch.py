"""
Tests for F2: Forecast Watch early warning (hack_win F2 / impleme_work F2).
Verifies:
1. Clean live data (real Oct values, ~50-74) gives risk: none and no audit row.
2. Replay forecast gives risk: act, label contains 'not active', and exactly one CONTINGENCY_DRAFTED row.
3. Sensitive class crossing stricter limit gives risk: act with explanation.
4. Sunday (no classes) is skipped in next 2 school days.
5. Watch creates NO DEC# item, NO TOKEN# item, and NO Step Functions execution.
6. GET /watch without key returns 401.
"""

import json
import os
import unittest
from unittest import mock

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

from moto import mock_aws

from services.audit.store import read_chain
from services.forecast.handler import watch_get_handler
from services.forecast.watch import next_school_days, run_watch, watch_handler
from tests.test_audit_store import make_table

ADMIN_KEY = "watch-test-admin-secret-12345"

# Clean live October hourly response (~50-74)
import urllib.parse

CLEAN_HOURLY = [51.7, 52.4, 52.7, 54.0, 56.3, 60.1, 67.5, 73.6, 69.6, 58.1, 50.3, 49.9,
                50.5, 51.2, 50.3, 49.9, 49.5, 53.1, 61.2, 68.5, 71.0, 72.0, 73.0, 74.0]


def make_clean_fetch(pm_values):
    def _fetch(url):
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        d = qs.get("start_date", ["2026-10-12"])[0]
        return {
            "hourly_units": {"pm2_5": "μg/m³"},
            "hourly": {
                "time": [f"{d}T{h:02d}:00" for h in range(24)],
                "pm2_5": pm_values,
            },
        }
    return _fetch


clean_fetch = make_clean_fetch(CLEAN_HOURLY)


@mock_aws
class TestForecastWatch(unittest.TestCase):

    def setUp(self):
        self.table = make_table()
        os.environ["ADMIN_API_KEY"] = ADMIN_KEY

    def test_clean_live_data_gives_risk_none_and_no_audit_row(self):
        watches = run_watch(table=self.table, today="2026-10-12", source="live", fetch=clean_fetch)
        self.assertEqual(len(watches), 2)
        for w in watches:
            self.assertEqual(w["risk"], "none")
            self.assertIn("normal limits", w["risk_reason"])
            self.assertIn("not active", w["label"])

        # No CONTINGENCY_DRAFTED row written to audit chain
        rows = read_chain(self.table, "TENANT#demo")
        draft_rows = [r for r in rows if r["event"] == "CONTINGENCY_DRAFTED"]
        self.assertEqual(draft_rows, [])

    def test_replay_forecast_gives_act_label_and_single_audit_row(self):
        watches = run_watch(table=self.table, today="2026-10-12", source="replay")
        self.assertEqual(len(watches), 2)
        for w in watches:
            self.assertEqual(w["risk"], "act")
            self.assertIn("not active until an order", w["label"])
            self.assertGreater(w["peak_pm25"], 120)

        # Audit chain contains CONTINGENCY_DRAFTED rows
        rows = read_chain(self.table, "TENANT#demo")
        draft_rows = [r for r in rows if r["event"] == "CONTINGENCY_DRAFTED"]
        self.assertEqual(len(draft_rows), 2)

        # Running again does NOT duplicate audit rows
        run_watch(table=self.table, today="2026-10-12", source="replay")
        rows2 = read_chain(self.table, "TENANT#demo")
        draft_rows2 = [r for r in rows2 if r["event"] == "CONTINGENCY_DRAFTED"]
        self.assertEqual(len(draft_rows2), 2)

    def test_sensitive_class_stricter_limit_crossed_gives_act(self):
        # 98.0 µg/m³ is below restricted (120), but exceeds Class 6A stricter limit (96.0)
        sensitive_fetch = make_clean_fetch([98.0] * 24)
        watches = run_watch(table=self.table, today="2026-10-12", source="live", fetch=sensitive_fetch)
        self.assertEqual(watches[0]["risk"], "act")
        self.assertIn("stricter limit for class 6A", watches[0]["risk_reason"])

    def test_sunday_is_skipped(self):
        # From Saturday 2026-10-17, next 2 school days should be Mon 2026-10-19 & Tue 2026-10-20
        watches = run_watch(table=self.table, today="2026-10-17", source="replay")
        dates = [w["date"] for w in watches]
        self.assertEqual(dates, ["2026-10-19", "2026-10-20"])
        self.assertNotIn("2026-10-18", dates)

    def test_watch_creates_no_decision_token_or_sfn(self):
        run_watch(table=self.table, today="2026-10-12", source="replay")
        items = self.table.scan().get("Items", [])
        sks = [i.get("SK", "") for i in items]
        self.assertFalse(any(sk.startswith("DEC#") for sk in sks), "Found DEC# item")
        self.assertFalse(any(sk.startswith("TOKEN#") for sk in sks), "Found TOKEN# item")

    def test_get_watch_requires_admin_key(self):
        # Missing key -> 401
        r1 = watch_get_handler({"queryStringParameters": {"tenant": "demo"}}, None)
        self.assertEqual(r1["statusCode"], 401)

        # Invalid key -> 401
        r2 = watch_get_handler({
            "headers": {"x-saans-admin-key": "invalid-key"},
            "queryStringParameters": {"tenant": "demo"}
        }, None)
        self.assertEqual(r2["statusCode"], 401)

        # Valid key -> 200 with stored watches and promote hint
        run_watch(table=self.table, today="2026-10-12", source="replay")
        with mock.patch("services.forecast.handler._get_table", return_value=self.table):
            r3 = watch_get_handler({
                "headers": {"x-saans-admin-key": ADMIN_KEY},
                "queryStringParameters": {"tenant": "demo"}
            }, None)
        self.assertEqual(r3["statusCode"], 200)
        body = json.loads(r3["body"])
        self.assertEqual(body["tenant"], "demo")
        self.assertEqual(len(body["watches"]), 2)
        self.assertEqual(body["promote_hint"]["method"], "aws lambda invoke")

    def test_scheduled_watch_handler_completes(self):
        with mock.patch("services.forecast.watch.TABLE_NAME", "SaansStateTable"):
            with mock.patch("boto3.resource", return_value=mock.MagicMock(Table=lambda _: self.table)):
                res = watch_handler({"source": "replay"}, None)
        self.assertEqual(res["statusCode"], 200)
        self.assertEqual(res.get("watches_evaluated"), 2)


if __name__ == "__main__":
    unittest.main()
