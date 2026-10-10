"""
Tests for F3: GET /forecast chart data endpoint (hack_win M4 / impleme_work F3).
Verifies:
1. Live stub of 48 hourly values: shape, unit, school_hours flags, first_crossing.
2. Fetch failure gives source: replay plus reason and HTTP 200.
3. Bad hours or source returns 400 JSON error.
4. No sensitive_count and no class names in response (DPDP privacy).
5. Cache hit within 1h; refetch after.
"""

import json
import os
import unittest
from unittest import mock

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

from moto import mock_aws

import services.forecast.handler as handler
from services.forecast.handler import forecast_handler
from services.forecast.ingest import get_hourly_forecast
from tests.test_audit_store import make_table

# 48 hours of clean October PM2.5 (no value crosses 120; hour 21 reaches 98)
OCT_24 = [51.7, 52.4, 52.7, 54.0, 56.3, 60.1, 67.5, 73.6, 69.6, 58.1, 50.3, 49.9,
          50.5, 51.2, 50.3, 49.9, 49.5, 53.1, 61.2, 68.5, 76.6, 85.9, 94.8, 98.0]
CLEAN_48_PM = OCT_24 + [round(v * 1.05, 1) for v in OCT_24]

TIMES_48 = [f"2026-10-12T{h:02d}:00" for h in range(24)] + [f"2026-10-13T{h:02d}:00" for h in range(24)]

STUB_48_RESPONSE = {
    "hourly_units": {"pm2_5": "μg/m³"},
    "hourly": {
        "time": TIMES_48,
        "pm2_5": CLEAN_48_PM
    }
}


def stub_clean_fetch(_url):
    return STUB_48_RESPONSE


@mock_aws
class TestForecastApi(unittest.TestCase):

    def setUp(self):
        self.table = make_table()

    def test_live_48_hours_shape_unit_flags_crossing(self):
        with mock.patch("services.forecast.ingest.http_get_json", side_effect=stub_clean_fetch):
            event = {"queryStringParameters": {"tenant": "demo", "hours": "48", "source": "live"}}
            resp = forecast_handler(event, None)

        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(body["source"], "live")
        self.assertEqual(body["label"], "live forecast")
        self.assertEqual(body["unit"], "µg/m³ (PM2.5, hourly mean)")
        self.assertIsNone(body["fallback_reason"])
        self.assertEqual(len(body["hours"]), 48)

        # Hour flags: 08:00 is school hour; 00:00 and 15:00 are not
        h0 = body["hours"][0]
        self.assertFalse(h0["school_hours"])
        h8 = body["hours"][8]
        self.assertTrue(h8["school_hours"])
        h14 = body["hours"][14]
        self.assertTrue(h14["school_hours"])
        h15 = body["hours"][15]
        self.assertFalse(h15["school_hours"])

        # Clean October air does not cross restricted threshold (120)
        self.assertEqual(body["first_crossing"]["threshold"], "restricted")
        self.assertIsNone(body["first_crossing"]["time"])

        # Thresholds structure
        names = [t["name"] for t in body["thresholds"]]
        self.assertIn("advisory", names)
        self.assertIn("restricted", names)
        self.assertTrue(any("stricter limit" in n for n in names))
        self.assertEqual(body["note"], "Saans never declares a GRAP stage; thresholds decide advisory/restricted only within what the order allows.")

    def test_first_crossing_detected_when_threshold_exceeded(self):
        # Spike PM2.5 at hour 10 to 142.0 (crosses 120)
        spiked_pm = list(CLEAN_48_PM)
        spiked_pm[10] = 142.0
        spiked_resp = {
            "hourly_units": {"pm2_5": "μg/m³"},
            "hourly": {"time": TIMES_48, "pm2_5": spiked_pm}
        }
        with mock.patch("services.forecast.ingest.http_get_json", return_value=spiked_resp):
            event = {"queryStringParameters": {"hours": "48", "source": "live"}}
            resp = forecast_handler(event, None)

        body = json.loads(resp["body"])
        self.assertEqual(body["first_crossing"]["threshold"], "restricted")
        self.assertIn("2026-10-12T10:00", body["first_crossing"]["time"])

    def test_fetch_failure_gives_replay_and_200(self):
        def timeout_fetch(_url):
            raise TimeoutError("connection timed out after 5s")

        with mock.patch("services.forecast.ingest.http_get_json", side_effect=timeout_fetch):
            event = {"queryStringParameters": {"tenant": "demo", "hours": "48", "source": "live"}}
            resp = forecast_handler(event, None)

        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(body["source"], "replay")
        self.assertIn("TimeoutError", body["fallback_reason"])
        self.assertEqual(len(body["hours"]), 48)
        # In Stage III replay, peak hours cross restricted (120)
        self.assertIsNotNone(body["first_crossing"]["time"])

    def test_explicit_replay_gives_replay_data(self):
        event = {"queryStringParameters": {"tenant": "demo", "hours": "48", "source": "replay"}}
        resp = forecast_handler(event, None)

        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(body["source"], "replay")
        self.assertIsNone(body["fallback_reason"])
        self.assertEqual(len(body["hours"]), 48)

    def test_bad_parameters_return_400_json(self):
        bad_cases = [
            ({"hours": "not_a_number"}, "invalid_hours"),
            ({"hours": "0"}, "invalid_hours"),
            ({"hours": "200"}, "invalid_hours"),
            ({"source": "satellite"}, "invalid_source"),
            ({"tenant": "bad tenant name with spaces!"}, "invalid_tenant"),
        ]
        for params, expected_code in bad_cases:
            event = {"queryStringParameters": params}
            resp = forecast_handler(event, None)
            self.assertEqual(resp["statusCode"], 400, f"Failed on {params}")
            err = json.loads(resp["body"]).get("error", {})
            self.assertEqual(err.get("code"), expected_code)

    def test_dpdp_privacy_no_sensitive_count_or_class_names(self):
        with mock.patch("services.forecast.ingest.http_get_json", side_effect=stub_clean_fetch):
            event = {"queryStringParameters": {"tenant": "demo", "hours": "48"}}
            resp = forecast_handler(event, None)

        raw = resp["body"]
        self.assertNotIn("sensitive_count", raw)
        self.assertNotIn("students", raw)
        self.assertNotIn("6A", raw)
        self.assertNotIn("7B", raw)
        self.assertNotIn("9A", raw)

        body = json.loads(raw)
        stricter = next(t for t in body["thresholds"] if "stricter limit" in t["name"])
        # Demo school classes with sensitive students produce distinct thresholds [96.0, 108.0, 114.0]
        self.assertEqual(stricter["values"], [96.0, 108.0, 114.0])
        self.assertEqual(stricter["basis"], "policy")


@mock_aws
class TestForecastCache(unittest.TestCase):

    def setUp(self):
        self.table = make_table()

    def test_cache_hit_within_1h_and_refetch_after(self):
        call_count = 0

        def counting_fetch(_url):
            nonlocal call_count
            call_count += 1
            return STUB_48_RESPONSE

        # Call 1: at t = 1,791,000,000 (cache miss, calls fetch)
        r1 = get_hourly_forecast(
            tenant_id="demo",
            hours=48,
            source="live",
            table=self.table,
            fetch=counting_fetch,
            now=1_791_000_000.0,
        )
        self.assertEqual(call_count, 1)
        self.assertEqual(r1["cache"], "miss")

        # Call 2: at t = 1,791,000,000 + 1800 (30 min later, cache hit, does not call fetch)
        r2 = get_hourly_forecast(
            tenant_id="demo",
            hours=48,
            source="live",
            table=self.table,
            fetch=counting_fetch,
            now=1_791_001_800.0,
        )
        self.assertEqual(call_count, 1)
        self.assertEqual(r2["cache"], "hit")
        self.assertEqual(len(r2["hours"]), 48)

        # Call 3: at t = 1,791,000,000 + 3601 (60 min 1 sec later, cache expired, calls fetch again)
        r3 = get_hourly_forecast(
            tenant_id="demo",
            hours=48,
            source="live",
            table=self.table,
            fetch=counting_fetch,
            now=1_791_003_601.0,
        )
        self.assertEqual(call_count, 2)
        self.assertEqual(r3["cache"], "miss")


if __name__ == "__main__":
    unittest.main()
