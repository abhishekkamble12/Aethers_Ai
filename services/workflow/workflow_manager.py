"""
Saans Workflow Manager & Token Registry
Manages Step Functions task token mapping to secure, short expiring IDs:
- Raw task tokens NEVER leave the server.
- Supports principal approval, vice-principal escalation, and fail-safe timeout.
"""

import os
import secrets
import time
from typing import Dict, Any, Optional

TOKEN_TTL_SECONDS = 300 # 5 minutes

class WorkflowManager:
    def __init__(self):
        # In-memory token store for local demo / execution (backed by DynamoDB in AWS)
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._execution_history: Dict[str, list] = {}

    def register_task_token(
        self,
        task_token: str,
        tenant_id: str,
        decision_id: str,
        escalation: bool = False
    ) -> str:
        """
        Stores the AWS TaskToken securely and returns a short 8-character random ID.
        """
        short_id = secrets.token_urlsafe(6) # ~8 chars
        self._tokens[short_id] = {
            "task_token": task_token,
            "tenant_id": tenant_id,
            "decision_id": decision_id,
            "escalation": escalation,
            "created_at": time.time(),
            "expires_at": time.time() + TOKEN_TTL_SECONDS,
            "consumed": False
        }
        return short_id

    def resolve_token(self, short_id: str) -> Optional[Dict[str, Any]]:
        """
        Validates and retrieves the record for a short ID.
        """
        record = self._tokens.get(short_id)
        if not record:
            return None
        if time.time() > record["expires_at"]:
            return None
        if record["consumed"]:
            return None
        return record

    def consume_token(self, short_id: str) -> Optional[Dict[str, Any]]:
        record = self.resolve_token(short_id)
        if record:
            record["consumed"] = True
            return record
        return None

    def execute_workflow_step(
        self,
        decision_data: Dict[str, Any],
        principal_action: Optional[str] = None,
        timeout_occurred: bool = False,
        escalation_timeout: bool = False
    ) -> Dict[str, Any]:
        """
        Deterministic local state machine runner:
        Replicates the exact Step Functions state transitions:
        LoadContext -> CheckIfInterventionNeeded -> RequestPrincipalApproval -> (Escalate) -> (FailSafe or Approved)
        """
        decision_id = decision_data.get("decision_id", "TENANT#demo#2026-10-12#MORN")
        transitions = ["LoadContext"]

        if decision_data.get("status") == "confirmed_no_change":
            transitions.append("CheckIfInterventionNeeded")
            transitions.append("AuditCloseNoChange")
            return {
                "decision_id": decision_id,
                "status": "closed_no_change",
                "final_state": "AuditCloseNoChange",
                "transitions": transitions,
                "notified": False
            }

        transitions.append("CheckIfInterventionNeeded")
        transitions.append("RequestPrincipalApproval")

        # Did principal time out?
        if timeout_occurred:
            transitions.append("EscalateToVicePrincipal")
            if escalation_timeout:
                transitions.append("FailSafeNoBroadcast")
                return {
                    "decision_id": decision_id,
                    "status": "failed_safe_timeout",
                    "final_state": "FailSafeNoBroadcast",
                    "transitions": transitions,
                    "notified": False,
                    "reason": "Principal and Vice-Principal approval timed out. Safe state maintained."
                }
            # Vice-principal approved
            action = principal_action or "APPROVE_PLAN_A"
            transitions.append("ProcessDecisionAction")
            transitions.append("DraftAndDispatchNotices")
            transitions.append("AuditCloseApproved")
            return {
                "decision_id": decision_id,
                "status": "approved_by_escalation",
                "action": action,
                "final_state": "AuditCloseApproved",
                "transitions": transitions,
                "notified": True
            }

        # Normal Principal response
        if principal_action in ("APPROVE_PLAN_A", "APPROVE_PLAN_B"):
            transitions.append("ProcessDecisionAction")
            transitions.append("DraftAndDispatchNotices")
            transitions.append("AuditCloseApproved")
            return {
                "decision_id": decision_id,
                "status": "approved",
                "action": principal_action,
                "final_state": "AuditCloseApproved",
                "transitions": transitions,
                "notified": True
            }
        else:
            # Explicit Reject
            transitions.append("ProcessDecisionAction")
            transitions.append("FailSafeNoBroadcast")
            return {
                "decision_id": decision_id,
                "status": "rejected_by_approver",
                "final_state": "FailSafeNoBroadcast",
                "transitions": transitions,
                "notified": False
            }

# Global singleton instance for local runtime
workflow_registry = WorkflowManager()
