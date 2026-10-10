"""
GET /health?tenant=demo: one call that says what is working right now.

checks:  table (reachable, latency) · ruleset (version, sha256, rule count) · declared stage (tenant record) ·
         forecast (live or replay fallback for tomorrow, with reason and age) · bedrock (usable or why not) ·
         audit (head seq/hash and whether the chain verifies)
status:  ok        everything works
         degraded  the system runs on a labelled fallback (replay forecast, static notices) or is not seeded
         down      the table is unreachable or the audit chain does not verify   (HTTP 503)
No secrets, approval links or per-class sensitive counts are returned.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import boto3

from services.audit.hash_chain import verify_audit_chain
from services.audit.store import read_chain
from services.circular.diff_engine import compute_ruleset_hash
from services.common.http import ApiError, guarded, respond
from services.forecast.ingest import get_forecast, load_school

IST = timezone(timedelta(hours=5, minutes=30))
TENANT_RE = re.compile(r"^[a-z0-9_-]{1,40}$")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
BEDROCK_CHECK_TTL = 600
_bedrock_cache: Dict[str, Any] = {}


def _table():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def _bedrock_client():
    return boto3.client("bedrock-runtime")


def check_bedrock(now: float) -> Dict[str, Any]:
    """One 1-token call, cached for 10 minutes so health checks do not spend money."""
    if _bedrock_cache.get("at") and now - _bedrock_cache["at"] < BEDROCK_CHECK_TTL:
        return {**_bedrock_cache["result"], "cached": True}
    try:
        _bedrock_client().converse(modelId=BEDROCK_MODEL_ID, messages=[{"role": "user", "content": [{"text": "ok"}]}],
                                   inferenceConfig={"maxTokens": 1})
        result = {"usable": True, "model": BEDROCK_MODEL_ID}
    except Exception as e:
        code = getattr(e, "response", {}).get("Error", {}).get("Code", type(e).__name__)
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))[:160]
        result = {"usable": False, "model": BEDROCK_MODEL_ID, "error": f"{code}: {msg}",
                  "effect": "notices use the labelled static template (fallback_used=true)"}
    _bedrock_cache.update(at=now, result=result)
    return {**result, "cached": False}


def _ruleset() -> Dict[str, Any]:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "data", "demo", "ruleset_v1.json")
    with open(path, "r", encoding="utf-8") as f:
        rs = json.load(f)
    return {"version": rs.get("ruleset_version"), "sha256": compute_ruleset_hash(rs), "rules": len(rs.get("rules", [])),
            "jurisdiction": rs.get("jurisdiction")}


@guarded
def health_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    tenant = (event.get("queryStringParameters") or {}).get("tenant", "demo")
    if not TENANT_RE.match(tenant):
        raise ApiError(400, "invalid_tenant", "'tenant' must match [a-z0-9_-]{1,40}.")
    tenant_id, now = f"TENANT#{tenant}", time.time()
    checks: Dict[str, Any] = {}

    try:
        t0 = time.time()
        table = _table()
        meta = table.get_item(Key={"PK": tenant_id, "SK": "META"}).get("Item")
        checks["table"] = {"ok": True, "latency_ms": round((time.time() - t0) * 1000)}
    except Exception as e:
        checks["table"] = {"ok": False, "error": type(e).__name__}
        return respond(503, {"status": "down", "checks": checks, "checked_at": datetime.now(timezone.utc).isoformat()})

    checks["ruleset"] = _ruleset()
    checks["declared_stage"] = ({"stage": meta["declared_stage"], "source": meta.get("stage_source")} if meta
                                else {"stage": None, "note": "tenant not seeded: run scripts/seed_demo.py"})

    tomorrow = (datetime.now(IST).date() + timedelta(days=1)).isoformat()
    try:
        from services.planner.handler import _get_demo_fixtures
        timetable, _, _ = _get_demo_fixtures()
        fc = get_forecast(tomorrow, timetable, "live", table=table)
        checks["forecast"] = {"date": tomorrow, "source": "replay" if fc.get("is_replay") else "live",
                              "fallback_reason": fc.get("fallback_reason"), "model": fc.get("model"),
                              "generated_at": fc.get("generated_at"), "cache": fc.get("cache"),
                              "school_location": {k: load_school()[k] for k in ("lat", "lon")}}
    except Exception as e:
        checks["forecast"] = {"source": "error", "error": type(e).__name__}

    checks["bedrock"] = check_bedrock(now)

    rows = read_chain(table, tenant_id)
    ok, message, broken = verify_audit_chain(rows)
    checks["audit"] = {"rows": len(rows), "head_seq": rows[-1]["seq"] if rows else 0,
                       "head_hash": rows[-1]["hash"] if rows else None, "chain_valid": ok,
                       "message": message, "broken_seq": rows[broken]["seq"] if broken >= 0 else None}

    if not ok:
        status, code = "down", 503
    elif checks["forecast"].get("source") != "live" or not checks["bedrock"]["usable"] or not meta:
        status, code = "degraded", 200
    else:
        status, code = "ok", 200
    return respond(code, {"status": status, "tenant": tenant, "checks": checks,
                          "checked_at": datetime.now(timezone.utc).isoformat()})
