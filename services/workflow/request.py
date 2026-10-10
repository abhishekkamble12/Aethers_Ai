"""
RequestApproval Lambda: invoked by Step Functions with `lambda:invoke.waitForTaskToken`.

Stores the task token behind a short, role-bound, expiring ID and marks the decision as
awaiting that role. The approver reaches the link through GET /decisions (admin key) and
answers via POST /approve/{shortId}. The execution stays paused until then, or until the
state's TimeoutSeconds fires and the workflow escalates or fails safe.
"""

import logging
import os
from typing import Any, Dict

import boto3

from services.workflow.decision_store import decision_key, parse_decision_id
from services.workflow.token_store import issue_token

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Must equal TimeoutSeconds of the approval states in state_machine.json (checked by tests).
APPROVAL_TIMEOUT_SECONDS = int(os.environ.get("APPROVAL_TIMEOUT_SECONDS", "60"))


def _table():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def request_approval_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    task_token = event.get("taskToken")
    tenant_id = event.get("tenant_id")
    decision_id = event.get("decision_id")
    if not task_token or not tenant_id or not decision_id:
        raise ValueError("taskToken, tenant_id and decision_id are required")
    if parse_decision_id(decision_id)[0] != tenant_id:
        raise ValueError("decision_id does not belong to tenant_id")

    role = "vice_principal" if event.get("escalation") is True else "principal"
    table = _table()
    issued = issue_token(table, task_token, tenant_id, decision_id, role, APPROVAL_TIMEOUT_SECONDS)

    table.update_item(
        Key=decision_key(decision_id),
        UpdateExpression="SET #s = :s, approval_pending = :p",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": f"AWAITING_{role.upper()}",
            ":p": {"short_id": issued["short_id"], "role": role, "expires_at": issued["expires_at"]},
        },
    )
    # Never log the task token.
    logger.info("Approval requested decision=%s role=%s expires_at=%s",
                decision_id, role, issued["expires_at"])
    return {"decision_id": decision_id, "role": role, "expires_at": issued["expires_at"]}
