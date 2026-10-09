"""
Approval Callback & Webhook Lambda Handler
Handles:
1. Webhook callbacks from Telegram bot (verifying secret token header & allowlisted chat ID)
2. HTTP POST /approve/{shortId} from the Principal Brief interface
"""

import json
import os
from typing import Dict, Any

try:
    import boto3
except ImportError:
    boto3 = None

from services.workflow.workflow_manager import workflow_registry

ALLOWLISTED_APPROVERS = {
    "principal_delhi_demo": "Principal - DPS",
    "vp_delhi_demo": "Vice Principal - DPS",
    "chat_id_987654321": "Principal Telegram"
}

TELEGRAM_SECRET_HEADER = os.environ.get("TELEGRAM_SECRET_TOKEN", "")


def approval_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handles approval requests via API Gateway or Telegram Webhook.
    """
    path_parameters = event.get("pathParameters") or {}
    headers = event.get("headers") or {}
    short_id = path_parameters.get("shortId")

    # 1. Telegram Webhook Secret Check (if applicable)
    telegram_token = headers.get("x-telegram-bot-api-secret-token") or headers.get("X-Telegram-Bot-Api-Secret-Token")
    if "update_id" in event: # Telegram payload
        expected_token = os.environ.get("TELEGRAM_SECRET_TOKEN", TELEGRAM_SECRET_HEADER)
        if not expected_token or telegram_token != expected_token:
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Unauthorized webhook token"})
            }

    # 2. Parse Action and Approver
    body_data = {}
    if "body" in event and event["body"]:
        try:
            body_data = json.loads(event["body"])
        except Exception:
            body_data = {}

    action = body_data.get("action", "APPROVE_PLAN_A")
    approver_id = body_data.get("approver_id", "principal_delhi_demo")

    # Verify allowlisted approver
    if approver_id not in ALLOWLISTED_APPROVERS:
        return {
            "statusCode": 403,
            "body": json.dumps({"error": f"Approver '{approver_id}' is not in authorized allowlist."})
        }

    # 3. Resolve Short ID to Step Functions Token
    if short_id:
        token_record = workflow_registry.consume_token(short_id)
        if not token_record:
            return {
                "statusCode": 410,
                "body": json.dumps({"error": "Approval token expired, invalid, or already consumed."})
            }
        
        raw_task_token = token_record["task_token"]
        
        # If in AWS, resume Step Functions
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") and raw_task_token != "MOCK_TOKEN":
            try:
                sfn = boto3.client("stepfunctions")
                sfn.send_task_success(
                    taskToken=raw_task_token,
                    output=json.dumps({
                        "action": action,
                        "approver": approver_id,
                        "timestamp": body_data.get("timestamp")
                    })
                )
            except Exception as e:
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error": f"Failed to resume Step Functions: {str(e)}"})
                }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "success",
            "message": f"Action '{action}' recorded by {ALLOWLISTED_APPROVERS.get(approver_id)}.",
            "action": action
        })
    }
