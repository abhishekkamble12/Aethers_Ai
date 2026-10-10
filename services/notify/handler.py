"""
Lambda handler for Bilingual Notification Drafting and WhatsApp Dispatch

- Step Functions (DraftAndDispatchNotices): drafts the approved plan's notices and appends a
  NOTICES_DRAFTED audit row recording, per notice, whether Bedrock or the static template wrote
  it and a digest of the exact text, so a fallback is always visible in the chain.
- Direct HTTP invocation: drafts only, no audit. (No public API route: only the workflow drafts notices.)
Notices are drafted and returned as WhatsApp click-to-share links; nothing is pushed to phones.
"""

import json
import logging
import os
from typing import Dict, Any

import boto3

from services.audit.hash_chain import compute_payload_digest
from services.audit.store import append_audit
from services.common.http import ApiError, guarded, is_http_event, json_body, respond
from services.notify.drafting import generate_parent_broadcast_package
from services.planner.handler import normalise_stage

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _summary(package: Dict[str, Any]):
    return [{"audience": n["audience"], "language": n["language"], "model_used": n["model_used"],
             "fallback_used": n["fallback_used"], "text_sha256": compute_payload_digest(n["notice_text"])}
            for n in (package["english"], package["hindi"], package["teacher"])]


def notify_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    if is_http_event(event):
        return _notify_http(event, context)

    tenant_id, decision_id = event.get("tenant_id"), event.get("decision_id")
    if not tenant_id or not decision_id:
        raise ValueError("tenant_id and decision_id are required")
    stage = normalise_stage(event.get("stage", "III"))
    package = generate_parent_broadcast_package(event.get("plan") or {}, stage=stage,
                                                receipt_id=event.get("receipt_id"))
    notices = _summary(package)

    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    row = append_audit(table, tenant_id, "workflow:notify", "NOTICES_DRAFTED",
                       {"decision_id": decision_id, "approval": event.get("approval"), "notices": notices},
                       idempotency_key=f"{event['execution']}#NOTICES_DRAFTED" if event.get("execution") else None)
    logger.info("Notices drafted for %s (fallback used: %s)", decision_id,
                [n["fallback_used"] for n in notices])
    return {"status": "drafted", "notices": notices, "broadcast_package": package, "audit_seq": row["seq"]}


@guarded
def _notify_http(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    body = json_body(event)
    try:
        stage = normalise_stage(body.get("stage", "III"))
    except ValueError as e:
        raise ApiError(400, "invalid_stage", str(e))
    plan = body.get("plan") or {}
    if not isinstance(plan, dict):
        raise ApiError(400, "invalid_plan", "'plan' must be an object.")
    package = generate_parent_broadcast_package(plan, stage=stage)
    return respond(200, {"status": "drafted", "broadcast_package": package, "notices": _summary(package)})
