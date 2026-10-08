"""
Lambda handler for Bilingual Notification Drafting and WhatsApp Dispatch
"""

import json
from typing import Dict, Any
from services.notify.drafting import generate_parent_broadcast_package

def notify_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for notification generation.
    """
    body = event
    if "body" in event and event["body"]:
        try:
            body = json.loads(event["body"])
        except Exception:
            pass

    plan = body.get("plan") or {}
    stage = body.get("stage") or "III"

    package = generate_parent_broadcast_package(plan, stage=stage)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "dispatched",
            "broadcast_package": package
        })
    }
