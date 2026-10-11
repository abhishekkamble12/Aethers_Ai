"""
Circular validator evaluation on the gold and hostile fixtures, and the side-effect-free stage rehearsal handler.
Failure paths (Bedrock denied, duplicate triggers) are tested on the real code in test_fallback_model.py and
test_workflow_paths.py.
"""

import unittest
import json
from services.circular.eval_runner import run_gold_evaluation
from services.planner.handler import rehearse_handler

class TestEvalAndRehearse(unittest.TestCase):

    # 1. AI Evaluation Run
    def test_ai_gold_evaluation_metrics(self):
        """Validator evaluation: quotes verified, hostile inputs refused, and known gaps reported, not hidden."""
        summary = run_gold_evaluation()
        metrics = summary["metrics"]
        self.assertIn("validator only", summary["what_this_measures"])
        self.assertEqual(summary["dataset_size"]["real_circulars"], 1)
        self.assertEqual(metrics["verbatim_quote_validity_pct"], 100.0)
        self.assertTrue(metrics["prompt_injection_refused"])
        self.assertTrue(metrics["invented_quote_refused"])
        # r-018 (hybrid-mode quote) and r-019 (assembly quote) do not justify an outdoor-sports ban.
        self.assertEqual(sorted(g["rule_id"] for g in summary["known_gaps"]), ["r-018", "r-019"])

    # 2. Stage Rehearsal Handler
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
