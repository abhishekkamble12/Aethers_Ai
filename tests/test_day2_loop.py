"""
Day 2 Test Suite: The Real Loop
Verifies:
1. Step Functions Workflow: Approval, Escalation, and Fail-Safe paths
2. Token Registry: Secure short-ID expiring tokens
3. Teacher Schedule Generator: Personalized rosters and activity preservation
4. Ruleset Diff Engine: Version comparison with quote citations
5. Notice Drafting: Bilingual templates and WhatsApp click-to-share links
"""

import unittest
from services.workflow.workflow_manager import WorkflowManager
from services.planner.teacher_schedule import generate_teacher_schedules
from services.circular.diff_engine import compute_ruleset_diff, compute_ruleset_hash
from services.notify.drafting import draft_notice, generate_parent_broadcast_package

class TestDay2Loop(unittest.TestCase):

    def setUp(self):
        self.wm = WorkflowManager()
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

    # 1. Workflow Tests
    def test_workflow_direct_approval(self):
        """Principal approves -> notices dispatched -> closed approved."""
        res = self.wm.execute_workflow_step(self.sample_plan, principal_action="APPROVE_PLAN_B")
        self.assertEqual(res["status"], "approved")
        self.assertEqual(res["final_state"], "AuditCloseApproved")
        self.assertTrue(res["notified"])

    def test_workflow_timeout_escalates_to_vice_principal(self):
        """Principal times out -> escalates to Vice-Principal -> VP approves."""
        res = self.wm.execute_workflow_step(
            self.sample_plan,
            timeout_occurred=True,
            principal_action="APPROVE_PLAN_B"
        )
        self.assertEqual(res["status"], "approved_by_escalation")
        self.assertIn("EscalateToVicePrincipal", res["transitions"])
        self.assertTrue(res["notified"])

    def test_workflow_final_timeout_fails_safe_no_broadcast(self):
        """Both Principal and VP time out -> system fails safe with zero broadcasts."""
        res = self.wm.execute_workflow_step(
            self.sample_plan,
            timeout_occurred=True,
            escalation_timeout=True
        )
        self.assertEqual(res["status"], "failed_safe_timeout")
        self.assertEqual(res["final_state"], "FailSafeNoBroadcast")
        self.assertFalse(res["notified"])

    def test_secure_short_token_registry(self):
        """Verifies short random token generation, resolution, and one-time consumption."""
        raw_sfn_token = "arn:aws:states:us-east-1:123456789:taskToken:xyz987"
        short_id = self.wm.register_task_token(raw_sfn_token, "demo_tenant", "dec_1")
        
        self.assertLessEqual(len(short_id), 12)
        # First consumption succeeds
        record = self.wm.consume_token(short_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["task_token"], raw_sfn_token)
        
        # Second consumption fails (already consumed)
        reused = self.wm.consume_token(short_id)
        self.assertIsNone(reused)

    # 2. Teacher Schedule Tests
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

    # 3. Ruleset Diff Engine Tests
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

    # 4. Notice Drafting & WhatsApp Link Tests
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
