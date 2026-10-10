"""
hack_win M3a: persisted hash-chained audit log (services/audit/store.py) against moto DynamoDB.
"""

import hashlib
import os
import threading
import unittest

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

from services.audit.hash_chain import GENESIS_HASH, canonical_json, verify_audit_chain  # noqa: E402
from services.audit.store import append_audit, read_chain, read_head  # noqa: E402

TENANT = "TENANT#demo"


def make_table():
    return boto3.resource("dynamodb").create_table(
        TableName="SaansStateTable",
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                              {"AttributeName": "SK", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST")


@mock_aws
class TestAuditStore(unittest.TestCase):

    def setUp(self):
        self.table = make_table()

    def test_rows_link_from_genesis_and_verify(self):
        for i, event in enumerate(["PLAN_GENERATED", "APPROVAL_REQUESTED", "APPROVAL_RECEIVED"]):
            append_audit(self.table, TENANT, "workflow", event, {"decision_id": "d1", "i": i})
        rows = read_chain(self.table, TENANT)
        self.assertEqual([r["seq"] for r in rows], [1, 2, 3])
        self.assertEqual(rows[0]["prev_hash"], GENESIS_HASH)
        self.assertEqual(rows[1]["prev_hash"], rows[0]["hash"])
        ok, msg, _ = verify_audit_chain(rows)
        self.assertTrue(ok, msg)
        self.assertEqual(read_head(self.table, TENANT), (3, rows[-1]["hash"]))

    def test_stored_payload_matches_digest(self):
        append_audit(self.table, TENANT, "scheduler:planner", "PLAN_GENERATED", {"swaps": 2, "stage": "III"})
        row = read_chain(self.table, TENANT)[0]
        self.assertEqual(hashlib.sha256(canonical_json(row["payload"]).encode()).hexdigest(), row["payload_digest"])

    def test_tenants_have_independent_chains(self):
        append_audit(self.table, TENANT, "workflow", "A", {})
        append_audit(self.table, "TENANT#other", "workflow", "B", {})
        self.assertEqual(len(read_chain(self.table, TENANT)), 1)
        self.assertEqual(read_chain(self.table, "TENANT#other")[0]["seq"], 1)

    def test_concurrent_appends_produce_one_gapless_chain(self):
        """4 writers x 5 appends race on the head pointer.
        moto's transact_write_items is not thread-safe (it deep-copies tables for rollback while other
        threads write), so each transaction is serialised here to stand in for DynamoDB's own atomicity.
        Head reads stay unlocked and are slowed down, so writers really do build rows on stale heads."""
        import time
        import services.audit.store as store
        client = self.table.meta.client
        real_transact, real_read_head = client.transact_write_items, store.read_head
        lock, conflicts = threading.Lock(), []

        def atomic_transact(**kwargs):
            with lock:
                try:
                    return real_transact(**kwargs)
                except client.exceptions.TransactionCanceledException:
                    conflicts.append(1)
                    raise

        def slow_read_head(table, tenant_id):
            head = real_read_head(table, tenant_id)
            time.sleep(0.005)  # widen the read -> write window
            return head

        client.transact_write_items = atomic_transact
        store.read_head = slow_read_head
        self.addCleanup(setattr, store, "read_head", real_read_head)
        errors = []

        def worker(n):
            try:
                for i in range(5):
                    append_audit(self.table, TENANT, "workflow", f"W{n}_{i}", {"n": n, "i": i}, max_attempts=30)
            except Exception as e:  # surfaced below
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        rows = read_chain(self.table, TENANT)
        self.assertEqual([r["seq"] for r in rows], list(range(1, 21)))
        self.assertEqual(len({r["event"] for r in rows}), 20)  # nothing lost, nothing duplicated
        self.assertTrue(verify_audit_chain(rows)[0])
        self.assertGreater(len(conflicts), 0, "race was not exercised")

    def test_head_moved_by_another_writer_is_retried_not_forked(self):
        append_audit(self.table, TENANT, "workflow", "FIRST", {})
        import services.audit.store as store
        real_read_head, calls = store.read_head, []

        def stale_once(table, tenant_id):
            calls.append(1)
            return (0, GENESIS_HASH) if len(calls) == 1 else real_read_head(table, tenant_id)

        store.read_head = stale_once
        try:
            row = append_audit(self.table, TENANT, "workflow", "SECOND", {})
        finally:
            store.read_head = real_read_head
        self.assertEqual(row["seq"], 2)
        self.assertGreaterEqual(len(calls), 2)
        self.assertTrue(verify_audit_chain(read_chain(self.table, TENANT))[0])

    def test_idempotency_key_prevents_double_logging_on_retry(self):
        first = append_audit(self.table, TENANT, "workflow", "RUN_CLOSED", {"x": 1}, idempotency_key="exec1#RUN_CLOSED")
        append_audit(self.table, TENANT, "workflow", "OTHER", {})
        again = append_audit(self.table, TENANT, "workflow", "RUN_CLOSED", {"x": 1}, idempotency_key="exec1#RUN_CLOSED")
        self.assertEqual(again["seq"], first["seq"])
        self.assertEqual([r["event"] for r in read_chain(self.table, TENANT)], ["RUN_CLOSED", "OTHER"])

    def test_history_cannot_be_overwritten_by_append(self):
        append_audit(self.table, TENANT, "workflow", "A", {})
        # Force a writer to target seq 1 again: the AUD# not-exists condition must refuse it.
        with self.assertRaises(self.table.meta.client.exceptions.TransactionCanceledException):
            self.table.meta.client.transact_write_items(TransactItems=[{"Put": {
                "TableName": "SaansStateTable",
                "Item": {"PK": {"S": TENANT}, "SK": {"S": "AUD#000001"}, "event": {"S": "FORGED"}},
                "ConditionExpression": "attribute_not_exists(SK)"}}])
        self.assertEqual(read_chain(self.table, TENANT)[0]["event"], "A")

    def test_edited_payload_is_detected(self):
        append_audit(self.table, TENANT, "scheduler:planner", "PLAN_GENERATED", {"exposure_after": 0, "stage": "III"})
        self.table.update_item(Key={"PK": TENANT, "SK": "AUD#000001"}, UpdateExpression="SET payload = :p",
                               ExpressionAttributeValues={":p": '{"exposure_after":0,"stage":"I"}'})
        ok, msg, idx = verify_audit_chain(read_chain(self.table, TENANT))
        self.assertFalse(ok)
        self.assertIn("Tampered payload at seq 1", msg)

    def test_edited_row_is_detected_at_its_seq(self):
        for e in ("A", "B", "C"):
            append_audit(self.table, TENANT, "workflow", e, {})
        self.table.update_item(Key={"PK": TENANT, "SK": "AUD#000002"},
                               UpdateExpression="SET #e = :v", ExpressionAttributeNames={"#e": "event"},
                               ExpressionAttributeValues={":v": "APPROVED_PLAN_A"})
        ok, msg, idx = verify_audit_chain(read_chain(self.table, TENANT))
        self.assertFalse(ok)
        self.assertEqual(idx, 1)
        self.assertIn("seq 2", msg)


if __name__ == "__main__":
    unittest.main()
