"""
Standing Order Pre-Authorization Module (P2 Feature)
Allows a school principal or administrator to define Standing Orders:
e.g. "If CAQM declares Stage III or higher, automatically execute Plan B and notify teachers without morning approval bottleneck."
"""

from typing import Dict, Any, Optional

class StandingOrderManager:

    def __init__(self):
        self.standing_orders: Dict[str, Dict[str, Any]] = {}

    def register_standing_order(
        self,
        tenant_id: str,
        threshold_stage: str = "III",
        auto_action: str = "APPROVE_PLAN_B",
        authorized_by: str = "principal_delhi_demo"
    ) -> Dict[str, Any]:
        """
        Stores an active standing order rule for a tenant.
        """
        order = {
            "tenant_id": tenant_id,
            "threshold_stage": threshold_stage,
            "auto_action": auto_action,
            "authorized_by": authorized_by,
            "status": "ACTIVE",
            "policy": f"Auto-execute {auto_action} whenever declared stage >= {threshold_stage}"
        }
        self.standing_orders[tenant_id] = order
        return order

    def evaluate_standing_order(
        self,
        tenant_id: str,
        declared_stage: str
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates whether an active standing order applies to the incoming stage.
        Stages order: I < II < III < IV.
        """
        order = self.standing_orders.get(tenant_id)
        if not order or order.get("status") != "ACTIVE":
            return None

        stage_levels = {"I": 1, "II": 2, "III": 3, "IV": 4}
        target_level = stage_levels.get(declared_stage, 1)
        threshold_level = stage_levels.get(order.get("threshold_stage", "III"), 3)

        if target_level >= threshold_level:
            return {
                "triggered": True,
                "action": order["auto_action"],
                "policy": order["policy"],
                "authorized_by": order["authorized_by"],
                "reason": f"Stage {declared_stage} meets or exceeds standing threshold {order['threshold_stage']}"
            }

        return None
