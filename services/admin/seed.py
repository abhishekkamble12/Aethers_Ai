"""
Demo reset and scenario seeding for one tenant.

reset_tenant:  deletes the tenant's decisions, audit chain (AUD#, AUDHEAD, AUDKEY#), approval tokens,
               receipts and forecast cache, so the next recording starts at audit record #1.
seed_scenario: writes the tenant META (school, declared GRAP stage) and records the stage change as the
               first audit row (STAGE_DECLARED). The scenario is labelled a replay: it is not today's order.

Step Functions keeps execution names for 90 days, so a reset also issues a new run label; demo runs pass it
as rerun_label to start a fresh execution for the same decision date.
"""

import secrets
from datetime import datetime, timezone
from typing import Any, Dict

from boto3.dynamodb.conditions import Attr, Key

from services.audit.store import append_audit
from services.forecast.ingest import load_school

STAGES = ("I", "II", "III", "IV")


def _delete_all(table, items) -> int:
    n = 0
    with table.batch_writer() as batch:
        for it in items:
            batch.delete_item(Key={"PK": it["PK"], "SK": it["SK"]})
            n += 1
    return n


def _query_all(table, **kwargs):
    while True:
        resp = table.query(**kwargs)
        yield from resp["Items"]
        if "LastEvaluatedKey" not in resp:
            return
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def _scan_all(table, **kwargs):
    while True:
        resp = table.scan(**kwargs)
        yield from resp["Items"]
        if "LastEvaluatedKey" not in resp:
            return
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def reset_tenant(table, tenant_id: str, grid_cell: str) -> Dict[str, int]:
    own = list(_query_all(table, KeyConditionExpression=Key("PK").eq(tenant_id), ProjectionExpression="PK, SK"))
    linked = list(_scan_all(table, FilterExpression=(Attr("PK").begins_with("TOKEN#") | Attr("PK").begins_with("RECEIPT#"))
                            & Attr("tenant_id").eq(tenant_id), ProjectionExpression="PK, SK"))
    cache = list(_scan_all(table, FilterExpression=Attr("PK").begins_with(f"GRID#{grid_cell}#"), ProjectionExpression="PK, SK"))
    return {"tenant_items": _delete_all(table, own), "tokens_and_receipts": _delete_all(table, linked),
            "forecast_cache": _delete_all(table, cache)}


def seed_scenario(table, from_stage: str = "II", to_stage: str = "III") -> Dict[str, Any]:
    if from_stage not in STAGES or to_stage not in STAGES:
        raise ValueError(f"stages must be in {STAGES}")
    school = load_school()
    tenant_id = school["tenant_id"]
    now = datetime.now(timezone.utc).isoformat()
    run_label = "r" + secrets.token_hex(4)
    stage_source = {"label": "REPLAY SCENARIO", "order": f"GRAP Stage {to_stage} invoked (recorded scenario, not a live order)",
                    "previous_stage": from_stage, "declared_at": now}
    table.put_item(Item={"PK": tenant_id, "SK": "META", "name": school["name"], "jurisdiction": school["jurisdiction"],
                         "grid_cell": school["grid_cell"], "declared_stage": to_stage, "stage_source": stage_source,
                         "demo_run_label": run_label, "seeded_at": now})
    row = append_audit(table, tenant_id, "admin:seed", "STAGE_DECLARED",
                       {"from_stage": from_stage, "to_stage": to_stage, "basis": stage_source["label"],
                        "order": stage_source["order"]})
    return {"tenant_id": tenant_id, "declared_stage": to_stage, "previous_stage": from_stage,
            "first_audit_seq": row["seq"], "run_label": run_label}


def declared_stage(table, tenant_id: str):
    item = table.get_item(Key={"PK": tenant_id, "SK": "META"}).get("Item")
    return (item or {}).get("declared_stage")
