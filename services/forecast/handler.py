"""
AWS Lambda Handlers for Forecast endpoints.
Provides:
- GET /forecast (forecast_handler): public hourly PM2.5 chart data with product thresholds.
- GET /watch (watch_get_handler): contingency draft watches for the principal (admin key).
"""

import logging
import os
import re

import boto3
from boto3.dynamodb.conditions import Key

from services.common.auth import require_admin
from services.common.http import ApiError, guarded, respond
from services.forecast.ingest import get_hourly_forecast

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("TABLE_NAME", "SaansStateTable")
APP_REGION = os.environ.get("APP_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
TENANT_ID_RE = re.compile(r"^TENANT#[a-z0-9_-]{1,40}$")


def _get_table():
    try:
        return boto3.resource("dynamodb", region_name=APP_REGION).Table(TABLE_NAME)
    except Exception:
        return None


@guarded
def forecast_handler(event, context):
    """
    GET /forecast?tenant=demo&hours=48&source=live|replay
    Public endpoint: gives the frontend real hourly PM2.5 chart data with product thresholds.
    """
    params = (event.get("queryStringParameters") or {}) if isinstance(event, dict) else {}

    tenant = params.get("tenant", "demo")
    if not isinstance(tenant, str) or not tenant:
        raise ApiError(400, "invalid_tenant", "Parameter 'tenant' is required.")

    canonical_tenant = tenant if tenant.startswith("TENANT#") else f"TENANT#{tenant}"
    if not TENANT_ID_RE.match(canonical_tenant):
        raise ApiError(400, "invalid_tenant", "Parameter 'tenant' must be a valid tenant identifier.")

    hours_raw = params.get("hours", "48")
    try:
        hours = int(hours_raw)
        if not (1 <= hours <= 120):
            raise ValueError()
    except (TypeError, ValueError):
        raise ApiError(400, "invalid_hours", "Parameter 'hours' must be an integer between 1 and 120.")

    source = params.get("source", "live")
    if source not in ("live", "replay"):
        raise ApiError(400, "invalid_source", "Parameter 'source' must be one of: live, replay.")

    table = _get_table()
    data = get_hourly_forecast(
        tenant_id=tenant,
        hours=hours,
        source=source,
        table=table,
    )
    return respond(200, data)


@guarded
def watch_get_handler(event, context):
    """
    GET /watch?tenant=demo
    Admin endpoint (requires x-saans-admin-key): returns contingency draft watches for the tenant,
    plus promote_hint (the exact trigger payload to activate the plan).
    """
    require_admin(event)
    params = (event.get("queryStringParameters") or {}) if isinstance(event, dict) else {}

    tenant = params.get("tenant", "demo")
    canonical_tenant = tenant if tenant.startswith("TENANT#") else f"TENANT#{tenant}"
    if not TENANT_ID_RE.match(canonical_tenant):
        raise ApiError(400, "invalid_tenant", "Parameter 'tenant' must be a valid tenant identifier.")

    table = _get_table()
    watches = []
    if table is not None:
        try:
            resp = table.query(
                KeyConditionExpression=Key("PK").eq(canonical_tenant) & Key("SK").begins_with("WATCH#")
            )
            watches = resp.get("Items", [])
        except Exception:
            logger.exception("Failed to query watches for %s", canonical_tenant)

    watches = sorted(watches, key=lambda w: w.get("date", ""))

    return respond(200, {
        "tenant": tenant,
        "watches": watches,
        "promote_hint": promote_hint(canonical_tenant, watches),
    })


def promote_hint(tenant_id: str, watches) -> dict:
    """How a principal turns a contingency draft into a real run. There is no HTTP trigger route:
    runs start only through the Trigger Lambda (the 19:30 IST schedule invokes the same function)."""
    function_name = os.environ.get("TRIGGER_FUNCTION_NAME") or "<TriggerFunctionName stack output>"
    payloads = [{"tenant_id": tenant_id, "date": w.get("date"), "session": "MORN",
                 "forecast_source": w.get("forecast_source") or "live"}
                for w in watches if w.get("risk") == "act"]
    return {
        "description": ("Drafts are never active on their own. The 19:30 IST evening run plans the next "
                        "school day automatically; to start a run for a watched date now, invoke the Trigger "
                        "Lambda with one of these payloads (duplicates are refused per decision)."),
        "method": "aws lambda invoke",
        "function_name": function_name,
        "payloads": payloads,
        "example": (f"aws lambda invoke --function-name {function_name} --cli-binary-format raw-in-base64-out "
                    f"--payload '<payload json>' out.json"),
    }
