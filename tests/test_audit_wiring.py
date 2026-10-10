"""
hack_win M3a: the real Lambda handlers, driven through state_machine.json by the ASL interpreter
from test_workflow_paths, write one verifiable hash chain to (moto) DynamoDB.
"""

import json
import os
import unittest
from unittest import mock

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

from moto import mock_aws  # noqa: E402

from services.audit.handler import audit_event_handler  # noqa: E402
from services.audit.hash_chain import verify_audit_chain  # noqa: E402
from services.audit.store import read_chain  # noqa: E402
from services.notify import drafting  # noqa: E402
from services.notify.handler import notify_handler  # noqa: E402
from services.planner.handler import lambda_handler as planner  # noqa: E402
from services.workflow import handler as approve_mod  # noqa: E402
from services.workflow.decisions import decisions_handler  # noqa: E402
from services.workflow.request import request_approval_handler  # noqa: E402
from tests.test_audit_store import make_table  # noqa: E402
from tests.test_workflow_paths import DEFINITION, RUN_INPUT, AslRunner, StatesError  # noqa: E402

TENANT = "TENANT#demo"
ADMIN = "wiring-admin-key-0123456789"


@mock_aws
class TestAuditWiring(unittest.TestCase):

    def setUp(self):
        os.environ.update(TABLE_NAME="SaansStateTable", ADMIN_API_KEY=ADMIN, AWS_LAMBDA_FUNCTION_NAME="local-test")
        self.addCleanup(os.environ.pop, "AWS_LAMBDA_FUNCTION_NAME", None)
        self.table = make_table()
        self.bedrock = mock.patch.object(drafting, "_invoke_bedrock_nova", return_value=None)  # model unavailable
        self.bedrock.start()
        self.addCleanup(self.bedrock.stop)

    def human(self, action):
        """A waitForTaskToken behaviour: issue the link, then the approver answers via the real APIs."""
        def behaviour(payload):
            request_approval_handler(dict(payload, taskToken="TASK-TOKEN"), None)
            if action is None:
                raise StatesError("States.Timeout")
            brief = json.loads(decisions_handler({"httpMethod": "GET", "headers": {"x-saans-admin-key": ADMIN},
                                                  "queryStringParameters": {"tenant": "demo", "date": "2026-10-12"}},
                                                 None)["body"])
            sid = brief["approval"]["approve_url"].rsplit("/", 1)[1]
            sent = []

            class Sfn:
                def send_task_success(self, taskToken, output):
                    sent.append(json.loads(output))
            with mock.patch.object(approve_mod, "_sfn", lambda: Sfn()):
                resp = approve_mod.approval_handler({"httpMethod": "POST", "pathParameters": {"shortId": sid},
                                                     "body": json.dumps({"action": action})}, None)
            assert resp["statusCode"] == 200, resp["body"]
            return sent[0]
        return behaviour

    def run_workflow(self, principal, vice_principal="APPROVE_PLAN_B"):
        def lam(handler):  # Lambda handlers take (event, context)
            return lambda payload: handler(payload, None)
        audits = {s: lam(audit_event_handler) for s in ("AuditCloseNoChange", "AuditCloseApproved",
                                                        "FailSafeRejected", "FailSafeTimeout", "FailSafeError")}
        r = AslRunner(DEFINITION, {"LoadContext": lam(planner), "RequestPrincipalApproval": self.human(principal),
                                   "EscalateToVicePrincipal": self.human(vice_principal),
                                   "DraftAndDispatchNotices": lam(notify_handler), **audits})
        return r.run(dict(RUN_INPUT))

    def events(self):
        return [(r["actor_role"], r["event"]) for r in read_chain(self.table, TENANT)]

    def test_approved_run_writes_one_verifiable_chain(self):
        end, _, _ = self.run_workflow("APPROVE_PLAN_B")
        self.assertEqual(end, "AuditCloseApproved")
        self.assertEqual(self.events(), [
            ("scheduler:planner", "PLAN_GENERATED"),
            ("workflow", "APPROVAL_REQUESTED"),
            ("principal", "APPROVAL_RECEIVED"),
            ("workflow:notify", "NOTICES_DRAFTED"),
            ("workflow", "RUN_CLOSED_APPROVED_AND_NOTIFIED"),
        ])
        rows = read_chain(self.table, TENANT)
        ok, msg, _ = verify_audit_chain(rows)
        self.assertTrue(ok, msg)

        plan_row, notice_row, close_row = rows[0]["payload"], rows[3]["payload"], rows[4]["payload"]
        self.assertEqual(plan_row["declared_stage"], "III")
        self.assertEqual(plan_row["ruleset_version"], "2026-10-08-r1")
        self.assertTrue(plan_row["forecast"]["is_replay"])  # the replay forecast is labelled in the record
        self.assertEqual(len(plan_row["ruleset_sha256"]), 64)
        self.assertTrue(all(n["fallback_used"] for n in notice_row["notices"]))  # model was down: visible
        self.assertEqual((close_row["action"], close_row["approver_role"]), ("APPROVE_PLAN_B", "principal"))

        dec = self.table.get_item(Key={"PK": TENANT, "SK": "DEC#2026-10-12#MORN"})["Item"]
        self.assertEqual(int(dec["audit_seq"]), 1)
        self.assertEqual(dec["audit_hash"], rows[0]["hash"])

    def test_escalated_run_records_both_requests_and_vp_decision(self):
        end, _, _ = self.run_workflow(principal=None, vice_principal="APPROVE_PLAN_A")
        self.assertEqual(end, "AuditCloseApproved")
        events = self.events()
        self.assertIn(("vice_principal", "APPROVAL_RECEIVED"), events)
        requested = [r["payload"]["awaiting_role"] for r in read_chain(self.table, TENANT)
                     if r["event"] == "APPROVAL_REQUESTED"]
        self.assertEqual(requested, ["principal", "vice_principal"])
        self.assertTrue(verify_audit_chain(read_chain(self.table, TENANT))[0])

    def test_unanswered_run_records_fail_safe_and_no_notices(self):
        end, _, _ = self.run_workflow(principal=None, vice_principal=None)
        self.assertEqual(end, "FailSafeTimeout")
        events = [e for _, e in self.events()]
        self.assertEqual(events[-1], "FAILSAFE_TIMEOUT_NO_BROADCAST")
        self.assertNotIn("NOTICES_DRAFTED", events)

    def test_short_id_never_enters_the_chain(self):
        self.run_workflow("APPROVE_PLAN_A")
        dumped = json.dumps(read_chain(self.table, TENANT))
        token_items = self.table.scan(FilterExpression="begins_with(PK, :p)",
                                      ExpressionAttributeValues={":p": "TOKEN#"})["Items"]
        self.assertTrue(token_items)
        for item in token_items:
            self.assertNotIn(item["PK"].split("#", 1)[1], dumped)
        self.assertNotIn("TASK-TOKEN", dumped)

    def test_step_functions_retry_does_not_double_log(self):
        self.run_workflow("APPROVE_PLAN_A")
        before = len(read_chain(self.table, TENANT))
        replay = {"tenant_id": TENANT, "decision_id": "TENANT#demo#2026-10-12#MORN",
                  "execution": "TENANT_demo_2026-10-12_MORN", "event": "RUN_CLOSED_APPROVED_AND_NOTIFIED",
                  "action": "APPROVE_PLAN_A", "approver_role": "principal"}
        out = audit_event_handler(replay, None)  # Lambda retried by Step Functions
        self.assertEqual(out["seq"], before)
        self.assertEqual(len(read_chain(self.table, TENANT)), before)

    def test_final_status_is_written_to_the_decision(self):
        cases = (("APPROVE_PLAN_B", "APPROVE_PLAN_B", "APPROVED_AND_NOTIFIED"), (None, None, "FAILSAFE_TIMEOUT"),
                 ("REJECT", None, "REJECTED_NO_BROADCAST"))
        for principal, vp, expected in cases:
            with self.subTest(expected=expected):
                for item in self.table.scan()["Items"]:
                    self.table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                self.run_workflow(principal, vp)
                dec = self.table.get_item(Key={"PK": TENANT, "SK": "DEC#2026-10-12#MORN"})["Item"]
                self.assertEqual(dec["status"], expected)
                self.assertNotIn("approval_pending", dec)

    def test_unknown_audit_event_rejected(self):
        with self.assertRaises(ValueError):
            audit_event_handler({"tenant_id": TENANT, "event": "APPROVED_BY_HACKER"}, None)


if __name__ == "__main__":
    unittest.main()
