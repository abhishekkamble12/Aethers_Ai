"""
Test suite for Hash-Chained Audit Log and Tamper-Detection
"""

import unittest
from services.audit.hash_chain import (
    GENESIS_HASH,
    create_audit_row,
    verify_audit_chain
)

class TestAuditChain(unittest.TestCase):

    def test_valid_chain(self):
        row1 = create_audit_row(seq=1, prev_hash=GENESIS_HASH, actor_role="scheduler", event="INGEST_FORECAST", payload={"pm25": 280})
        row2 = create_audit_row(seq=2, prev_hash=row1["hash"], actor_role="planner", event="GENERATE_PLAN", payload={"swaps": 2})
        row3 = create_audit_row(seq=3, prev_hash=row2["hash"], actor_role="principal", event="APPROVE_PLAN", payload={"plan": "A"})

        chain = [row1, row2, row3]
        valid, msg, broken_idx = verify_audit_chain(chain)
        self.assertTrue(valid)
        self.assertEqual(broken_idx, -1)

    def test_tamper_detection(self):
        row1 = create_audit_row(seq=1, prev_hash=GENESIS_HASH, actor_role="scheduler", event="INGEST_FORECAST", payload={"pm25": 280})
        row2 = create_audit_row(seq=2, prev_hash=row1["hash"], actor_role="planner", event="GENERATE_PLAN", payload={"swaps": 2})
        
        # Malicious actor tampers with row 1's event or timestamp
        row1["event"] = "MALICIOUS_EVENT"

        chain = [row1, row2]
        valid, msg, broken_idx = verify_audit_chain(chain)
        self.assertFalse(valid)
        self.assertEqual(broken_idx, 0)
        self.assertIn("Tampered record", msg)

    def test_broken_link_detection(self):
        row1 = create_audit_row(seq=1, prev_hash=GENESIS_HASH, actor_role="scheduler", event="INGEST_FORECAST", payload={"pm25": 280})
        row2 = create_audit_row(seq=2, prev_hash="f" * 64, actor_role="planner", event="GENERATE_PLAN", payload={"swaps": 2}) # wrong prev_hash

        chain = [row1, row2]
        valid, msg, broken_idx = verify_audit_chain(chain)
        self.assertFalse(valid)
        self.assertEqual(broken_idx, 1)
        self.assertIn("Broken prev_hash link", msg)

if __name__ == "__main__":
    unittest.main()
