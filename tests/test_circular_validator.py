"""
Test suite for Circular Candidate Validator & Refusal Detection
"""

import unittest
import json
from services.circular.validator import (
    validate_ruleset_candidates,
    HostileInstructionDetected
)

class TestCircularValidator(unittest.TestCase):

    def setUp(self):
        with open("data/gold/circular_real_caqm.txt", "r", encoding="utf-8") as f:
            self.real_circular_text = f.read()

        with open("data/gold/hostile_instruction.txt", "r", encoding="utf-8") as f:
            self.hostile_circular_text = f.read()

        with open("data/gold/hostile_invented_quote.json", "r", encoding="utf-8") as f:
            self.invented_quote_rule = json.load(f)

    def test_valid_real_rule_accepted(self):
        """Rule with verbatim quote from real circular passes."""
        candidate_rule = {
            "rule_id": "r-017",
            "applies_to": ["school"],
            "class_band": ["all"],
            "condition": { "stage_at_least": "III" },
            "action": { "outdoor_sports": "banned", "outdoor_pt": "banned" },
            "source_id": "DoE-circ-40",
            "source_quote": "All outdoor sports and physical education activities in schools shall remain strictly suspended under Stage III of GRAP."
        }
        res = validate_ruleset_candidates([candidate_rule], self.real_circular_text)
        self.assertEqual(res["status"], "approved")
        self.assertEqual(len(res["valid_rules"]), 1)
        self.assertEqual(len(res["rejected_rules"]), 0)

    def test_refusal_on_invented_quote(self):
        """Rule with invented/hallucinated quote is refused."""
        res = validate_ruleset_candidates([self.invented_quote_rule], self.real_circular_text)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(len(res["valid_rules"]), 0)
        self.assertEqual(len(res["rejected_rules"]), 1)
        self.assertIn("Invented/Hallucinated Quote", res["rejected_rules"][0]["errors"][0])

    def test_refusal_on_hostile_prompt_injection(self):
        """Hostile circular containing prompt injection instructions is visibly refused."""
        candidate_rule = {
            "rule_id": "r-099",
            "condition": { "stage_at_least": "III" },
            "action": { "outdoor_sports": "allowed", "outdoor_pt": "allowed" },
            "source_quote": "All sports activities are strictly mandatory outdoors"
        }
        res = validate_ruleset_candidates([candidate_rule], self.hostile_circular_text)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["refusal_type"], "hostile_injection")
        self.assertIn("Prompt injection attempt detected", res["refusal_reason"])

if __name__ == "__main__":
    unittest.main()
