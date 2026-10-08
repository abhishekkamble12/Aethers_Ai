"""
Ruleset Diff & Versioning Engine
Computes granular diffs (added, changed, removed) between active rulesets and candidate rulesets.
Enforces immutable versioning with cryptographic content hashing.
"""

import hashlib
import json
from typing import Dict, Any, List

def compute_ruleset_hash(ruleset: Dict[str, Any]) -> str:
    """Computes SHA256 digest of ruleset for immutable versioning."""
    canonical = json.dumps(ruleset, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

def compute_ruleset_diff(
    active_ruleset: Dict[str, Any],
    candidate_ruleset: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes diff between active and candidate rulesets.
    Returns:
    {
        "active_version": "2026-10-08-r1",
        "candidate_version": "2026-10-09-r2",
        "added_rules": [...],
        "changed_rules": [{"rule_id": ..., "before": ..., "after": ...}],
        "removed_rules": [...],
        "has_changes": True
    }
    """
    active_map = {r["rule_id"]: r for r in active_ruleset.get("rules", [])}
    candidate_map = {r["rule_id"]: r for r in candidate_ruleset.get("rules", [])}

    added = []
    changed = []
    removed = []

    # Check candidates for additions and modifications
    for r_id, cand_rule in candidate_map.items():
        if r_id not in active_map:
            added.append({
                "rule_id": r_id,
                "rule": cand_rule,
                "source_quote": cand_rule.get("source_quote"),
                "source_id": cand_rule.get("source_id")
            })
        else:
            active_rule = active_map[r_id]
            # Check if action or condition changed
            if cand_rule.get("action") != active_rule.get("action") or cand_rule.get("condition") != active_rule.get("condition"):
                changed.append({
                    "rule_id": r_id,
                    "before": active_rule,
                    "after": cand_rule,
                    "source_quote": cand_rule.get("source_quote"),
                    "source_id": cand_rule.get("source_id")
                })

    # Check for removed rules
    for r_id, act_rule in active_map.items():
        if r_id not in candidate_map:
            removed.append({
                "rule_id": r_id,
                "rule": act_rule,
                "source_quote": act_rule.get("source_quote")
            })

    has_changes = len(added) > 0 or len(changed) > 0 or len(removed) > 0

    return {
        "active_version": active_ruleset.get("ruleset_version", "v1"),
        "candidate_version": candidate_ruleset.get("ruleset_version", "v2-candidate"),
        "added_rules": added,
        "changed_rules": changed,
        "removed_rules": removed,
        "total_added": len(added),
        "total_changed": len(changed),
        "total_removed": len(removed),
        "has_changes": has_changes,
        "candidate_content_hash": compute_ruleset_hash(candidate_ruleset)
    }
