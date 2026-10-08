"""
Hash-Chained Audit Log Module
Implements tamper-evident audit trail:
hash_n = SHA256( hash_{n-1} || canonical_json(row_n) )
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

GENESIS_HASH = "0" * 64

def canonical_json(obj: Dict[str, Any]) -> str:
    """Returns deterministic, canonical JSON string (sorted keys, compact)."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))

def compute_payload_digest(payload: Any) -> str:
    """Computes SHA256 digest of any payload data."""
    if isinstance(payload, str):
        data = payload.encode('utf-8')
    else:
        data = canonical_json(payload).encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def compute_row_hash(prev_hash: str, row_body: Dict[str, Any]) -> str:
    """
    Computes hash_n = SHA256( prev_hash || canonical_json(row_body) )
    """
    content = prev_hash + canonical_json(row_body)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def create_audit_row(
    seq: int,
    prev_hash: str,
    actor_role: str,
    event: str,
    payload: Any,
    timestamp: str = None
) -> Dict[str, Any]:
    """
    Creates an immutable AuditRow with computed SHA256 hash chain link.
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    payload_digest = compute_payload_digest(payload)
    
    row_body = {
        "seq": seq,
        "actor_role": actor_role,
        "event": event,
        "payload_digest": payload_digest,
        "ts": ts
    }
    
    row_hash = compute_row_hash(prev_hash, row_body)
    
    return {
        "seq": seq,
        "prev_hash": prev_hash,
        "hash": row_hash,
        "actor_role": actor_role,
        "event": event,
        "payload_digest": payload_digest,
        "ts": ts
    }

def verify_audit_chain(rows: List[Dict[str, Any]]) -> Tuple[bool, str, int]:
    """
    Recomputes the hash chain from genesis to head.
    Returns (is_valid, message, broken_seq_index).
    """
    if not rows:
        return True, "Audit log is empty (valid).", -1

    current_expected_prev = GENESIS_HASH

    for idx, row in enumerate(rows):
        seq = row.get("seq")
        prev_hash = row.get("prev_hash")
        row_hash = row.get("hash")

        # 1. Sequence check
        if seq != idx + 1:
            return False, f"Broken sequence at index {idx}: expected seq {idx+1}, got {seq}", idx

        # 2. Previous hash link check
        if prev_hash != current_expected_prev:
            return False, f"Broken prev_hash link at seq {seq}: expected {current_expected_prev}, got {prev_hash}", idx

        # 3. Hash recomputation check
        row_body = {
            "seq": row.get("seq"),
            "actor_role": row.get("actor_role"),
            "event": row.get("event"),
            "payload_digest": row.get("payload_digest"),
            "ts": row.get("ts")
        }
        recomputed = compute_row_hash(prev_hash, row_body)
        if recomputed != row_hash:
            return False, f"Tampered record at seq {seq}! Recomputed hash {recomputed} does not match {row_hash}", idx

        current_expected_prev = row_hash

    return True, f"All {len(rows)} records mathematically verified against SHA256 chain.", -1
