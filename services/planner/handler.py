"""
AWS Lambda Handlers for Ingest, Planner, and Stage Rehearsal
"""

import json
import os
import boto3
from typing import Dict, Any

from services.planner.planner import plan_schedule
from services.planner.csv_loader import load_timetable_csv
from services.audit.hash_chain import GENESIS_HASH, create_audit_row

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


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Scheduled or on-demand execution handler:
    1. Loads context (timetable, forecast, ruleset, declared stage)
    2. Runs deterministic planner
    3. Writes Decision and Audit row
    """
    tenant_id = event.get("tenant_id", "TENANT#demo")
    declared_stage = event.get("stage", "III")
    date_str = event.get("date", "2026-10-12")
    decision_id = f"{tenant_id}#{date_str}#MORN"

    timetable_records, forecast_data, ruleset_data = _get_demo_fixtures()

    # Run deterministic planner
    plan_result = plan_schedule(
        timetable=timetable_records,
        forecast=forecast_data,
        ruleset=ruleset_data,
        declared_stage=declared_stage,
        school_jurisdiction="Delhi",
        decision_id=decision_id
    )

    # Generate tamper-evident audit row
    audit_row = create_audit_row(
        seq=1,
        prev_hash=GENESIS_HASH,
        actor_role="scheduler:planner",
        event="DECISION_PLAN_GENERATED",
        payload={
            "decision_id": decision_id,
            "swaps_count": len(plan_result["plan_a"]),
            "fallbacks_count": len(plan_result["plan_b"]),
            "exposure_before": plan_result["exposure_before"],
            "exposure_after": plan_result["exposure_after"],
            "pe_minutes_preserved": plan_result["pe_minutes_preserved"]
        }
    )

    response_payload = {
        "statusCode": 200,
        "decision": plan_result,
        "audit_head": audit_row
    }

    # If running inside AWS with DynamoDB available:
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        try:
            dynamodb = boto3.resource("dynamodb")
            table = dynamodb.Table(TABLE_NAME)
            
            # Put Decision item
            table.put_item(
                Item={
                    "PK": tenant_id,
                    "SK": f"DEC#{date_str}#MORN",
                    "GSI1PK": "STATUS#PENDING",
                    "GSI1SK": date_str,
                    "data": json.dumps(plan_result),
                    "audit_head_hash": audit_row["hash"]
                }
            )
            # Put Audit row
            table.put_item(
                Item={
                    "PK": tenant_id,
                    "SK": f"AUD#{audit_row['seq']:06d}",
                    "data": json.dumps(audit_row)
                }
            )
        except Exception as e:
            response_payload["db_warning"] = str(e)

    return {
        "statusCode": 200,
        "headers": { "Content-Type": "application/json" },
        "body": json.dumps(response_payload)
    }


def rehearse_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Stage Rehearsal API handler:
    Runs instant what-if plan for requested stage (I, II, III, IV) with zero DB mutations.
    """
    params = event.get("queryStringParameters") or {}
    stage = params.get("stage", "III")
    
    # Also support JSON body if called via POST body
    if "body" in event and event["body"]:
        try:
            body_data = json.loads(event["body"])
            stage = body_data.get("stage", stage)
        except Exception:
            pass

    timetable_records, forecast_data, ruleset_data = _get_demo_fixtures()

    plan_result = plan_schedule(
        timetable=timetable_records,
        forecast=forecast_data,
        ruleset=ruleset_data,
        declared_stage=stage,
        school_jurisdiction="Delhi",
        decision_id=f"REHEARSAL#STAGE_{stage}"
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(plan_result)
    }
