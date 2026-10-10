"""
Decision item helpers. decision_id = "{tenant_id}#{date}#{session}", e.g. "TENANT#demo#2026-10-12#MORN".
Item: PK={tenant_id}  SK=DEC#{date}#{session}
"""

import re
from typing import Dict, Tuple

DECISION_ID_RE = re.compile(r"^(TENANT#[a-z0-9_-]{1,40})#(\d{4}-\d{2}-\d{2})#(EVE|MORN)$")


def decision_key(decision_id: str) -> Dict[str, str]:
    tenant_id, date_str, session = parse_decision_id(decision_id)
    return {"PK": tenant_id, "SK": f"DEC#{date_str}#{session}"}


def parse_decision_id(decision_id: str) -> Tuple[str, str, str]:
    m = DECISION_ID_RE.match(decision_id or "")
    if not m:
        raise ValueError(f"Malformed decision_id: {decision_id!r}")
    return m.group(1), m.group(2), m.group(3)
