"""
AWS Lambda Handlers for Ingest, Planner, and Stage Rehearsal
"""

import json
import logging
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any

import boto3

from services.planner.planner import plan_schedule
from services.planner.csv_loader import load_timetable_csv
from services.audit.hash_chain import compute_payload_digest
from services.audit.store import append_audit
from services.circular.diff_engine import compute_ruleset_hash
from services.common.http import ApiError, guarded, is_http_event, json_body, respond

logger = logging.getLogger()
logger.setLevel(logging.INFO)

STAGES = ("I", "II", "III", "IV")
STAGE_ALIASES = {"1": "I", "2": "II", "3": "III", "4": "IV"}
SESSIONS = ("EVE", "MORN")
TENANT_ID_RE = re.compile(r"^TENANT#[a-z0-9_-]{1,40}$")
IST = timezone(timedelta(hours=5, minutes=30))

TABLE_NAME = os.environ.get("TABLE_NAME", "SaansStateTable")

def _get_demo_fixtures():
    """Loads default fixtures for local and demo execution."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    csv_path = os.path.join(base_dir, "data", "demo", "timetable_sample.csv")
    forecast_path = os.path.join(base_dir, "data", "demo", "forecast_stage3_sample.json")
    ruleset_path = os.path.join(base_dir, "data", "demo", "ruleset_v1.json")

    with open(csv_path, "r", encoding="utf-8") as f:
        timetable_records, _ = load_timetable_csv(f.read())

    with open(forecast_path, "r", encoding="utf-8") as f:
        forecast_data = json.load(f)

    with open(ruleset_path, "r", encoding="utf-8") as f:
        ruleset_data = json.load(f)

    return timetable_records, forecast_data, ruleset_data


def _get_school_config() -> Dict[str, Any]:
    """Venues, indoor-air assumptions and class sizes (counts only) for the demo school."""
    demo = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "demo")
    def load(name):
        with open(os.path.join(demo, name), "r", encoding="utf-8") as f:
            return json.load(f)
    profiles = validate_class_profiles(load("class_profiles.json")["classes"])
    return {
        "venues": load("venues.json")["venues"],
        "indoor_air": load("indoor_air.json"),
        "class_sizes": {c["class"]: c["students"] for c in profiles},
        "sensitive_counts": {c["class"]: c.get("sensitive_count", 0) for c in profiles},
        "sensitivity_policy": load("sensitivity_policy.json"),
    }


PROFILE_FIELDS = {"class", "students", "sensitive_count"}


def validate_class_profiles(classes):
    """Class profiles hold counts only. Anything else (names, roll numbers, conditions per child) is refused."""
    for c in classes:
        extra = set(c) - PROFILE_FIELDS
        if extra:
            raise ValueError(f"class profile for {c.get('class')!r} has non-count fields {sorted(extra)}; counts only")
        n, total = c.get("sensitive_count", 0), c.get("students")
        if not isinstance(total, int) or total <= 0 or not isinstance(n, int) or not 0 <= n <= total:
            raise ValueError(f"class profile for {c.get('class')!r} needs integer students > 0 and 0 <= sensitive_count <= students")
    return classes


def redact_sensitive_counts(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Public responses keep the stricter thresholds but not how many children in a class have a condition."""
    for t in plan.get("decision_trace", []):
        sv = t.get("sensitivity")
        if sv:
            sv["sensitive_count"] = "redacted"
            sv["applied"] = (f"stricter threshold applied for students with respiratory conditions "
                             f"(advisory {sv['advisory_at']}, restricted {sv['restricted_at']} \u00b5g/m\u00b3)")
    return plan


def normalise_stage(raw: Any) -> str:
    """Accepts I-IV or 1-4; raises ValueError otherwise."""
    stage = STAGE_ALIASES.get(str(raw).strip(), str(raw).strip().upper())
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {', '.join(STAGES)} (or 1-4), got {raw!r}")
    return stage


def parse_run_input(event: Dict[str, Any]) -> Dict[str, str]:
    """Validates a planner run request. The date defaults to tomorrow in IST: the evening run plans the next school day."""
    tenant_id = event.get("tenant_id", "TENANT#demo")
    if not isinstance(tenant_id, str) or not TENANT_ID_RE.match(tenant_id):
        raise ValueError("tenant_id must look like TENANT#<id> with id matching [a-z0-9_-]{1,40}")
    raw_date = event.get("date") or (datetime.now(IST).date() + timedelta(days=1)).isoformat()
    try:
        date_str = date.fromisoformat(str(raw_date)).isoformat()
    except ValueError:
        raise ValueError(f"date must be YYYY-MM-DD, got {raw_date!r}")
    session = event.get("session", "MORN")
    if session not in SESSIONS:
        raise ValueError(f"session must be EVE or MORN, got {session!r}")
    return {
        "tenant_id": tenant_id,
        "stage": normalise_stage(event.get("stage", "III")),
        "date": date_str,
        "session": session,
        "decision_id": f"{tenant_id}#{date_str}#{session}",
    }


def run_planner(run: Dict[str, str], execution: str = "") -> Dict[str, Any]:
    """Plans one decision, persists it and its audit row when running in AWS, returns {decision, audit_head}."""
    timetable_records, forecast_data, ruleset_data = _get_demo_fixtures()

    plan_result = plan_schedule(
        timetable=timetable_records,
        forecast=forecast_data,
        ruleset=ruleset_data,
        declared_stage=run["stage"],
        school_jurisdiction="Delhi",
        decision_id=run["decision_id"],
        day=date.fromisoformat(run["date"]).strftime("%A"),
        **_get_school_config()
    )

    # What the decision was based on, so the audit row alone explains it.
    audit_payload = {
        "decision_id": run["decision_id"],
        "declared_stage": run["stage"],
        "ruleset_version": ruleset_data.get("ruleset_version"),
        "ruleset_sha256": compute_ruleset_hash(ruleset_data),
        "forecast": {k: forecast_data.get(k) for k in ("grid_cell", "date", "generated_at", "model", "is_replay")},
        "timetable_sha256": compute_payload_digest(timetable_records),
        "plan_sha256": compute_payload_digest(plan_result),
        "swaps_count": len(plan_result["plan_a"]),
        "fallbacks_count": len(plan_result["plan_b"]),
        "exposure_before": plan_result["exposure_before"],
        "exposure_after": plan_result["exposure_after"],
        "pe_minutes_preserved": plan_result["pe_minutes_preserved"],
        "indoor_air_assumptions": _get_school_config()["indoor_air"]["infiltration"],
        # Policy only: per-class sensitive counts never enter the public audit chain.
        "sensitivity_policy": {k: v for k, v in _get_school_config()["sensitivity_policy"].items() if k != "note"},
        "classes_with_stricter_limits": sum(1 for t in plan_result.get("decision_trace", []) if t.get("sensitivity"))
    }

    audit_row, receipt_id = None, None
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        # Fail loudly: a workflow must never wait for approval of a decision that was not stored.
        table = boto3.resource("dynamodb").Table(TABLE_NAME)
        # Public, opaque receipt ID for this decision (printable as a QR on notices).
        receipt_id = secrets.token_urlsafe(9)
        table.put_item(Item={"PK": f"RECEIPT#{receipt_id}", "SK": "META", "tenant_id": run["tenant_id"],
                             "decision_id": run["decision_id"]},
                       ConditionExpression="attribute_not_exists(PK)")
        audit_payload["receipt_id"] = receipt_id  # plan_sha256 above covers plan_result unchanged
        audit_row = append_audit(
            table, run["tenant_id"], "scheduler:planner", "PLAN_GENERATED", audit_payload,
            idempotency_key=f"{execution}#PLAN_GENERATED" if execution else None)
        table.put_item(
            Item={
                "PK": run["tenant_id"],
                "SK": f"DEC#{run['date']}#{run['session']}",
                "GSI1PK": "STATUS#PENDING",
                "GSI1SK": run["date"],
                "status": "PLANNED",
                "declared_stage": run["stage"],
                "data": json.dumps(plan_result),
                "receipt_id": receipt_id,
                "audit_seq": audit_row["seq"],
                "audit_hash": audit_row["hash"]
            }
        )

    # audit_head / receipt_id are None for local runs: nothing was persisted, so there is no chain to point at.
    return {"decision": plan_result, "audit_head": audit_row, "receipt_id": receipt_id}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Planner entry point.
    - Step Functions (LoadContext) / EventBridge: returns the plain {decision, audit_head} dict
      that the state machine's ResultSelector reads; invalid input raises, failing the execution visibly.
    - API Gateway: same result wrapped in an HTTP response, with clean 400s.
    """
    if not is_http_event(event):
        return run_planner(parse_run_input(event or {}), execution=str((event or {}).get("execution", "")))
    return _planner_http(event, context)


@guarded
def _planner_http(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        run = parse_run_input(json_body(event))
    except ValueError as e:
        raise ApiError(400, "invalid_input", str(e))
    return respond(200, run_planner(run))


@guarded
def rehearse_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Stage Rehearsal API handler:
    Runs instant what-if plan for requested stage (I-IV or 1-4) with zero DB mutations.
    """
    params = event.get("queryStringParameters") or {}
    raw_stage = json_body(event).get("stage", params.get("stage", "III"))
    try:
        stage = normalise_stage(raw_stage)
    except ValueError as e:
        raise ApiError(400, "invalid_stage", str(e))

    timetable_records, forecast_data, ruleset_data = _get_demo_fixtures()

    plan_result = plan_schedule(
        timetable=timetable_records,
        forecast=forecast_data,
        ruleset=ruleset_data,
        declared_stage=stage,
        school_jurisdiction="Delhi",
        decision_id=f"REHEARSAL#STAGE_{stage}",
        **_get_school_config()
    )
    plan_result["declared_stage"] = stage
    return respond(200, redact_sensitive_counts(plan_result))
