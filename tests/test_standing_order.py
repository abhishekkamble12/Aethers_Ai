"""
Unit Test Suite for Standing Order Pre-Authorization (P2 Feature)
"""

import unittest
from services.planner.standing_order import StandingOrderManager

class TestStandingOrder(unittest.TestCase):

    def setUp(self):
        self.mgr = StandingOrderManager()
        self.mgr.register_standing_order(
            tenant_id="TENANT#dps",
            threshold_stage="III",
            auto_action="APPROVE_PLAN_B",
            authorized_by="principal_delhi_demo"
        )

    def test_standing_order_triggers_on_or_above_threshold(self):
        """Under Stage III or IV, standing order activates and pre-approves Plan B."""
        # Stage III triggers
        res_iii = self.mgr.evaluate_standing_order("TENANT#dps", declared_stage="III")
        self.assertIsNotNone(res_iii)
        self.assertTrue(res_iii["triggered"])
        self.assertEqual(res_iii["action"], "APPROVE_PLAN_B")

        # Stage IV triggers
        res_iv = self.mgr.evaluate_standing_order("TENANT#dps", declared_stage="IV")
        self.assertIsNotNone(res_iv)
        self.assertTrue(res_iv["triggered"])

    def test_standing_order_does_not_trigger_below_threshold(self):
        """Under Stage I or II, standing order does not auto-execute."""
        res_i = self.mgr.evaluate_standing_order("TENANT#dps", declared_stage="I")
        self.assertIsNone(res_i)

        res_ii = self.mgr.evaluate_standing_order("TENANT#dps", declared_stage="II")
        self.assertIsNone(res_ii)

    def test_unregistered_tenant_returns_none(self):
        """A tenant without an active standing order requires standard manual approval."""
        res = self.mgr.evaluate_standing_order("TENANT#other_school", declared_stage="III")
        self.assertIsNone(res)

if __name__ == "__main__":
    unittest.main()
