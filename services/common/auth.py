"""
Shared authentication and authorization helpers.
Validates admin requests via x-saans-admin-key header and ADMIN_API_KEY environment variable.
"""

import hmac
import os
from typing import Any, Dict

from services.common.http import ApiError, header


def require_admin(event: Dict[str, Any]) -> None:
    """
    Validates that the event carries the valid x-saans-admin-key header.
    Raises ApiError(503) if ADMIN_API_KEY is unset, or ApiError(401) if invalid/missing.
    """
    expected = os.environ.get("ADMIN_API_KEY", "")
    if not expected:
        raise ApiError(503, "not_configured", "ADMIN_API_KEY is not configured.")
    supplied = header(event, "x-saans-admin-key") or ""
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise ApiError(401, "unauthorized", "Missing or invalid x-saans-admin-key header.")
