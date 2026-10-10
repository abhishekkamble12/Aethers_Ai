"""
Forecast Watch: proactive early warning without ML (hack_win F2).
Checks the forecast for the next 2 school days, runs plan_schedule as a rehearsal,
and classifies risk into none / watch / act.
Stores a contingency draft in DynamoDB (PK=TENANT#demo, SK=WATCH#{date}) and,
if risk is 'act' and new, appends a provable CONTINGENCY_DRAFTED audit row.
Never declares a GRAP stage, never notifies parents, never creates a decision or token.
"""

import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

import boto3

from services.audit.store import append_audit
from services.forecast.ingest import get_forecast
from services.planner.handler import _get_demo_fixtures, _get_school_config
from services.planner.planner import plan_schedule

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
TABLE_NAME = os.environ.get("TABLE_NAME", "SaansStateTable")
APP_REGION = os.environ.get("APP_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))


def next_school_days(base_date: date, count: int = 2) -> List[date]:
    """Returns the next `count` school days (skipping Sunday, weekday 6)."""
    days = []
    curr = base_date + timedelta(days=1)
    while len(days) < count:
        if curr.weekday() < 6:  # Monday to Saturday
            days.append(curr)
        curr += timedelta(days=1)
    return days


def rehearsal_summary(plan: Dict[str, Any]) -> Dict[str, int]:
    """Counts from a plan_schedule() result. Keys must match what the planner actually returns."""
    flagged = [cp for cp in plan.get("classified_periods", [])
               if cp.get("is_outdoor") and cp.get("label") in ("banned", "restricted")]
    return {
        "problematic_count": len(flagged),
        "swaps_count": len(plan.get("plan_a", [])),
        "fallbacks_count": len(plan.get("plan_b", [])),
        "classes_with_stricter_limits": len({t["class"] for t in plan.get("decision_trace", [])
                                             if t.get("sensitivity")}),
    }


def run_watch(table=None,
              today: Optional[str] = None,
              source: str = "live",
              tenant_id: str = "TENANT#demo",
              school: Optional[Dict[str, Any]] = None,
              fetch: Optional[Callable] = None,
              now: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Runs early warning watch for the next 2 school days.
    """
    now = now if now is not None else time.time()
    t_key = tenant_id if tenant_id.startswith("TENANT#") else f"TENANT#{tenant_id}"

    if today is None:
        today_date = datetime.fromtimestamp(now, IST).date()
    else:
        today_date = date.fromisoformat(today)

    school_days = next_school_days(today_date, count=2)
    timetable, _, ruleset = _get_demo_fixtures()
    school_cfg = _get_school_config()

    # Determine stage from tenant record (no guessing)
    stage = os.environ.get("DELHI_STAGE_DEFAULT", "III")
    if table is not None:
        try:
            from services.admin.seed import declared_stage as get_declared_stage
            s = get_declared_stage(table, t_key)
            if s:
                stage = s
        except Exception:
            pass

    adv_val = ruleset.get("advisory_pm25", {}).get("advisory_at", 90)
    res_val = ruleset.get("advisory_pm25", {}).get("restricted_at", 120)

    # Class sensitivity policy & sensitive counts
    sensitive_counts = school_cfg.get("sensitive_counts", {})
    policy = school_cfg.get("sensitivity_policy", {})
    floor = float(policy.get("floor", 0.6))
    per_student = float(policy.get("per_student", 0.05))

    stricter_by_class = {}
    for cls, n in sensitive_counts.items():
        if isinstance(n, int) and n > 0:
            mult = round(min(1.0, max(floor, 1.0 - per_student * n)), 3)
            stricter_by_class[cls] = round(res_val * mult, 1)

    results = []

    for d in school_days:
        d_str = d.isoformat()
        fc = get_forecast(d_str, timetable, source=source, table=table, school=school, fetch=fetch, now=now)

        # Run planner as rehearsal (no decision_id, no DEC# item written)
        plan = plan_schedule(
            timetable=timetable,
            forecast=fc,
            ruleset=ruleset,
            declared_stage=stage,
            delta=0.20,
            venues=school_cfg["venues"],
            indoor_air=school_cfg["indoor_air"],
            class_sizes=school_cfg["class_sizes"],
            sensitive_counts=sensitive_counts,
            sensitivity_policy=policy
        )

        periods = fc.get("periods", [])
        peak_pm25 = max((p.get("pm25_nominal", 0.0) for p in periods), default=0.0)
        peak_period = max(periods, key=lambda p: p.get("pm25_nominal", 0.0))["period"] if periods else "P1"

        # Risk classification based on forecast and stricter limits
        risk = "none"
        risk_reason = "Forecast PM2.5 is within normal limits."

        # Check if sensitive class limit crossed
        sensitive_crossed = False
        sensitive_cls_name = None
        for p in periods:
            val = p.get("pm25_nominal", 0.0)
            for cls, limit in stricter_by_class.items():
                if val >= limit:
                    sensitive_crossed = True
                    sensitive_cls_name = cls
                    break
            if sensitive_crossed:
                break

        if peak_pm25 >= res_val:
            risk = "act"
            risk_reason = f"Forecast peak PM2.5 ({peak_pm25} µg/m³) exceeds restricted threshold ({res_val} µg/m³)."
        elif sensitive_crossed:
            risk = "act"
            risk_reason = f"Forecast crosses stricter limit for class {sensitive_cls_name} ({stricter_by_class[sensitive_cls_name]} µg/m³)."
        elif peak_pm25 >= adv_val:
            risk = "watch"
            risk_reason = f"Forecast peak PM2.5 ({peak_pm25} µg/m³) exceeds advisory threshold ({adv_val} µg/m³)."

        watch_item = {
            "PK": t_key,
            "SK": f"WATCH#{d_str}",
            "date": d_str,
            "risk": risk,
            "risk_reason": risk_reason,
            "peak_pm25": peak_pm25,
            "peak_period": peak_period,
            "forecast_source": fc.get("requested_source", source),
            "is_replay": fc.get("is_replay", False),
            "plan_summary": rehearsal_summary(plan),
            "forecast_summary": {
                "model": fc.get("model", "CAMS"),
                "periods_count": len(periods),
                "generated_at": fc.get("generated_at"),
            },
            "label": "CONTINGENCY DRAFT: not active until an order or the principal starts the day's run",
            "updated_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "ttl": int(now) + 7 * 86400,
        }

        from decimal import Decimal
        db_item = dict(watch_item)
        db_item["peak_pm25"] = Decimal(str(round(float(peak_pm25), 1)))

        if table is not None:
            # Check existing to prevent duplicate CONTINGENCY_DRAFTED audit rows
            prev_risk = None
            try:
                existing = table.get_item(Key={"PK": t_key, "SK": f"WATCH#{d_str}"}).get("Item")
                if existing:
                    prev_risk = existing.get("risk")
            except Exception:
                pass

            try:
                table.put_item(Item=db_item)
            except Exception:
                logger.exception("Failed to write WATCH item for %s", d_str)

            # Append audit event if risk is 'act' and new/higher
            if risk == "act" and prev_risk != "act":
                try:
                    append_audit(
                        table=table,
                        tenant_id=t_key,
                        actor_role="forecast:watch",
                        event="CONTINGENCY_DRAFTED",
                        payload={
                            "date": d_str,
                            "risk": "act",
                            "peak_pm25": peak_pm25,
                            "source": fc.get("requested_source", source),
                        }
                    )
                except Exception:
                    logger.exception("Failed to append CONTINGENCY_DRAFTED audit event for %s", d_str)

        results.append(watch_item)

    return results


def watch_handler(event, context):
    """EventBridge cron handler: runs daily at 16:30 IST; logs and never raises unhandled errors."""
    try:
        table = boto3.resource("dynamodb", region_name=APP_REGION).Table(TABLE_NAME)
        source = event.get("source", "live") if isinstance(event, dict) else "live"
        watches = run_watch(table=table, source=source)
        logger.info("Forecast watch completed: %d contingency drafts evaluated", len(watches))
        return {"statusCode": 200, "watches_evaluated": len(watches)}
    except Exception as e:
        logger.exception("Forecast watch scheduled run encountered an error: %s", e)
        return {"statusCode": 200, "error": str(e)[:160]}
