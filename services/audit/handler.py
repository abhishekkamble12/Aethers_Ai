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


def audit_event_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Step Functions audit states (AuditCloseNoChange / AuditCloseApproved / FailSafeNoBroadcast).
    INTERIM (hack_win M2a): logs the workflow event only and reports persisted=False.
    hack_win M3 replaces this with a conditional, hash-chained DynamoDB append.
    """
    import logging
    logging.getLogger().info("Workflow audit event %s tenant=%s", event.get("event"), event.get("tenant_id"))
    return {"event": event.get("event"), "tenant_id": event.get("tenant_id"), "persisted": False}
