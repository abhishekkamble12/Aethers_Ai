"""
Persisted, hash-chained audit log in the single DynamoDB table.

    PK={tenant_id}  SK=AUD#{seq:06d}   seq, prev_hash, hash, actor_role, event, payload_digest, ts, payload
    PK={tenant_id}  SK=AUDHEAD         seq, hash                     (head pointer)
    PK={tenant_id}  SK=AUDKEY#{key}    seq                           (idempotency marker, optional)

hash_n = SHA256(hash_{n-1} || canonical_json({seq, actor_role, event, payload_digest, ts}))
payload_digest = SHA256(canonical_json(payload)); the payload itself is stored so anyone can
re-check the digest. Payloads carry roles, counts and IDs, never personal data or approval links.

Each append is ONE TransactWriteItems:
  - Put AUD#{n}       if attribute_not_exists(SK)      (no overwrite of history)
  - Update AUDHEAD    if seq = n-1  (or Put if absent)  (strict order under concurrency)
  - Put AUDKEY#{key}  if attribute_not_exists(SK)      (Step Functions retries cannot double-log)
A concurrent writer makes the transaction fail as a whole; we re-read the head and retry.
"""

import json
import logging
import random
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from services.audit.hash_chain import GENESIS_HASH, canonical_json, create_audit_row

logger = logging.getLogger(__name__)

ROW_FIELDS = ("seq", "prev_hash", "hash", "actor_role", "event", "payload_digest", "ts")


class AuditAppendConflict(Exception):
    pass


def _normalise(item: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: item[k] for k in ROW_FIELDS if k in item}
    out["seq"] = int(out["seq"])
    if "payload" in item:
        out["payload"] = json.loads(item["payload"])
    return out


def read_head(table, tenant_id: str):
    item = table.get_item(Key={"PK": tenant_id, "SK": "AUDHEAD"}, ConsistentRead=True).get("Item")
    if not item:
        return 0, GENESIS_HASH
    return int(item["seq"]), item["hash"]


def append_audit(table, tenant_id: str, actor_role: str, event: str, payload: Dict[str, Any],
                 idempotency_key: Optional[str] = None, max_attempts: int = 6) -> Dict[str, Any]:
    """Appends one row and returns it (or the already-recorded row for a repeated idempotency_key)."""
    # The resource's client serialises plain Python values itself; pass items untyped.
    client = table.meta.client
    payload = json.loads(json.dumps(payload, default=_json_default))  # plain JSON types only
    for attempt in range(1, max_attempts + 1):
        seq, head_hash = read_head(table, tenant_id)
        row = create_audit_row(seq + 1, head_hash, actor_role, event, payload)
        item = {"PK": tenant_id, "SK": f"AUD#{row['seq']:06d}", **row, "payload": canonical_json(payload)}

        ops = [{"Put": {"TableName": table.name, "Item": item,
                        "ConditionExpression": "attribute_not_exists(SK)"}}]
        if seq == 0:
            ops.append({"Put": {"TableName": table.name,
                                "Item": {"PK": tenant_id, "SK": "AUDHEAD", "seq": 1, "hash": row["hash"]},
                                "ConditionExpression": "attribute_not_exists(SK)"}})
        else:
            ops.append({"Update": {"TableName": table.name, "Key": {"PK": tenant_id, "SK": "AUDHEAD"},
                                   "UpdateExpression": "SET #seq = :new, #h = :hash",
                                   "ConditionExpression": "#seq = :prev",
                                   "ExpressionAttributeNames": {"#seq": "seq", "#h": "hash"},
                                   "ExpressionAttributeValues": {":new": row["seq"], ":hash": row["hash"],
                                                                     ":prev": seq}}})
        if idempotency_key:
            ops.append({"Put": {"TableName": table.name,
                                "Item": {"PK": tenant_id, "SK": f"AUDKEY#{idempotency_key}",
                                             "seq": row["seq"]},
                                "ConditionExpression": "attribute_not_exists(SK)"}})
        try:
            client.transact_write_items(TransactItems=ops)
            return {**row, "payload": payload}
        except ClientError as e:
            if e.response["Error"]["Code"] != "TransactionCanceledException":
                raise
            reasons = [r.get("Code") for r in e.response.get("CancellationReasons", [])]
            if idempotency_key and len(reasons) == len(ops) and reasons[-1] == "ConditionalCheckFailed":
                existing = _existing_for_key(table, tenant_id, idempotency_key)
                if existing:
                    logger.info("Audit %s already recorded at seq %s (key %s)", event, existing["seq"], idempotency_key)
                    return existing
            logger.info("Audit append conflict for %s (attempt %d, reasons %s); retrying", tenant_id, attempt, reasons)
            time.sleep(min(0.05 * (2 ** attempt), 1.0) * random.random())
    raise AuditAppendConflict(f"Could not append audit row for {tenant_id} after {max_attempts} attempts")


def _existing_for_key(table, tenant_id: str, key: str) -> Optional[Dict[str, Any]]:
    marker = table.get_item(Key={"PK": tenant_id, "SK": f"AUDKEY#{key}"}, ConsistentRead=True).get("Item")
    if not marker:
        return None
    item = table.get_item(Key={"PK": tenant_id, "SK": f"AUD#{int(marker['seq']):06d}"},
                          ConsistentRead=True).get("Item")
    return _normalise(item) if item else None


def read_chain(table, tenant_id: str) -> List[Dict[str, Any]]:
    """All rows in seq order, numbers as int, payload decoded."""
    rows, kwargs = [], {
        "KeyConditionExpression": "PK = :pk AND begins_with(SK, :p)",
        "ExpressionAttributeValues": {":pk": tenant_id, ":p": "AUD#"},
        "ConsistentRead": True,
    }
    while True:
        resp = table.query(**kwargs)
        rows.extend(_normalise(i) for i in resp["Items"])
        if "LastEvaluatedKey" not in resp:
            return rows
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def _json_default(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    raise TypeError(f"Not JSON serialisable: {type(o).__name__}")
