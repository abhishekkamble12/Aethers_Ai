"""
hack_win M5: measured PE minutes, exact PE detection, notices that state only plan facts and link only
to our own receipt page.
"""

import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import services.planner.planner as planner
from services.notify import drafting
from services.planner.handler import _get_demo_fixtures
from services.planner.planner import is_pe_period, plan_schedule

ROOT = Path(__file__).resolve().parent.parent


class TestPeMinutes(unittest.TestCase):

    def setUp(self):
        self.tt, self.fc, self.rs = _get_demo_fixtures()

    def test_breakdown_is_measured_and_adds_up(self):
        for stage, moved, indoor in (("I", 80, 160), ("III", 0, 240)):
            pe = plan_schedule(self.tt, self.fc, self.rs, stage, day="Monday")["pe_minutes"]
            self.assertEqual(pe["scheduled"], 240)
            self.assertEqual((pe["moved_to_cleaner_slot"], pe["replaced_indoor_active"], pe["lost"]), (moved, indoor, 0))
            self.assertEqual(pe["kept_active"], pe["unchanged"] + pe["moved_to_cleaner_slot"] + pe["replaced_indoor_active"])

    def test_seated_replacement_counts_as_lost(self):
        seated = {band: [{"name": "Chess", "physical": False}] for band in planner.DEFAULT_INDOOR_ACTIVITIES}
        with mock.patch.dict(planner.DEFAULT_INDOOR_ACTIVITIES, seated):
            res = plan_schedule(self.tt, self.fc, self.rs, "III", day="Monday")
        self.assertEqual(res["pe_minutes"]["lost"], 240)
        self.assertEqual(res["pe_minutes_preserved"], 0.0)

    def test_default_bank_is_physical_only(self):
        for band, items in planner.DEFAULT_INDOOR_ACTIVITIES.items():
            for item in items:
                self.assertTrue(item["physical"], item)
                self.assertNotRegex(item["name"], r"(?i)chess|carrom|lecture|audio-visual|workshop")

    def test_pe_detection_is_exact(self):
        for subject in ("Speech", "Optics", "Experiment Lab", "Computer", "Depth Studies"):
            self.assertFalse(is_pe_period({"subject": subject}), subject)
        for subject in ("Physical Education", "PE", "PT", "Games"):
            self.assertTrue(is_pe_period({"subject": subject}), subject)


class TestNotices(unittest.TestCase):

    PLAN = {"decision_id": "TENANT#demo#2026-10-12#MORN", "plan_a": [], "plan_b": [{"class": "7A"}] * 6,
            "exposure_reduction_pct": 100.0,
            "pe_minutes": {"scheduled": 240, "kept_active": 240}}

    def test_no_foreign_or_government_domains(self):
        src = (ROOT / "services/notify/drafting.py").read_text(encoding="utf-8")
        self.assertNotIn("gov.in", src)
        for lang in ("english", "hindi"):
            n = drafting.draft_notice(self.PLAN, language=lang, receipt_id="AbCdEfGh1234",
                                      public_base_url="https://api.example/Prod", force_fallback=True)
            self.assertNotIn("gov.in", n["notice_text"])
            self.assertIn("https://api.example/Prod/verify/AbCdEfGh1234", n["notice_text"])
            self.assertEqual(n["verify_url"], "https://api.example/Prod/verify/AbCdEfGh1234")

    def test_no_link_when_receipt_or_base_url_missing(self):
        for kwargs in ({"receipt_id": None, "public_base_url": "https://x"}, {"receipt_id": "AbCdEfGh1234", "public_base_url": ""}):
            n = drafting.draft_notice(self.PLAN, force_fallback=True, **kwargs)
            self.assertIsNone(n["verify_url"])
            self.assertNotIn("http", n["notice_text"])
            self.assertNotIn("{", n["notice_text"])

    def test_teacher_and_hindi_templates_render(self):
        for audience, lang in (("teachers", "english"), ("teachers", "hindi"), ("parents", "hindi")):
            n = drafting.draft_notice(self.PLAN, audience=audience, language=lang, force_fallback=True)
            self.assertNotIn("{", n["notice_text"])
            self.assertIn("III", n["notice_text"])

    def test_teacher_notice_uses_the_decision_date(self):
        n = drafting.draft_notice({**self.PLAN, "decision_id": "TENANT#demo#2026-11-03#MORN"},
                                  audience="teachers", force_fallback=True)
        self.assertIn("(2026-11-03)", n["notice_text"])

    def test_model_prompt_states_only_plan_facts(self):
        captured = {}

        class FakeClient:
            def invoke_model(self, **kw):
                captured["body"] = json.loads(kw["body"])
                text = "Dear parents, outdoor PE is replaced by indoor physical sessions today."
                return {"body": io.BytesIO(json.dumps({"output": {"message": {"content": [{"text": text}]}}}).encode())}

        fake_boto3 = types.SimpleNamespace(client=lambda *a, **k: FakeClient())
        with mock.patch.dict(sys.modules, {"boto3": fake_boto3}):
            n = drafting.draft_notice(self.PLAN, receipt_id="AbCdEfGh1234", public_base_url="https://api.example/Prod")
        prompt = captured["body"]["messages"][0]["content"][0]["text"]
        self.assertNotIn("100% of physical education", prompt)
        self.assertIn("6 outdoor activity periods were replaced", prompt)
        self.assertIn("240 of 240 scheduled PE minutes", prompt)
        self.assertIn("https://api.example/Prod/verify/AbCdEfGh1234", prompt)
        self.assertFalse(n["fallback_used"])
        self.assertEqual(n["facts"]["periods_replaced_indoor"], 6)


class TestNoFabricatedScale(unittest.TestCase):

    def test_scale_simulator_is_gone(self):
        self.assertFalse((ROOT / "services/drills/tenant_scale_sim.py").exists())
        self.assertNotIn("400,000", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_notify_has_no_public_route_and_links_to_own_api(self):
        tpl = (ROOT / "infra/template.yaml").read_text(encoding="utf-8")
        notify = tpl.split("  NotificationFunction:", 1)[1].split("\n  # ", 1)[0]
        self.assertNotIn("Type: Api", notify)
        self.assertIn('PUBLIC_BASE_URL: !Sub "https://${ServerlessRestApi}', notify)
        self.assertNotIn("/notifications/dispatch", tpl)


if __name__ == "__main__":
    unittest.main()
