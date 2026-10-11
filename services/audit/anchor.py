"""
S3 Object Lock Anchor Module for Saans Audit Log
Anchors daily head hashes of audit chains into an S3 bucket with Object Lock COMPLIANCE mode.
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3

from services.audit.hash_chain import canonical_json, verify_audit_chain
from services.audit.store import read_chain

logger = logging.getLogger(__name__)

ANCHOR_KEY_RE = re.compile(r"^anchors/([^/]+)/([^/]+)/(\d{6})-([0-9a-f]{64})\.json$")
ANCHOR_SPEC = "S3 Object Lock COMPLIANCE mode: anchors/{school}/{chain}/{seq:06d}-{hash}.json"


class ChainNotAnchorable(Exception):
    pass


def school_of(tenant_id: str) -> str:
    """Extracts school ID from tenant_id, e.g. 'demo' from 'TENANT#demo'."""
    return tenant_id.split("#", 1)[1] if "#" in tenant_id else tenant_id


def chain_name(rows: List[Dict[str, Any]]) -> Optional[str]:
    """Unique identifier for a chain; uses the hash of row 1 (the genesis transaction)."""
    return rows[0]["hash"] if rows else None


def list_anchors(s3, bucket: str, tenant_id: str) -> List[Dict[str, Any]]:
    """Every anchor for the school, all chains, oldest first, read from the object keys alone."""
    anchors, kwargs = [], {"Bucket": bucket, "Prefix": f"anchors/{school_of(tenant_id)}/"}
    while True:
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            m = ANCHOR_KEY_RE.match(obj["Key"])
            if m:
                anchors.append({"chain": m.group(2), "seq": int(m.group(3)), "hash": m.group(4), "key": obj["Key"],
                                "anchoredAt": obj["LastModified"].astimezone(timezone.utc).isoformat()})
        if not resp.get("IsTruncated"):
            break
        kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    return sorted(anchors, key=lambda a: (a["anchoredAt"], a["seq"]))


def check_against_anchors(rows: List[Dict[str, Any]], anchors: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The first anchor of this chain that the rows no longer match, or None. rows are store.read_chain rows."""
    by_seq = {r["seq"]: r["hash"] for r in rows}
    for a in sorted(anchors, key=lambda a: a["seq"]):
        if by_seq.get(a["seq"]) != a["hash"]:
            return a
    return None


def anchor_tenant(table, s3, bucket: str, tenant_id: str, now: Optional[datetime] = None) -> Dict[str, Any]:
    rows = read_chain(table, tenant_id)
    if not rows:
        return {"tenant_id": tenant_id, "anchored": False, "reason": "empty_chain"}
    ok, message, _ = verify_audit_chain(rows)
    if not ok:
        raise ChainNotAnchorable(f"{tenant_id}: chain does not verify, not anchoring: {message}")
    chain = chain_name(rows)
    anchors = [a for a in list_anchors(s3, bucket, tenant_id) if a["chain"] == chain]
    mismatch = check_against_anchors(rows, anchors)
    if mismatch:
        raise ChainNotAnchorable(f"{tenant_id}: row #{mismatch['seq']} no longer matches the anchor "
                                 f"{mismatch['key']}; the chain was rewritten after it was anchored")

    head = rows[-1]
    if any(a["seq"] == head["seq"] for a in anchors):
        return {"tenant_id": tenant_id, "anchored": False, "reason": "head_already_anchored", "seq": head["seq"]}

    key = f"anchors/{school_of(tenant_id)}/{chain}/{head['seq']:06d}-{head['hash']}.json"
    body = {"tenant_id": tenant_id, "chain": chain, "seq": head["seq"], "hash": head["hash"],
            "anchored_at": (now or datetime.now(timezone.utc)).isoformat(),
            "chain_rows_verified": len(rows), "spec": ANCHOR_SPEC}
    # Object Lock buckets refuse a PUT without an integrity checksum; retention comes from the bucket default.
    resp = s3.put_object(Bucket=bucket, Key=key, Body=canonical_json(body).encode("utf-8"),
                         ContentType="application/json", ChecksumAlgorithm="SHA256")
    logger.info("Anchored %s head #%s in s3://%s/%s", tenant_id, head["seq"], bucket, key)
    return {"tenant_id": tenant_id, "anchored": True, "chain": chain, "seq": head["seq"], "hash": head["hash"],
            "key": key, "version_id": resp.get("VersionId")}


def anchor_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """EventBridge nightly schedule (or a manual invoke with {"tenant_ids": [...]})."""
    bucket = os.environ["ANCHOR_BUCKET"]
    tenants = (event or {}).get("tenant_ids") or [
        t.strip() for t in os.environ.get("ANCHOR_TENANTS", "TENANT#demo").split(",") if t.strip()]
    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    s3 = boto3.client("s3")
    results, failures = [], []
    for tenant_id in tenants:
        try:
            results.append(anchor_tenant(table, s3, bucket, tenant_id))
        except ChainNotAnchorable as e:
            logger.error("%s", e)
            failures.append(str(e))
    if failures:  # fail the invocation so the Lambda error alarm fires
        raise ChainNotAnchorable("; ".join(failures))
    return {"results": results}


def anchor_summary(s3, bucket: str, tenant_id: str, chain: Optional[str]) -> Dict[str, Any]:
    """What a receipt shows: this chain's anchors, the newest one's lock, and any other chains anchored for the school."""
    every = list_anchors(s3, bucket, tenant_id)
    mine = sorted((a for a in every if a["chain"] == chain), key=lambda a: a["seq"])
    others: Dict[str, Dict[str, Any]] = {}
    for a in every:
        if a["chain"] != chain:
            o = others.setdefault(a["chain"], {"chain": a["chain"], "anchors": 0, "lastSeq": 0, "lastAnchoredAt": None})
            o["anchors"] += 1
            o["lastSeq"] = max(o["lastSeq"], a["seq"])
            o["lastAnchoredAt"] = max(o["lastAnchoredAt"] or "", a["anchoredAt"])
    latest = dict(mine[-1]) if mine else None
    if latest:
        try:
            head = s3.head_object(Bucket=bucket, Key=latest["key"])
            latest["lockMode"] = head.get("ObjectLockMode")
            until = head.get("ObjectLockRetainUntilDate")
            latest["retainUntil"] = until.astimezone(timezone.utc).isoformat() if until else None
            latest["versionId"] = head.get("VersionId")
        except Exception as e:  # the listing alone still proves what was anchored
            logger.warning("Could not read the lock on %s: %s", latest["key"], e)
    return {"bucket": bucket, "chain": chain,
            "anchors": [{"seq": a["seq"], "hash": a["hash"], "anchoredAt": a["anchoredAt"]} for a in mine],
            "latest": latest, "otherChains": sorted(others.values(), key=lambda o: o["lastAnchoredAt"]),
            "spec": ANCHOR_SPEC}


def anchor_summary_or_none(tenant_id: str, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """For the receipt: None when anchoring is not deployed; never fails the receipt."""
    bucket = os.environ.get("ANCHOR_BUCKET")
    if not bucket:
        return None
    try:
        return anchor_summary(boto3.client("s3"), bucket, tenant_id, chain_name(rows))
    except Exception as e:
        logger.warning("Anchor lookup failed for %s: %s", tenant_id, e)
        return {"bucket": bucket, "chain": chain_name(rows), "anchors": [], "latest": None, "otherChains": [],
                "error": type(e).__name__}
