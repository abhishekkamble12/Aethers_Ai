"""
GET /decisions?tenant=demo&date=YYYY-MM-DD&session=MORN: the principal's Brief.

Returns the stored plan with its explanations and, while the workflow is waiting, the
approval link for the role it is waiting on. Because that link carries approval authority,
the endpoint requires the `x-saans-admin-key` header (secret from the ADMIN_API_KEY env var).
"""

import hmac
import json
import os
import re
import time
from datetime import date
from typing import Any, Dict

import boto3

from services.common.http import ApiError, guarded, header, respond

TENANT_RE = re.compile(r"^[a-z0-9_-]{1,40}$")
SESSIONS = ("EVE", "MORN")


def _table():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


from services.common.auth import require_admin as _require_admin


def _base_url(event: Dict[str, Any]) -> str:
    ctx = event.get("requestContext") or {}
    if ctx.get("domainName") and ctx.get("stage"):
        return f"https://{ctx['domainName']}/{ctx['stage']}"
    return ""


@guarded
def decisions_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    _require_admin(event)
    q = event.get("queryStringParameters") or {}

    tenant = q.get("tenant", "")
    if not TENANT_RE.match(tenant):
        raise ApiError(400, "invalid_tenant", "'tenant' must match [a-z0-9_-]{1,40}.")
    try:
        date_str = date.fromisoformat(q.get("date", "")).isoformat()
    except ValueError:
        raise ApiError(400, "invalid_date", "'date' must be YYYY-MM-DD.")
    session = q.get("session", "MORN")
    if session not in SESSIONS:
        raise ApiError(400, "invalid_session", "'session' must be EVE or MORN.")

    item = _table().get_item(Key={"PK": f"TENANT#{tenant}", "SK": f"DEC#{date_str}#{session}"}).get("Item")
    if not item:
        raise ApiError(404, "decision_not_found", "No decision for that tenant, date and session.")

    body = {
        "decision_id": f"TENANT#{tenant}#{date_str}#{session}",
        "status": item.get("status", "PENDING"),
        "decided_by_role": item.get("decided_by_role"),
        "decided_at": item.get("decided_at"),
        "plan": json.loads(item["data"]) if item.get("data") else None,
        "receipt_id": item.get("receipt_id"),
        "approval": None,
    }
    pending = item.get("approval_pending")
    if pending and int(pending["expires_at"]) > time.time():
        body["approval"] = {
            "waiting_for_role": pending["role"],
            "expires_at": int(pending["expires_at"]),
            "approve_url": f"{_base_url(event)}/approve/{pending['short_id']}",
            "actions": ["APPROVE_PLAN_A", "APPROVE_PLAN_B", "REJECT"],
        }
    return respond(200, body)
