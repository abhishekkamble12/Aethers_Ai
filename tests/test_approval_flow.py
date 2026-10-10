"""
hack_win M2a: approval loop (RequestApproval -> GET /decisions -> POST /approve) against
moto's in-process DynamoDB, plus contract checks between the planner, the state machine
definition and the SAM template.
Step Functions is replaced by a recording stub; the real execution is verified after deploy.
"""

import json
import os
import re
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from moto import mock_aws  # noqa: E402

from services.planner import handler as planner_handler  # noqa: E402
from services.workflow import handler as approve_mod  # noqa: E402
from services.workflow.decisions import decisions_handler  # noqa: E402
from services.workflow.request import request_approval_handler  # noqa: E402
from services.workflow.token_store import issue_token  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TENANT = "TENANT#demo"
DECISION_ID = "TENANT#demo#2026-10-12#MORN"
ADMIN_KEY = "test-admin-key-0123456789"


class StubSfn:
    def __init__(self, fail_code=None):
        self.calls, self.fail_code = [], fail_code

    def send_task_success(self, taskToken, output):
        if self.fail_code:
            raise ClientError({"Error": {"Code": self.fail_code, "Message": "x"}}, "SendTaskSuccess")
        self.calls.append({"taskToken": taskToken, "output": json.loads(output)})


def approve_event(short_id, body):
    return {"httpMethod": "POST", "pathParameters": {"shortId": short_id},
            "body": body if isinstance(body, str) else json.dumps(body)}


def decisions_event(key=ADMIN_KEY, **q):
    params = {"tenant": "demo", "date": "2026-10-12", "session": "MORN", **q}
    return {"httpMethod": "GET", "headers": {"x-saans-admin-key": key} if key else {},
            "queryStringParameters": params,
            "requestContext": {"domainName": "abc.execute-api.ap-south-1.amazonaws.com", "stage": "Prod"}}


@mock_aws
class TestApprovalFlow(unittest.TestCase):

    def setUp(self):
        os.environ["TABLE_NAME"] = "SaansStateTable"
        os.environ["ADMIN_API_KEY"] = ADMIN_KEY
        self.table = boto3.resource("dynamodb").create_table(
            TableName="SaansStateTable",
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                                  {"AttributeName": "SK", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST")
        self.table.put_item(Item={"PK": TENANT, "SK": "DEC#2026-10-12#MORN", "status": "PLANNED",
                                  "data": json.dumps({"decision_id": DECISION_ID, "plan_b": [{"class": "7A"}]})})
        self.sfn = StubSfn()
        self.sfn_patch = mock.patch.object(approve_mod, "_sfn", lambda: self.sfn)
        self.sfn_patch.start()

    def tearDown(self):
        self.sfn_patch.stop()

    def request(self, escalation=False):
        return request_approval_handler({"taskToken": "RAW-TASK-TOKEN-SECRET", "tenant_id": TENANT,
                                         "decision_id": DECISION_ID, "escalation": escalation}, None)

    def pending_short_id(self):
        resp = decisions_handler(decisions_event(), None)
        return json.loads(resp["body"])["approval"]["approve_url"].rsplit("/", 1)[1]

    # --- RequestApproval -------------------------------------------------------------
    def test_request_issues_principal_token_and_marks_decision(self):
        out = self.request()
        self.assertEqual(out["role"], "principal")
        self.assertNotIn("RAW-TASK-TOKEN-SECRET", json.dumps(out))
        item = self.table.get_item(Key={"PK": TENANT, "SK": "DEC#2026-10-12#MORN"})["Item"]
        self.assertEqual(item["status"], "AWAITING_PRINCIPAL")

    def test_escalation_issues_vice_principal_token(self):
        self.assertEqual(self.request(escalation=True)["role"], "vice_principal")

    def test_request_rejects_decision_of_other_tenant(self):
        with self.assertRaises(ValueError):
            request_approval_handler({"taskToken": "t", "tenant_id": "TENANT#other",
                                      "decision_id": DECISION_ID}, None)

    # --- GET /decisions ---------------------------------------------------------------
    def test_decisions_requires_admin_key(self):
        self.assertEqual(decisions_handler(decisions_event(key=None), None)["statusCode"], 401)
        self.assertEqual(decisions_handler(decisions_event(key="wrong-key"), None)["statusCode"], 401)

    def test_decisions_not_configured_without_env_secret(self):
        del os.environ["ADMIN_API_KEY"]
        self.assertEqual(decisions_handler(decisions_event(), None)["statusCode"], 503)

    def test_decisions_validates_and_404s(self):
        self.assertEqual(decisions_handler(decisions_event(date="12-10-2026"), None)["statusCode"], 400)
        self.assertEqual(decisions_handler(decisions_event(tenant="DROP TABLE"), None)["statusCode"], 400)
        self.assertEqual(decisions_handler(decisions_event(date="2026-10-13"), None)["statusCode"], 404)

    def test_decisions_shows_pending_link_and_plan(self):
        self.request()
        body = json.loads(decisions_handler(decisions_event(), None)["body"])
        self.assertEqual(body["status"], "AWAITING_PRINCIPAL")
        self.assertEqual(body["approval"]["waiting_for_role"], "principal")
        self.assertTrue(body["approval"]["approve_url"].startswith(
            "https://abc.execute-api.ap-south-1.amazonaws.com/Prod/approve/"))
        self.assertEqual(body["plan"]["plan_b"][0]["class"], "7A")

    # --- POST /approve/{shortId} ------------------------------------------------------
    def test_approve_resumes_workflow_with_role_from_token_not_body(self):
        self.request()
        sid = self.pending_short_id()
        resp = approval = approve_mod.approval_handler(
            approve_event(sid, {"action": "APPROVE_PLAN_B", "approver_id": "vice_principal"}), None)
        self.assertEqual(resp["statusCode"], 200, approval["body"])
        self.assertEqual(len(self.sfn.calls), 1)
        self.assertEqual(self.sfn.calls[0]["taskToken"], "RAW-TASK-TOKEN-SECRET")
        self.assertEqual(self.sfn.calls[0]["output"]["action"], "APPROVE_PLAN_B")
        self.assertEqual(self.sfn.calls[0]["output"]["approver_role"], "principal")  # body claim ignored
        item = self.table.get_item(Key={"PK": TENANT, "SK": "DEC#2026-10-12#MORN"})["Item"]
        self.assertEqual(item["status"], "APPROVE_PLAN_B")
        self.assertNotIn("approval_pending", item)

    def test_link_is_single_use(self):
        self.request()
        sid = self.pending_short_id()
        self.assertEqual(approve_mod.approval_handler(approve_event(sid, {"action": "REJECT"}), None)["statusCode"], 200)
        second = approve_mod.approval_handler(approve_event(sid, {"action": "APPROVE_PLAN_A"}), None)
        self.assertEqual(second["statusCode"], 410)
        self.assertEqual(len(self.sfn.calls), 1)

    def test_expired_link_rejected(self):
        issued = issue_token(self.table, "tok", TENANT, DECISION_ID, "principal", window_seconds=60, now=1_000)
        resp = approve_mod.approval_handler(approve_event(issued["short_id"], {"action": "APPROVE_PLAN_A"}), None)
        self.assertEqual(resp["statusCode"], 410)

    def test_input_validation_returns_clean_errors(self):
        self.request()
        sid = self.pending_short_id()
        cases = [(approve_event("../etc", {"action": "REJECT"}), 400, "invalid_short_id"),
                 (approve_event(sid, {}), 400, "invalid_action"),
                 (approve_event(sid, {"action": "APPROVE_EVERYTHING"}), 400, "invalid_action"),
                 (approve_event(sid, "{not json"), 400, "invalid_json")]
        for event, status, code in cases:
            resp = approve_mod.approval_handler(event, None)
            self.assertEqual(resp["statusCode"], status)
            body = json.loads(resp["body"])
            self.assertEqual(body["error"]["code"], code)
            self.assertNotIn("Traceback", resp["body"])
        self.assertEqual(self.sfn.calls, [])  # nothing consumed the token
        self.assertEqual(approve_mod.approval_handler(approve_event(sid, {"action": "REJECT"}), None)["statusCode"], 200)

    def test_timed_out_execution_returns_409(self):
        self.request()
        sid = self.pending_short_id()
        self.sfn.fail_code = "TaskTimedOut"
        resp = approve_mod.approval_handler(approve_event(sid, {"action": "APPROVE_PLAN_A"}), None)
        self.assertEqual(resp["statusCode"], 409)

    def test_transient_workflow_error_keeps_link_usable(self):
        self.request()
        sid = self.pending_short_id()
        self.sfn.fail_code = "ServiceUnavailable"
        self.assertEqual(approve_mod.approval_handler(approve_event(sid, {"action": "APPROVE_PLAN_A"}), None)["statusCode"], 502)
        self.sfn.fail_code = None
        self.assertEqual(approve_mod.approval_handler(approve_event(sid, {"action": "APPROVE_PLAN_A"}), None)["statusCode"], 200)

    def test_unexpected_error_does_not_leak(self):
        with mock.patch.object(approve_mod, "_table", side_effect=RuntimeError("secret internals")):
            resp = approve_mod.approval_handler(approve_event("abcdefgh", {"action": "REJECT"}), None)
        self.assertEqual(resp["statusCode"], 500)
        self.assertNotIn("secret internals", resp["body"])


class TestPlannerAndWorkflowContract(unittest.TestCase):

    def test_step_functions_invocation_returns_plain_decision(self):
        out = planner_handler.lambda_handler({"tenant_id": TENANT, "stage": "3", "date": "2026-10-12"}, None)
        self.assertEqual(set(out), {"decision", "audit_head", "receipt_id"})  # what LoadContext's ResultSelector reads
        self.assertEqual(out["decision"]["decision_id"], DECISION_ID)
        self.assertEqual(out["decision"]["declared_stage"], "III")

    def test_load_context_selects_only_fields_the_planner_returns(self):
        sm = json.loads((ROOT / "services/workflow/state_machine.json").read_text(encoding="utf-8"))
        selected = {v.split(".", 2)[2] for v in sm["States"]["LoadContext"]["ResultSelector"].values()}
        out = planner_handler.lambda_handler({"tenant_id": TENANT, "stage": "III", "date": "2026-10-12"}, None)
        self.assertTrue(selected <= set(out), f"ResultSelector reads {selected - set(out)} the planner does not return")

    def test_step_functions_invalid_input_fails_execution(self):
        for bad in ({"stage": "V"}, {"date": "tomorrow"}, {"tenant_id": "demo"}, {"session": "NOON"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                planner_handler.lambda_handler(bad, None)

    def test_date_defaults_to_tomorrow_ist(self):
        from datetime import datetime, timedelta
        out = planner_handler.lambda_handler({}, None)
        tomorrow = (datetime.now(planner_handler.IST).date() + timedelta(days=1)).isoformat()
        self.assertEqual(out["decision"]["decision_id"], f"TENANT#demo#{tomorrow}#MORN")

    def test_rehearse_rejects_bad_stage_cleanly(self):
        resp = planner_handler.rehearse_handler({"httpMethod": "POST", "body": json.dumps({"stage": "VII"})}, None)
        self.assertEqual(resp["statusCode"], 400)
        self.assertEqual(json.loads(resp["body"])["error"]["code"], "invalid_stage")

    def test_state_machine_placeholders_and_timeouts_match_template(self):
        sm_text = (ROOT / "services/workflow/state_machine.json").read_text(encoding="utf-8")
        tpl = (ROOT / "infra/template.yaml").read_text(encoding="utf-8")
        subs_block = tpl.split("DefinitionSubstitutions:", 1)[1].split("Policies:", 1)[0]
        subs = set(re.findall(r"^\s+(\w+):", subs_block, re.M))
        self.assertEqual(set(re.findall(r"\$\{(\w+)\}", sm_text)), subs)

        sm = json.loads(sm_text)
        env_timeout = int(re.search(r'APPROVAL_TIMEOUT_SECONDS: "(\d+)"', tpl).group(1))
        for state, esc in (("RequestPrincipalApproval", False), ("EscalateToVicePrincipal", True)):
            s = sm["States"][state]
            self.assertEqual(s["TimeoutSeconds"], env_timeout)
            self.assertEqual(s["Parameters"]["FunctionName"], "${RequestApprovalFunctionArn}")
            self.assertIs(s["Parameters"]["Payload"]["escalation"], esc)
        self.assertEqual(sm["States"]["LoadContext"]["ResultSelector"]["decision.$"], "$.Payload.decision")


if __name__ == "__main__":
    unittest.main()
