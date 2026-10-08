"""
Lambda handler for Public Receipt Verification
"""

import json
from typing import Dict, Any
from services.audit.hash_chain import verify_audit_chain

def receipt_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Returns public receipt with non-sensitive fields for client-side cryptographic verification.
    """
    path_parameters = event.get("pathParameters") or {}
    receipt_id = path_parameters.get("id", "latest")

    # In production, query DynamoDB for items matching PK=TENANT#{tenant_id}, SK begins_with AUD#
    # Here, return formatted receipt structure
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "receipt_id": receipt_id,
            "status": "tamper_evident",
            "algorithm": "SHA-256",
            "message": "Verify chain in browser using WebCrypto API."
        })
    }
