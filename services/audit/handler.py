"""
Lambda handler for Public Receipt Verification
Returns actual audit chain rows for client-side cryptographic verification.
"""

import json
from typing import Dict, Any, List
from services.audit.hash_chain import verify_audit_chain

# Demo chain data matching app.js (for demo purposes)
# In production, this would query DynamoDB for PK=TENANT#{tenant_id}, SK begins_with AUD#
DEMO_CHAIN = [
  {
    "seq": 1,
    "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "actor_role": "scheduler:eventbridge",
    "event": "STAGE_III_FORECAST_INGESTED",
    "payload_digest": "dea600875056e79ef3367e0283d95a1158f31be16e0b75b4ced781cb577f8369",
    "ts": "2026-10-12T05:30:00Z",
    "hash": "570219d0482ccdbf2d3b414dbb4926d00de2d9310f0e76abba6e17933018b842"
  },
  {
    "seq": 2,
    "prev_hash": "570219d0482ccdbf2d3b414dbb4926d00de2d9310f0e76abba6e17933018b842",
    "actor_role": "rules_engine",
    "event": "RULES_EVALUATED_RULESET_R1",
    "payload_digest": "94c7603a84d2399342420e2cf2e9a2b0e6d6e85b14542f6060fb44283284ba20",
    "ts": "2026-10-12T05:30:02Z",
    "hash": "22520f13d5bd5b368608d6e859209f833f654fb5731f2667614b37ada745f7aa"
  },
  {
    "seq": 3,
    "prev_hash": "22520f13d5bd5b368608d6e859209f833f654fb5731f2667614b37ada745f7aa",
    "actor_role": "planner:deterministic",
    "event": "PLAN_A_B_GENERATED",
    "payload_digest": "b3e9b3d0c9d058d74c09dca080314699bc5afe2ccc83166b2ed5aedbce60e60d",
    "ts": "2026-10-12T05:30:05Z",
    "hash": "a094dc8e6cc32627c44d8cdca7041e2ab30031cacd868a29012d5c66de8b807b"
  }
]

def receipt_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Returns public receipt with audit chain rows for client-side cryptographic verification.
    """
    path_parameters = event.get("pathParameters") or {}
    receipt_id = path_parameters.get("id", "latest")

    # Verify chain integrity
    is_valid, message, _ = verify_audit_chain(DEMO_CHAIN)
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "receipt_id": receipt_id,
            "status": "valid" if is_valid else "invalid",
            "algorithm": "SHA-256",
            "message": message,
            "chain": DEMO_CHAIN,
            "head_hash": DEMO_CHAIN[-1]["hash"] if DEMO_CHAIN else None
        })
    }



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
