"""
Period-level and hourly PM2.5 forecast for school operations.

live:   Open-Meteo Air Quality API (CAMS model) hourly PM2.5 for the school's location.
        - Hourly: returned directly with school_hours flags and product thresholds. Cached
          in DynamoDB (GRID#{cell}#H{hours}#{yyyy-mm-ddThh} / FCST) for 1 hour.
        - Period-level: minute-weighted average over each period; pessimistic = nominal x (1 + delta).
          Cached in DynamoDB (GRID#{cell}#{date} / FCST) for CACHE_HOURS.
replay: labelled demo forecast in data/demo (a recorded Stage III-type day).

A live request falls back to replay automatically when the API fails, times out, returns incomplete
hours, or the date is outside the forecast horizon. The result then says source="replay" with a
fallback_reason. It never silently substitutes.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
MODEL = "CAMS via Open-Meteo Air Quality API"
CACHE_HOURS = 6
CACHE_SECONDS_HOURLY = 3600
TIMEOUT_SECONDS = 5
SOURCES = ("live", "replay")
IST = timezone(timedelta(hours=5, minutes=30))
_DEMO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "demo")

STAGE3_HOURLY_PROFILE = [
    120.0, 125.0, 135.0, 145.0, 160.0, 175.0, 190.0, 200.0,  # 00:00 - 07:00
    210.0, 280.0, 360.0, 395.0, 340.0, 260.0, 140.0,         # 08:00 - 14:00 (P1 - P7)
    95.0,  115.0, 140.0, 180.0, 220.0, 250.0, 230.0, 180.0, 140.0  # 15:00 - 23:00 (P8, evening peak)
]


def load_school() -> Dict[str, Any]:
    with open(os.path.join(_DEMO, "school.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_replay() -> Dict[str, Any]:
    with open(os.path.join(_DEMO, "forecast_stage3_sample.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_ruleset() -> Dict[str, Any]:
    with open(os.path.join(_DEMO, "ruleset_v1.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_class_profiles() -> Dict[str, Any]:
    with open(os.path.join(_DEMO, "class_profiles.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_sensitivity_policy() -> Dict[str, Any]:
    with open(os.path.join(_DEMO, "sensitivity_policy.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def http_get_json(url: str) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "saans-hackathon/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Open-Meteo explains 4xx errors in a JSON body, e.g. a date beyond the forecast horizon.
        try:
            reason = json.loads(e.read().decode("utf-8")).get("reason")
        except Exception:
            reason = None
        raise ValueError(f"HTTP {e.code}: {reason or e.reason}") from None


def _minutes(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def period_windows(timetable: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    seen = {}
    for r in timetable:
        seen.setdefault(r["period"], (r["start"], r["end"]))
    return sorted(((p, s, e) for p, (s, e) in seen.items()), key=lambda x: _minutes(x[1]))


def is_school_hour(time_str: str) -> bool:
    """School periods run 08:30-14:45 on school days (Monday to Saturday, not Sunday)."""
    try:
        h = int(time_str[11:13])
        dt = datetime.fromisoformat(time_str[:19])
        return 8 <= h <= 14 and dt.weekday() < 6
    except Exception:
        return False


def compute_thresholds(ruleset: Optional[Dict[str, Any]] = None,
                       profiles: Optional[Dict[str, Any]] = None,
                       policy: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    ruleset = ruleset or load_ruleset()
    profiles = profiles or load_class_profiles()
    policy = policy or load_sensitivity_policy()

    adv_pm = ruleset.get("advisory_pm25", {})
    adv_val = adv_pm.get("advisory_at", 90)
    res_val = adv_pm.get("restricted_at", 120)
    ruleset_ver = ruleset.get("ruleset_version", "2026-10-08-r1")

    floor = float(policy.get("floor", 0.6))
    per_student = float(policy.get("per_student", 0.05))

    stricter_set = set()
    for c in profiles.get("classes", []):
        n = c.get("sensitive_count", 0)
        if isinstance(n, int) and n > 0:
            mult = round(min(1.0, max(floor, 1.0 - per_student * n)), 3)
            stricter_set.add(round(res_val * mult, 1))

    stricter_values = sorted(list(stricter_set))

    return [
        {
            "name": "advisory",
            "value": adv_val,
            "basis": f"ruleset {ruleset_ver} (product default, not an official limit)".strip(),
        },
        {
            "name": "restricted",
            "value": res_val,
            "basis": f"ruleset {ruleset_ver}".strip(),
        },
        {
            "name": "stricter limit for sensitive classes",
            "values": stricter_values,
            "basis": policy.get("basis", "policy"),
        },
    ]


# The replay is a hand-built Stage III scenario for demos and outages. It is not output from any
# forecasting model, so it must never carry a real model's name.
REPLAY_MODEL = "Illustrative Stage III scenario (hand-built, not a model forecast)"


def load_replay_hourly(hours: int = 48, base_dt: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Generates synthetic hourly PM2.5 data for the labelled Stage III replay scenario."""
    if base_dt is None:
        base_dt = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    points = []
    for i in range(hours):
        t = base_dt + timedelta(hours=i)
        t_str = t.strftime("%Y-%m-%dT%H:00+05:30")
        pm25 = STAGE3_HOURLY_PROFILE[t.hour % 24]
        points.append({
            "time": t_str,
            "pm25": pm25,
            "school_hours": is_school_hour(t_str),
        })
    return points


def fetch_hourly(school: Dict[str, Any],
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 hours: Optional[int] = None,
                 fetch: Optional[Callable[[str], Dict[str, Any]]] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Fetches hourly PM2.5 from Open-Meteo Air Quality API (CAMS model).
    Returns (url, [{"time": "2026-10-12T00:00", "pm25": 51.7}, ...]).
    Raises ValueError on missing data or API errors.
    """
    query: Dict[str, Any] = {
        "latitude": school["lat"],
        "longitude": school["lon"],
        "hourly": "pm2_5",
        "timezone": "Asia/Kolkata",
    }
    if start_date and end_date:
        query["start_date"] = start_date
        query["end_date"] = end_date
    elif hours is not None:
        query["forecast_hours"] = hours

    url = f"{API_URL}?{urllib.parse.urlencode(query)}"
    data = (fetch or http_get_json)(url)
    if data.get("error"):
        raise ValueError(data.get("reason", "API error"))
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    pm25s = hourly.get("pm2_5", [])
    if not times or not pm25s or len(times) != len(pm25s):
        raise ValueError("incomplete hourly PM2.5 data returned by API")
    points = []
    for t, v in zip(times, pm25s):
        if v is None:
            raise ValueError(f"no PM2.5 value for {t}")
        points.append({"time": t, "pm25": float(v)})
    return url, points


def map_hourly_to_periods(hourly: Dict[str, Any], date_str: str, windows, delta: float) -> List[Dict[str, Any]]:
    """Minute-weighted mean of the hourly values overlapping each period. Raises ValueError if any needed hour is missing."""
    by_hour = {}
    for t, v in zip(hourly.get("time", []), hourly.get("pm2_5", [])):
        if t.startswith(date_str) and v is not None:
            by_hour[int(t[11:13])] = float(v)
    periods = []
    for prd, start, end in windows:
        s, e = _minutes(start), _minutes(end)
        total, weighted = 0, 0.0
        for h in range(s // 60, (e - 1) // 60 + 1):
            overlap = min(e, (h + 1) * 60) - max(s, h * 60)
            if overlap <= 0:
                continue
            if h not in by_hour:
                raise ValueError(f"no PM2.5 value for {date_str} {h:02d}:00")
            total += overlap
            weighted += overlap * by_hour[h]
        nominal = round(weighted / total, 1)
        periods.append({"period": prd, "start": start, "end": end, "pm25_nominal": nominal,
                        "pm25_pessimistic": round(nominal * (1 + delta), 1)})
    return periods


def get_forecast(date_str: str, timetable: List[Dict[str, Any]], source: str = "live", table=None,
                 school: Optional[Dict[str, Any]] = None, fetch: Optional[Callable[[str], Dict[str, Any]]] = None,
                 delta: float = 0.20, now: Optional[float] = None) -> Dict[str, Any]:
    if source not in SOURCES:
        raise ValueError(f"forecast_source must be one of {SOURCES}")
    if source == "replay":
        return {**load_replay(), "is_replay": True, "requested_source": "replay", "fallback_reason": None}

    school = school or load_school()
    now = now if now is not None else time.time()
    cache_key = {"PK": f"GRID#{school['grid_cell']}#{date_str}", "SK": "FCST"}

    if table is not None:
        try:
            cached = table.get_item(Key=cache_key).get("Item")
            if cached and now - float(cached["fetched_at_epoch"]) < CACHE_HOURS * 3600:
                return {**json.loads(cached["forecast"]), "cache": "hit"}
        except Exception:
            logger.exception("Forecast cache read failed; fetching live")

    try:
        url, points = fetch_hourly(school, start_date=date_str, end_date=date_str, fetch=fetch)
        hourly_dict = {"time": [p["time"] for p in points], "pm2_5": [p["pm25"] for p in points]}
        periods = map_hourly_to_periods(hourly_dict, date_str, period_windows(timetable), delta)
    except Exception as e:
        reason = f"{type(e).__name__}: {str(e)[:160]}"
        logger.warning("Live forecast unavailable (%s); using labelled replay", reason)
        return {**load_replay(), "is_replay": True, "requested_source": "live", "fallback_reason": reason}

    forecast = {
        "grid_cell": school["grid_cell"], "date": date_str, "model": MODEL, "source_url": url,
        "generated_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
        "is_replay": False, "requested_source": "live", "fallback_reason": None,
        "pessimistic_rule": f"nominal x {1 + delta:.2f}", "periods": periods,
    }
    if table is not None:
        try:
            table.put_item(Item={**cache_key, "forecast": json.dumps(forecast), "fetched_at_epoch": int(now),
                                 "ttl": int(now) + 2 * 86400})
        except Exception:
            logger.exception("Forecast cache write failed (continuing with live data)")
    return {**forecast, "cache": "miss"}


def get_hourly_forecast(tenant_id: str = "demo",
                        hours: int = 48,
                        source: str = "live",
                        table=None,
                        school: Optional[Dict[str, Any]] = None,
                        fetch: Optional[Callable[[str], Dict[str, Any]]] = None,
                        now: Optional[float] = None) -> Dict[str, Any]:
    if source not in SOURCES:
        raise ValueError(f"forecast_source must be one of {SOURCES}")

    school = school or load_school()
    now = now if now is not None else time.time()
    ruleset = load_ruleset()
    profiles = load_class_profiles()
    policy = load_sensitivity_policy()

    thresholds = compute_thresholds(ruleset, profiles, policy)
    restricted_threshold = thresholds[1]["value"]

    # Determine stage
    stage = os.environ.get("DELHI_STAGE_DEFAULT", "III")
    if table is not None:
        try:
            from services.admin.seed import declared_stage as get_declared_stage
            t_key = tenant_id if tenant_id.startswith("TENANT#") else f"TENANT#{tenant_id}"
            s = get_declared_stage(table, t_key)
            if s:
                stage = s
        except Exception:
            pass

    dt_ist = datetime.fromtimestamp(now, IST)
    hour_bucket = dt_ist.strftime("%Y-%m-%dT%H")

    if source == "replay":
        replay_dt = dt_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        hours_data = load_replay_hourly(hours=hours, base_dt=replay_dt)
        first_crossing_time = next((p["time"] for p in hours_data if p["pm25"] >= restricted_threshold), None)
        return {
            "source": "replay",
            "label": "replay forecast",
            "model": REPLAY_MODEL,
            "generated_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "fallback_reason": None,
            "unit": "µg/m³ (PM2.5, hourly mean)",
            "hours": hours_data,
            "thresholds": thresholds,
            "first_crossing": {"threshold": "restricted", "time": first_crossing_time},
            "declared_stage": {"stage": stage, "label": "REPLAY SCENARIO"},
            "note": "Saans never declares a GRAP stage; thresholds decide advisory/restricted only within what the order allows.",
            "cache": "bypass",
        }

    # Live path with DynamoDB cache
    cache_key = {"PK": f"GRID#{school['grid_cell']}#H{hours}", "SK": "FCST"}
    if table is not None:
        try:
            cached = table.get_item(Key=cache_key).get("Item")
            if cached and now - float(cached["fetched_at_epoch"]) < CACHE_SECONDS_HOURLY:
                return {**json.loads(cached["forecast"]), "cache": "hit"}
        except Exception:
            logger.exception("Hourly forecast cache read failed; fetching live")

    try:
        url, raw_points = fetch_hourly(school, hours=hours, fetch=fetch)
        formatted_hours = []
        for p in raw_points[:hours]:
            t_str = p["time"]
            if not ("+" in t_str or t_str.endswith("Z")):
                t_str = f"{t_str}+05:30"
            formatted_hours.append({
                "time": t_str,
                "pm25": p["pm25"],
                "school_hours": is_school_hour(t_str),
            })
        first_crossing_time = next((p["time"] for p in formatted_hours if p["pm25"] >= restricted_threshold), None)
        forecast_resp = {
            "source": "live",
            "label": "live forecast",
            "model": MODEL,
            "generated_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "fallback_reason": None,
            "unit": "µg/m³ (PM2.5, hourly mean)",
            "hours": formatted_hours,
            "thresholds": thresholds,
            "first_crossing": {"threshold": "restricted", "time": first_crossing_time},
            "declared_stage": {"stage": stage, "label": f"Stage {stage}"},
            "note": "Saans never declares a GRAP stage; thresholds decide advisory/restricted only within what the order allows.",
        }
        if table is not None:
            try:
                table.put_item(Item={
                    **cache_key,
                    "forecast": json.dumps(forecast_resp),
                    "fetched_at_epoch": int(now),
                    "ttl": int(now) + 2 * 86400,
                })
            except Exception:
                logger.exception("Hourly forecast cache write failed")
        return {**forecast_resp, "cache": "miss"}

    except Exception as e:
        reason = f"{type(e).__name__}: {str(e)[:160]}"
        logger.warning("Live hourly forecast unavailable (%s); using labelled replay", reason)
        replay_dt = dt_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        hours_data = load_replay_hourly(hours=hours, base_dt=replay_dt)
        first_crossing_time = next((p["time"] for p in hours_data if p["pm25"] >= restricted_threshold), None)
        return {
            "source": "replay",
            "label": "replay forecast",
            "model": REPLAY_MODEL,
            "generated_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "fallback_reason": reason,
            "unit": "µg/m³ (PM2.5, hourly mean)",
            "hours": hours_data,
            "thresholds": thresholds,
            "first_crossing": {"threshold": "restricted", "time": first_crossing_time},
            "declared_stage": {"stage": stage, "label": "REPLAY SCENARIO"},
            "note": "Saans never declares a GRAP stage; thresholds decide advisory/restricted only within what the order allows.",
            "cache": "bypass",
        }
