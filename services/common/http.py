"""
Shared API Gateway response helpers.
Every endpoint returns JSON with CORS headers; errors carry a stable code and a
human message, never a stack trace.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def respond(status: int, body: Any) -> Dict[str, Any]:
    return {"statusCode": status, "headers": CORS_HEADERS, "body": json.dumps(body, default=str)}


def error(status: int, code: str, message: str) -> Dict[str, Any]:
    return respond(status, {"error": {"code": code, "message": message}})


def is_http_event(event: Any) -> bool:
    """API Gateway (REST) proxy events carry httpMethod; Step Functions/EventBridge payloads do not."""
    return isinstance(event, dict) and "httpMethod" in event


def json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    raw = event.get("body")
    if raw in (None, ""):
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        raise ApiError(400, "invalid_json", "Request body must be valid JSON.")
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "Request body must be a JSON object.")
    return data


def header(event: Dict[str, Any], name: str) -> Optional[str]:
    headers = event.get("headers") or {}
    lname = name.lower()
    for k, v in headers.items():
        if k.lower() == lname:
            return v
    return None


def guarded(handler):
    """Wrap an HTTP handler: ApiError -> clean JSON error, anything else -> logged 500 with no details."""
    def wrapper(event, context):
        try:
            return handler(event, context)
        except ApiError as e:
            return error(e.status, e.code, e.message)
        except Exception:
            logger.exception("Unhandled error in %s", handler.__name__)
            return error(500, "internal_error", "Internal error. The incident was logged.")
    wrapper.__name__ = handler.__name__
    wrapper.__wrapped__ = handler
    return wrapper
