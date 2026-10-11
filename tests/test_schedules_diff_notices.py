"""
Teacher schedules, ruleset diffs, and bilingual notices with WhatsApp share links.
The approval workflow itself is tested against the real state machine in test_workflow_paths.py and
test_approval_flow.py.
"""

import unittest
from services.planner.teacher_schedule import generate_teacher_schedules
from services.circular.diff_engine import compute_ruleset_diff
from services.notify.drafting import draft_notice, generate_parent_broadcast_package

class TestSchedulesDiffNotices(unittest.TestCase):

    def setUp(self):
        self.sample_plan = {
            "decision_id": "T1#2026-10-12#MORN",
            "status": "pending_approval",
            "plan_a": [],
            "plan_b": [
                {
                    "class": "7B",
                    "period": "P2",
                    "subject": "PT",
                    "fallback_venue": "Indoor Gymnasium",
                    "assigned_activity": "Table Tennis / Carrom Inter-House League",
                    "reason": "Stage III ban"
                }
            ],
            "exposure_before": 1200,
            "exposure_after": 0,
            "pe_minutes_preserved": 100.0
        }

    # 1. Teacher Schedule Tests
    def test_teacher_schedule_generation(self):
        """Generates clear indoor assignment for PE teachers."""
        raw_timetable = [
            {"class": "7B", "period": "P2", "start": "09:10", "end": "09:50", "subject": "PT", "teacher_code": "T_PE1", "venue": "Ground_A", "outdoor": True}
        ]
        rosters = generate_teacher_schedules(raw_timetable, self.sample_plan)
        self.assertIn("T_PE1", rosters)
        t_pe = rosters["T_PE1"]
        self.assertEqual(t_pe["role"], "Physical Education")
        self.assertEqual(t_pe["periods"][0]["status"], "PLAN_B_INDOOR_SESSION")
        self.assertEqual(t_pe["periods"][0]["activity"], "Table Tennis / Carrom Inter-House League")

    # 2. Ruleset Diff Engine Tests
    def test_ruleset_diff_computation(self):
        """Computes added and changed rules with quote citations."""
        active = {
            "ruleset_version": "2026-10-08-r1",
            "rules": [
                {"rule_id": "r-017", "action": {"outdoor_sports": "banned"}, "source_quote": "Quote A"}
            ]
        }
        candidate = {
            "ruleset_version": "2026-10-09-r2",
            "rules": [
                {"rule_id": "r-017", "action": {"outdoor_sports": "banned"}, "source_quote": "Quote A"},
                {"rule_id": "r-019", "action": {"hybrid_mode": "mandatory"}, "source_quote": "Classes up to 5th online"}
            ]
        }
        diff = compute_ruleset_diff(active, candidate)
        self.assertTrue(diff["has_changes"])
        self.assertEqual(diff["total_added"], 1)
        self.assertEqual(diff["added_rules"][0]["rule_id"], "r-019")
        self.assertEqual(diff["added_rules"][0]["source_quote"], "Classes up to 5th online")

    # 3. Notice Drafting & WhatsApp Link Tests
    def test_bilingual_notice_and_whatsapp_links(self):
        """Generates English and Hindi notices with valid WhatsApp share URLs."""
        package = generate_parent_broadcast_package(self.sample_plan, stage="III")
        
        # English check
        self.assertIn("GRAP Stage III", package["english"]["notice_text"])
        self.assertTrue(package["whatsapp_url_english"].startswith("https://api.whatsapp.com/send?text="))
        
        # Hindi check
        self.assertIn("ग्रैप स्टेज III", package["hindi"]["notice_text"])
        self.assertTrue(package["whatsapp_url_hindi"].startswith("https://api.whatsapp.com/send?text="))

    def test_static_fallback_notice_flag(self):
        """Static template fallback is marked cleanly in metadata without crashing."""
        notice = draft_notice(self.sample_plan, force_fallback=True)
        self.assertTrue(notice["fallback_used"])
        self.assertEqual(notice["model_used"], "STATIC_TEMPLATE_FALLBACK")

if __name__ == "__main__":
    unittest.main()
