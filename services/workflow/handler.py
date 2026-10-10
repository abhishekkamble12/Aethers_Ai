"""
POST /approve/{shortId}: the approver's answer to a paused Step Functions execution.

Authority comes from the short ID itself: it was issued for one decision and one role
(principal, or vice_principal after escalation), expires with the approval window, and is
consumed atomically on first use. Anything in the request body that claims an identity is
ignored. Body: {"action": "APPROVE_PLAN_A" | "APPROVE_PLAN_B" | "REJECT"}
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from services.common.http import ApiError, guarded, json_body, respond
from services.workflow.decision_store import decision_key
from services.workflow.token_store import consume_token, is_valid_short_id, release_token

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ACTIONS = ("APPROVE_PLAN_A", "APPROVE_PLAN_B", "REJECT")
# Errors meaning the execution is no longer waiting on this token (timed out / escalated / finished).
CLOSED_WINDOW_ERRORS = ("TaskTimedOut", "InvalidToken", "TaskDoesNotExist")


def _table():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def _sfn():
    return boto3.client("stepfunctions")


@guarded
def approval_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    short_id = (event.get("pathParameters") or {}).get("shortId")
    if not is_valid_short_id(short_id):
        raise ApiError(400, "invalid_short_id", "Approval link is malformed.")

    action = json_body(event).get("action")
    if action not in ACTIONS:
        raise ApiError(400, "invalid_action", f"'action' must be one of {', '.join(ACTIONS)}.")

    table = _table()
    record = consume_token(table, short_id)
    if record is None:
        raise ApiError(410, "approval_link_invalid",
                       "Approval link is unknown, already used, or expired.")

    decided_at = datetime.now(timezone.utc).isoformat()
    result = {"action": action, "approver_role": record["role"], "decided_at": decided_at}
    try:
        _sfn().send_task_success(taskToken=record["task_token"], output=json.dumps(result))
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in CLOSED_WINDOW_ERRORS:
            raise ApiError(409, "approval_window_closed",
                           "This decision is no longer waiting for this approver (timed out or escalated).")
        logger.error("send_task_success failed (%s) for decision=%s", code, record["decision_id"])
        release_token(table, short_id)  # transient failure: keep the link usable
        raise ApiError(502, "workflow_unavailable", "Workflow service unavailable. Please retry.")

    table.update_item(
        Key=decision_key(record["decision_id"]),
        UpdateExpression="SET #s = :s, decided_by_role = :r, decided_at = :t REMOVE approval_pending",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": action, ":r": record["role"], ":t": decided_at},
    )
    logger.info("Decision %s: %s by %s", record["decision_id"], action, record["role"])
    return respond(200, {"status": "recorded", "decision_id": record["decision_id"], **result})
