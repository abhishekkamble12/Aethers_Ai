"""
Approval Notification Service
Dispatches approval links via SNS (Email/SMS) when Step Functions pauses for human approval.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def send_approval_notification(
    sns_client: Any,
    topic_arn: Optional[str],
    decision_id: str,
    role: str,
    short_id: str,
    public_base_url: str,
    expires_in_seconds: int = 60,
    sms_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends an approval notification to the designated approver.
    Opening the link DOES NOT approve or reject; it only loads the decision page.
    """
    approve_url = f"{public_base_url.rstrip('/')}/approve/{short_id}"
    subject = f"Saans Action Needed: {role.replace('_', ' ').title()} approval for {decision_id.split('#')[1]}"
    message = (
        f"Saans Decision Notification\n"
        f"--------------------------\n"
        f"Decision: {decision_id}\n"
        f"Awaiting: {role}\n"
        f"Window: {expires_in_seconds} seconds\n\n"
        f"Review and take action here:\n"
        f"{approve_url}\n\n"
        f"Note: Visiting this link will not submit a decision. "
        f"You must press Approve or Reject on the page."
    )

    sent = False
    details = {}

    if topic_arn:
        try:
            resp = sns_client.publish(
                TopicArn=topic_arn,
                Subject=subject[:100],  # SNS subject max length 100
                Message=message,
            )
            sent = True
            details["topic_message_id"] = resp.get("MessageId")
            logger.info("Sent approval notification for %s to topic %s", decision_id, topic_arn)
        except Exception as e:
            logger.warning("Failed to publish approval notification to topic %s: %s", topic_arn, e)

    if sms_to:
        try:
            sms_msg = f"Saans approval needed ({role}): {approve_url} (expires in {expires_in_seconds}s)"
            resp = sns_client.publish(
                PhoneNumber=sms_to,
                Message=sms_msg,
            )
            sent = True
            details["sms_message_id"] = resp.get("MessageId")
            logger.info("Sent approval SMS for %s to %s", decision_id, sms_to)
        except Exception as e:
            logger.warning("Failed to send approval SMS to %s: %s", sms_to, e)

    return {
        "sent": sent,
        "approve_url": approve_url,
        "details": details,
    }
