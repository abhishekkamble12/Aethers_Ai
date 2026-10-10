"""
DynamoDB-backed approval token store.

Step Functions task tokens never leave the server: approvers receive an 8-character
short ID. The record binds that ID to one decision and one role (principal or
vice_principal), expires with the workflow's approval window, and can be consumed
exactly once (conditional update), so a replayed or late link cannot approve.

Item:  PK=TOKEN#{short_id}  SK=META
       task_token, tenant_id, decision_id, role, expires_at (epoch s), consumed, ttl
"""

import re
import secrets
import time
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

SHORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,32}$")
ROLES = ("principal", "vice_principal")


def _key(short_id: str) -> Dict[str, str]:
    return {"PK": f"TOKEN#{short_id}", "SK": "META"}


def is_valid_short_id(short_id: Any) -> bool:
    return isinstance(short_id, str) and bool(SHORT_ID_RE.match(short_id))


def issue_token(table, task_token: str, tenant_id: str, decision_id: str, role: str,
                window_seconds: int, now: Optional[float] = None) -> Dict[str, Any]:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    now = int(now if now is not None else time.time())
    for _ in range(3):  # retry on the (astronomically unlikely) short-ID collision
        short_id = secrets.token_urlsafe(6)
        record = {
            **_key(short_id),
            "task_token": task_token,
            "tenant_id": tenant_id,
            "decision_id": decision_id,
            "role": role,
            "issued_at": now,
            "expires_at": now + int(window_seconds),
            "consumed": False,
            "ttl": now + int(window_seconds) + 86400,  # DynamoDB TTL cleanup a day later
        }
        try:
            table.put_item(Item=record, ConditionExpression="attribute_not_exists(PK)")
            return {"short_id": short_id, "role": role, "expires_at": record["expires_at"]}
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
    raise RuntimeError("Could not allocate a unique approval short ID")


def consume_token(table, short_id: str, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Atomically mark the token consumed. Returns the record, or None if unknown, used or expired."""
    now = int(now if now is not None else time.time())
    try:
        resp = table.update_item(
            Key=_key(short_id),
            UpdateExpression="SET #c = :t, consumed_at = :now",
            ConditionExpression="attribute_exists(PK) AND #c = :f AND expires_at > :now",
            ExpressionAttributeNames={"#c": "consumed"},  # 'consumed' is a DynamoDB reserved word
            ExpressionAttributeValues={":t": True, ":f": False, ":now": now},
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return None
        raise
    return resp["Attributes"]


def release_token(table, short_id: str) -> None:
    """Undo a consume when the workflow could not be reached (transient error), so the link still works."""
    table.update_item(
        Key=_key(short_id),
        UpdateExpression="SET #c = :f REMOVE consumed_at",
        ExpressionAttributeNames={"#c": "consumed"},
        ExpressionAttributeValues={":f": False},
    )
