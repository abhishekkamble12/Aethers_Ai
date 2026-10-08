"""
Test Suite for Day 3 Proofs, Failure Drills & Evaluation
Verifies:
1. Drill 1: Bedrock IAM Access Denied -> Static Template Fallback
2. Drill 2: Idempotent Execution on Duplicate Scheduled Triggers
3. Drill 3: Telegram 5xx Error -> SQS Retries -> DLQ -> CloudWatch Alarm Trigger
4. AI Evaluation Engine: Benchmark Metrics on Gold & Hostile Circulars
5. Stage Rehearsal Lambda Handler: Side-effect free what-if simulator
"""

import unittest
import json
from services.drills.drills_simulator import FailureDrillsSimulator
from services.circular.eval_runner import run_gold_evaluation
from services.planner.handler import rehearse_handler

class TestDay3DrillsAndProof(unittest.TestCase):

    def setUp(self):
        self.simulator = FailureDrillsSimulator()
        self.sample_plan = {
            "decision_id": "T1#2026-10-12#MORN",
            "status": "pending_approval",
            "plan_a": [],
            "plan_b": [
                {
                    "class": "7B",
                    "period": "P2",
                    "subject": "PT",
                    "fallback_venue": "Indoor Hall",
                    "assigned_activity": "Indoor Wellness / Chess",
                    "reason": "Stage III ban"
                }
            ],
            "exposure_before": 1200,
            "exposure_after": 0,
            "pe_minutes_preserved": 100.0
        }

    # 1. Failure Drill 1
    def test_drill_1_bedrock_denied_fallback(self):
        """Simulates Bedrock IAM rejection and proves clean fallback to static templates."""
        res = self.simulator.run_drill_1_bedrock_denied(self.sample_plan)
        self.assertTrue(res["passed"])
        self.assertEqual(res["fallback_mechanism"], "STATIC_TEMPLATE_FALLBACK")
        self.assertEqual(res["model_used"], "STATIC_TEMPLATE_FALLBACK")
        self.assertIn("GRAP Stage III", res["notice_text"])
        self.assertTrue(res["whatsapp_url"].startswith("https://api.whatsapp.com/send?text="))

    # 2. Failure Drill 2
    def test_drill_2_idempotency_duplicate_trigger(self):
        """Simulates double-firing of scheduled trigger and proves single execution with 0 duplicates."""
        res = self.simulator.run_drill_2_idempotency_trigger(
            decision_id="TENANT#dps#2026-10-12#MORN",
            plan_data=self.sample_plan
        )
        self.assertTrue(res["passed"])
        self.assertEqual(res["total_attempts"], 2)
        self.assertEqual(res["actual_executions"], 1)
        self.assertEqual(res["notices_sent"], 1)
        self.assertEqual(res["trace"][1]["status"], "DUPLICATE_SUPPRESSED")

    # 3. Failure Drill 3
    def test_drill_3_telegram_5xx_dlq_alarm(self):
        """Simulates Telegram API 5xx failure, SQS retries exhaustion, DLQ placement, and CloudWatch alarm."""
        res = self.simulator.run_drill_3_telegram_5xx_dlq(
            payload={"recipient": "@principal_delhi", "text": "Approve Plan B"},
            max_receive_count=3
        )
        self.assertTrue(res["passed"])
        self.assertEqual(len(res["retry_attempts"]), 3)
        self.assertEqual(res["dlq_item"]["final_status"], "SENT_TO_DLQ")
        self.assertEqual(res["alarm"]["state"], "ALARM")
        self.assertIn("UNDELIVERED", res["dashboard_display"])

    # 4. AI Evaluation Run
    def test_ai_gold_evaluation_metrics(self):
        """Runs evaluation over gold set and hostile cases to verify 100% precision, quote validity, and refusal."""
        summary = run_gold_evaluation()
        metrics = summary["metrics"]
        self.assertEqual(metrics["rule_precision_pct"], 100.0)
        self.assertEqual(metrics["verbatim_quote_validity_pct"], 100.0)
        self.assertEqual(metrics["prompt_injection_refusal_rate_pct"], 100.0)
        self.assertEqual(metrics["hallucinated_quote_refusal_rate_pct"], 100.0)

    # 5. Stage Rehearsal Handler
    def test_stage_rehearsal_handler_zero_side_effects(self):
        """Rehearsal handler instantly re-plans for Stage IV without side effects or mutations."""
        event = {"queryStringParameters": {"stage": "IV"}}
        resp = rehearse_handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(body["declared_stage"], "IV")
        self.assertEqual(body["decision_id"], "REHEARSAL#STAGE_IV")
        self.assertEqual(body["pe_minutes_preserved"], 100.0)

if __name__ == "__main__":
    unittest.main()
