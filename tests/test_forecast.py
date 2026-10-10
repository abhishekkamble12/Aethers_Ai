"""
hack_win X4: live Open-Meteo forecast mapped onto periods, cached, with an automatic labelled replay fallback.
The HTTP call is stubbed with a response in the API's real shape (captured on Oct 10, 2026).
"""

import json
import os
import unittest
from unittest import mock

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

from moto import mock_aws  # noqa: E402

import services.forecast.ingest as ingest  # noqa: E402
from services.forecast.ingest import get_forecast, map_hourly_to_periods, period_windows  # noqa: E402
from services.planner.handler import _get_demo_fixtures, lambda_handler, parse_run_input, rehearse_handler  # noqa: E402

# Open-Meteo response for central Delhi, 2026-10-12 (hourly PM2.5, IST)
REAL_PM = [51.7, 52.4, 52.7, 54.0, 56.3, 60.1, 67.5, 73.6, 69.6, 58.1, 50.3, 49.9, 50.5, 51.2, 50.3, 49.9,
           49.5, 53.1, 61.2, 68.5, 76.6, 85.9, 94.8, 98.0]
API_RESPONSE = {"hourly_units": {"pm2_5": "μg/m³"},
                "hourly": {"time": [f"2026-10-12T{h:02d}:00" for h in range(24)], "pm2_5": REAL_PM}}
TIMETABLE, _, _ = _get_demo_fixtures()


def ok(_url):
    return API_RESPONSE


class TestMapping(unittest.TestCase):

    def test_minute_weighted_average(self):
        # P1 08:30-09:10 = 30 min of 08h (69.6) + 10 min of 09h (58.1)
        periods = map_hourly_to_periods(API_RESPONSE["hourly"], "2026-10-12", period_windows(TIMETABLE), 0.2)
        p1 = periods[0]
        self.assertEqual(p1["period"], "P1")
        self.assertEqual(p1["pm25_nominal"], round((30 * 69.6 + 10 * 58.1) / 40, 1))
        self.assertEqual(p1["pm25_pessimistic"], round(p1["pm25_nominal"] * 1.2, 1))
        self.assertEqual([p["period"] for p in periods], [f"P{i}" for i in range(1, 9)])

    def test_missing_hour_is_an_error_not_a_guess(self):
        hourly = {"time": API_RESPONSE["hourly"]["time"], "pm2_5": [None if h == 9 else v for h, v in enumerate(REAL_PM)]}
        with self.assertRaises(ValueError):
            map_hourly_to_periods(hourly, "2026-10-12", period_windows(TIMETABLE), 0.2)


class TestLiveAndFallback(unittest.TestCase):

    def test_live_forecast(self):
        fc = get_forecast("2026-10-12", TIMETABLE, "live", fetch=ok, now=1_791_000_000)
        self.assertFalse(fc["is_replay"])
        self.assertIsNone(fc["fallback_reason"])
        self.assertIn("Open-Meteo", fc["model"])
        self.assertIn("latitude=28.6139", fc["source_url"])
        self.assertEqual(len(fc["periods"]), 8)

    def test_fallbacks_are_automatic_and_labelled(self):
        def timeout(_):
            raise TimeoutError("timed out")

        def beyond_horizon(_):
            return {"error": True, "reason": "Parameter 'start_date' is out of allowed range from 2013-01-01 to 2026-10-16"}

        def gap(_):
            return {"hourly": {"time": API_RESPONSE["hourly"]["time"][:9], "pm2_5": REAL_PM[:9]}}

        for fetch, expect in ((timeout, "TimeoutError"), (beyond_horizon, "out of allowed range"), (gap, "no PM2.5 value")):
            fc = get_forecast("2026-10-12", TIMETABLE, "live", fetch=fetch)
            self.assertTrue(fc["is_replay"], expect)
            self.assertEqual(fc["requested_source"], "live")
            self.assertIn(expect, fc["fallback_reason"])

    def test_http_error_body_reason_is_kept(self):
        import io
        import urllib.error
        body = io.BytesIO(json.dumps({"error": True, "reason": "Parameter 'start_date' is out of allowed range"}).encode())
        err = urllib.error.HTTPError("u", 400, "Bad Request", {}, body)
        with mock.patch("urllib.request.urlopen", side_effect=err):
            fc = get_forecast("2026-11-30", TIMETABLE, "live")
        self.assertEqual(fc["fallback_reason"], "ValueError: HTTP 400: Parameter 'start_date' is out of allowed range")

    def test_explicit_replay(self):
        fc = get_forecast("2026-10-12", TIMETABLE, "replay")
        self.assertEqual((fc["is_replay"], fc["requested_source"], fc["fallback_reason"]), (True, "replay", None))

    def test_bad_source_rejected(self):
        with self.assertRaises(ValueError):
            get_forecast("2026-10-12", TIMETABLE, "satellite")
        with self.assertRaises(ValueError):
            parse_run_input({"forecast_source": "satellite"})


@mock_aws
class TestCacheAndAudit(unittest.TestCase):

    def setUp(self):
        from tests.test_audit_store import make_table
        self.table = make_table()

    def test_cache_hit_then_refresh_when_stale(self):
        calls = []

        def counting(url):
            calls.append(url)
            return API_RESPONSE
        t0 = 1_791_000_000
        self.assertEqual(get_forecast("2026-10-12", TIMETABLE, "live", table=self.table, fetch=counting, now=t0)["cache"], "miss")
        self.assertEqual(get_forecast("2026-10-12", TIMETABLE, "live", table=self.table, fetch=counting, now=t0 + 3600)["cache"], "hit")
        self.assertEqual(get_forecast("2026-10-12", TIMETABLE, "live", table=self.table, fetch=counting, now=t0 + 7 * 3600)["cache"], "miss")
        self.assertEqual(len(calls), 2)

    def test_fallback_is_written_to_the_audit_chain(self):
        from services.audit.store import read_chain
        os.environ.update(TABLE_NAME="SaansStateTable", AWS_LAMBDA_FUNCTION_NAME="local-test")
        try:
            with mock.patch.object(ingest, "http_get_json", side_effect=TimeoutError("timed out")):
                out = lambda_handler({"stage": "III", "date": "2026-10-12", "forecast_source": "live",
                                      "execution": "exec-1"}, None)
        finally:
            os.environ.pop("AWS_LAMBDA_FUNCTION_NAME")
        events = [(r["event"], r["payload"]) for r in read_chain(self.table, "TENANT#demo")]
        self.assertEqual([e for e, _ in events], ["FORECAST_FALLBACK_REPLAY", "PLAN_GENERATED"])
        self.assertIn("TimeoutError", events[0][1]["reason"])
        self.assertTrue(events[1][1]["forecast"]["is_replay"])
        self.assertTrue(out["decision"]["forecast"]["label"].startswith("REPLAY SCENARIO"))

    def test_live_plan_uses_live_values(self):
        os.environ.update(TABLE_NAME="SaansStateTable", AWS_LAMBDA_FUNCTION_NAME="local-test")
        try:
            with mock.patch.object(ingest, "http_get_json", side_effect=ok):
                d = lambda_handler({"stage": "II", "date": "2026-10-12", "forecast_source": "live"}, None)["decision"]
        finally:
            os.environ.pop("AWS_LAMBDA_FUNCTION_NAME")
        self.assertEqual(d["forecast"]["label"], "live forecast")
        # Real October air in central Delhi (~50-74 ug/m3) is under every limit at Stage II: no change needed.
        self.assertEqual(d["status"], "confirmed_no_change")
        self.assertTrue(all(p["pm25_nominal"] < 90 for p in d["forecast"]["periods"]))


class TestRehearsal(unittest.TestCase):

    def test_rehearsal_is_labelled_replay_by_default(self):
        body = json.loads(rehearse_handler({"httpMethod": "POST", "body": json.dumps({"stage": "III"})}, None)["body"])
        self.assertTrue(body["forecast"]["label"].startswith("REPLAY SCENARIO"))

    def test_rehearsal_rejects_unknown_source(self):
        resp = rehearse_handler({"httpMethod": "POST", "body": json.dumps({"stage": "III", "forecast_source": "x"})}, None)
        self.assertEqual(resp["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
