"""
Period-level PM2.5 forecast for one school day.

live:   Open-Meteo Air Quality API (CAMS model) hourly PM2.5 for the school's location, averaged over
        each period's minutes; pessimistic = nominal x (1 + delta). Cached per grid cell and date in
        DynamoDB (GRID#{cell}#{date} / FCST) for CACHE_HOURS.
replay: the labelled demo forecast in data/demo (a recorded Stage III-type day).

A live request falls back to replay automatically when the API fails, times out, returns incomplete
hours, or the date is outside the forecast horizon. The result then says is_replay=True with a
fallback_reason, and the planner records a FORECAST_FALLBACK_REPLAY audit event. It never silently
substitutes.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
MODEL = "CAMS via Open-Meteo Air Quality API"
CACHE_HOURS = 6
TIMEOUT_SECONDS = 5
SOURCES = ("live", "replay")
_DEMO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "demo")


def load_school() -> Dict[str, Any]:
    with open(os.path.join(_DEMO, "school.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_replay() -> Dict[str, Any]:
    with open(os.path.join(_DEMO, "forecast_stage3_sample.json"), "r", encoding="utf-8") as f:
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

    query = urllib.parse.urlencode({"latitude": school["lat"], "longitude": school["lon"], "hourly": "pm2_5",
                                    "timezone": "Asia/Kolkata", "start_date": date_str, "end_date": date_str})
    url = f"{API_URL}?{query}"
    try:
        data = (fetch or http_get_json)(url)
        if data.get("error"):
            raise ValueError(data.get("reason", "API error"))
        periods = map_hourly_to_periods(data.get("hourly", {}), date_str, period_windows(timetable), delta)
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
