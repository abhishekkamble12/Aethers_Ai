"""
Audit Lambda handlers
- GET /receipts/{id}: public, privacy-filtered receipt built from the tenant's real hash chain
- GET /verify/{id}:   self-contained page that fetches the receipt and recomputes every hash in the browser
- audit_event_handler: terminal Step Functions states append to the chain
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import boto3

from services.audit.hash_chain import GENESIS_HASH, verify_audit_chain
from services.audit.store import read_chain
from services.common.http import ApiError, guarded, respond

RECEIPT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,32}$")
HASHING_SPEC = ("hash_n = SHA-256(hash_{n-1} + JSON({actor, eventType, payloadDigest, sequence, timestamp}) "
                "with keys sorted and no whitespace); hash_0 = 64 zeros; payloadDigest = SHA-256(payloadJson)")
VERIFY_PAGE = Path(__file__).with_name("verify_page.html")


def _table():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def _receipt_id(event: Dict[str, Any]) -> str:
    receipt_id = (event.get("pathParameters") or {}).get("id", "")
    if not RECEIPT_ID_RE.match(receipt_id):
        raise ApiError(400, "invalid_receipt_id", "Receipt ID is malformed.")
    return receipt_id


@guarded
def receipt_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    The whole tenant chain is returned because verification must start at genesis. Rows contain
    roles, event names, digests, timestamps and payloads (counts, versions, hashes): no personal
    data, approval links or task tokens (enforced by tests/test_audit_wiring.py).
    """
    receipt_id = _receipt_id(event)
    table = _table()
    ref = table.get_item(Key={"PK": f"RECEIPT#{receipt_id}", "SK": "META"}).get("Item")
    if not ref:
        raise ApiError(404, "receipt_not_found", "No receipt with that ID.")

    rows = read_chain(table, ref["tenant_id"])
    ok, message, broken = verify_audit_chain(rows)
    decision = table.get_item(Key={"PK": ref["tenant_id"],
                                   "SK": "DEC#" + ref["decision_id"].split("#", 2)[2]}).get("Item") or {}
    blocks = [{
        "sequence": r["seq"], "hash": r["hash"], "previousHash": r["prev_hash"], "actor": r["actor_role"],
        "eventType": r["event"], "payloadDigest": r["payload_digest"], "timestamp": r["ts"],
        "payloadJson": r.get("payload_json"),
        "decisionId": (r.get("payload") or {}).get("decision_id"),
    } for r in rows]

    return respond(200, {
        "receiptId": receipt_id,
        "schoolId": ref["tenant_id"].split("#", 1)[1],
        "decisionId": ref["decision_id"],
        "decisionStatus": decision.get("status"),
        "decisionSequences": [b["sequence"] for b in blocks if b["decisionId"] == ref["decision_id"]],
        "genesisHash": GENESIS_HASH,
        "auditHead": blocks[-1]["hash"] if blocks else GENESIS_HASH,
        "blocks": blocks,
        "hashing": HASHING_SPEC,
        "serverVerification": {"valid": ok, "message": message,
                               "brokenSequence": blocks[broken]["sequence"] if broken >= 0 else None},
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
    })


@guarded
def verify_page_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Serves the browser verifier; it fetches ../receipts/{id} from the same API and checks every hash itself."""
    _receipt_id(event)
    return {"statusCode": 200,
            "headers": {"Content-Type": "text/html; charset=utf-8",
                        "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; "
                                                   "style-src 'unsafe-inline'; connect-src 'self'"},
            "body": VERIFY_PAGE.read_text(encoding="utf-8")}

WORKFLOW_EVENTS = ("RUN_CLOSED_NO_CHANGE", "RUN_CLOSED_APPROVED_AND_NOTIFIED", "REJECTED_NO_BROADCAST",
                   "FAILSAFE_TIMEOUT_NO_BROADCAST", "WORKFLOW_ERROR_NO_BROADCAST")


def audit_event_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Terminal Step Functions states (AuditCloseNoChange / AuditCloseApproved / FailSafe*).
    Appends one hash-chained row per execution and outcome; a retried invocation returns the
    row already written instead of logging the outcome twice.
    """
    import os
    import boto3
    from services.audit.store import append_audit

    name = event.get("event")
    tenant_id = event.get("tenant_id")
    if name not in WORKFLOW_EVENTS or not tenant_id:
        raise ValueError(f"audit event must be one of {WORKFLOW_EVENTS} with a tenant_id")
    payload = {k: v for k, v in event.items() if k not in ("event", "tenant_id")}
    if isinstance(payload.get("cause"), str):
        payload["cause"] = payload["cause"][:500]  # Step Functions error causes can be long
    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    row = append_audit(table, tenant_id, "workflow", name, payload,
                       idempotency_key=f"{event['execution']}#{name}" if event.get("execution") else None)
    return {"event": name, "seq": row["seq"], "hash": row["hash"], "persisted": True}
