"""
hack_win M2b: every path through services/workflow/state_machine.json, plus the idempotent trigger.

AslRunner interprets the subset of Amazon States Language the definition uses (Task, Pass,
Choice, Catch, Retry ignored, ResultSelector, ResultPath, InputPath, Parameters with .$ paths).
A JSONPath that does not resolve raises, like States.Runtime in AWS. Lambda behaviour is
scripted per state. This checks data flow between states; the real run is verified on AWS.
"""

import copy
import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

from services.workflow.trigger import execution_name, trigger_handler  # noqa: E402

DEFINITION = json.loads((Path(__file__).resolve().parent.parent /
                         "services/workflow/state_machine.json").read_text(encoding="utf-8"))
RUN_INPUT = {"tenant_id": "TENANT#demo", "stage": "III", "date": "2026-10-12", "session": "MORN"}
DECISION_ID = "TENANT#demo#2026-10-12#MORN"


class StatesError(Exception):
    def __init__(self, error, cause=""):
        super().__init__(error)
        self.error, self.cause = error, cause


def get_path(data, path, context):
    if path == "$":
        return data
    root, rest = (context, path[3:]) if path.startswith("$$.") else (data, path[2:])
    cur = root
    for part in rest.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise StatesError("States.Runtime", f"path {path} not found")
        cur = cur[part]
    return cur


def is_present(data, path):
    try:
        get_path(data, path, {})
        return True
    except StatesError:
        return False


def resolve(template, data, context):
    if isinstance(template, dict):
        out = {}
        for k, v in template.items():
            if k.endswith(".$"):
                out[k[:-2]] = get_path(data, v, context)
            else:
                out[k] = resolve(v, data, context)
        return out
    return template


def set_path(data, path, value):
    if path == "$":
        return value
    data = copy.deepcopy(data)
    parts = path[2:].split(".")
    cur = data
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value
    return data


def choice_matches(rule, data):
    if "And" in rule:
        return all(choice_matches(r, data) for r in rule["And"])
    if "Or" in rule:
        return any(choice_matches(r, data) for r in rule["Or"])
    if "Not" in rule:
        return not choice_matches(rule["Not"], data)
    if "IsPresent" in rule:
        return is_present(data, rule["Variable"]) == rule["IsPresent"]
    if "StringEquals" in rule:
        return is_present(data, rule["Variable"]) and get_path(data, rule["Variable"], {}) == rule["StringEquals"]
    raise NotImplementedError(rule)


class AslRunner:
    """behaviours: {state_name: callable(payload) -> result | raises StatesError}"""

    def __init__(self, definition, behaviours):
        self.d, self.behaviours, self.invocations = definition, behaviours, []

    def run(self, data):
        context = {"Execution": {"Name": "TENANT_demo_2026-10-12_MORN"}, "Task": {"Token": "TASK-TOKEN"}}
        name, path = self.d["StartAt"], []
        for _ in range(50):
            state = self.d["States"][name]
            path.append(name)
            t = state["Type"]
            if t == "Choice":
                name = next((r["Next"] for r in state["Choices"] if choice_matches(r, data)), state.get("Default"))
                if name is None:
                    raise StatesError("States.NoChoiceMatched")
                continue
            if t == "Pass":
                result = get_path(data, state.get("InputPath", "$"), context)
                data = set_path(data, state.get("ResultPath", "$"), result)
            elif t == "Task":
                payload = resolve(state["Parameters"]["Payload"], data, context)
                self.invocations.append((name, payload))
                try:
                    raw = self.behaviours[name](payload)
                    if not state["Resource"].endswith(".waitForTaskToken"):
                        raw = {"Payload": raw}  # lambda:invoke wraps the function result
                    result = resolve(state["ResultSelector"], raw, context) if "ResultSelector" in state else raw
                    data = set_path(data, state.get("ResultPath", "$"), result)
                except StatesError as e:
                    catch = next((c for c in state.get("Catch", [])
                                  if e.error in c["ErrorEquals"] or "States.ALL" in c["ErrorEquals"]), None)
                    if catch is None:
                        raise
                    data = set_path(data, catch["ResultPath"], {"Error": e.error, "Cause": e.cause})
                    name = catch["Next"]
                    continue
            else:
                raise NotImplementedError(t)
            if state.get("End"):
                return name, data, path
            name = state["Next"]
        raise RuntimeError("loop")


def timeout(_):
    raise StatesError("States.Timeout")


def answer(action, role):
    return lambda _p: {"action": action, "approver_role": role, "decided_at": "2026-10-11T02:00:00Z"}


def runner(status="pending_approval", **overrides):
    behaviours = {
        "LoadContext": lambda p: {"decision": {"decision_id": DECISION_ID, "status": status,
                                               "declared_stage": p["stage"], "plan_b": []},
                                  "audit_head": {"seq": 1}},
        "RequestPrincipalApproval": answer("APPROVE_PLAN_A", "principal"),
        "EscalateToVicePrincipal": answer("APPROVE_PLAN_B", "vice_principal"),
        "DraftAndDispatchNotices": lambda p: {"statusCode": 200},
    }
    for state in ("AuditCloseNoChange", "AuditCloseApproved", "FailSafeRejected", "FailSafeTimeout", "FailSafeError"):
        behaviours[state] = lambda p: {"event": p["event"], "persisted": False}
    behaviours.update(overrides)
    return AslRunner(DEFINITION, behaviours)


class TestWorkflowPaths(unittest.TestCase):

    def invoked(self, r, state):
        return [p for s, p in r.invocations if s == state]

    def test_definition_uses_only_supported_state_types(self):
        self.assertTrue({s["Type"] for s in DEFINITION["States"].values()} <= {"Task", "Pass", "Choice"})

    def test_principal_approves(self):
        r = runner()
        end, _, path = r.run(dict(RUN_INPUT))
        self.assertEqual(end, "AuditCloseApproved")
        self.assertNotIn("EscalateToVicePrincipal", path)
        draft = self.invoked(r, "DraftAndDispatchNotices")[0]
        self.assertEqual(draft["approval"]["action"], "APPROVE_PLAN_A")
        self.assertEqual(draft["stage"], "III")
        self.assertEqual(self.invoked(r, "AuditCloseApproved")[0]["approver_role"], "principal")

    def test_escalated_approval_reaches_notices(self):
        """The M2b bug: after a principal timeout, a VP approval used to hit a missing $.approval_result."""
        r = runner(RequestPrincipalApproval=timeout)
        end, _, path = r.run(dict(RUN_INPUT))
        self.assertEqual(end, "AuditCloseApproved")
        self.assertIn("EscalateToVicePrincipal", path)
        self.assertIs(self.invoked(r, "EscalateToVicePrincipal")[0]["escalation"], True)
        draft = self.invoked(r, "DraftAndDispatchNotices")[0]
        self.assertEqual(draft["approval"], {"action": "APPROVE_PLAN_B", "approver_role": "vice_principal",
                                             "decided_at": "2026-10-11T02:00:00Z"})

    def test_no_answer_fails_safe_without_notices(self):
        r = runner(RequestPrincipalApproval=timeout, EscalateToVicePrincipal=timeout)
        end, _, _ = r.run(dict(RUN_INPUT))
        self.assertEqual(end, "FailSafeTimeout")
        self.assertEqual(self.invoked(r, "FailSafeTimeout")[0]["event"], "FAILSAFE_TIMEOUT_NO_BROADCAST")
        self.assertEqual(self.invoked(r, "DraftAndDispatchNotices"), [])

    def test_principal_reject_is_recorded_as_rejection_not_timeout(self):
        r = runner(RequestPrincipalApproval=answer("REJECT", "principal"))
        end, _, _ = r.run(dict(RUN_INPUT))
        self.assertEqual(end, "FailSafeRejected")
        audit = self.invoked(r, "FailSafeRejected")[0]
        self.assertEqual((audit["event"], audit["action"], audit["approver_role"]),
                         ("REJECTED_NO_BROADCAST", "REJECT", "principal"))
        self.assertEqual(self.invoked(r, "DraftAndDispatchNotices"), [])

    def test_vice_principal_reject(self):
        r = runner(RequestPrincipalApproval=timeout, EscalateToVicePrincipal=answer("REJECT", "vice_principal"))
        end, _, _ = r.run(dict(RUN_INPUT))
        self.assertEqual(end, "FailSafeRejected")
        self.assertEqual(self.invoked(r, "FailSafeRejected")[0]["approver_role"], "vice_principal")

    def test_no_change_closes_without_asking(self):
        r = runner(status="confirmed_no_change")
        end, _, _ = r.run(dict(RUN_INPUT))
        self.assertEqual(end, "AuditCloseNoChange")
        self.assertEqual(self.invoked(r, "RequestPrincipalApproval"), [])

    def test_approval_step_error_fails_safe(self):
        def boom(_):
            raise StatesError("States.TaskFailed", "RequestApproval Lambda crashed")
        r = runner(RequestPrincipalApproval=boom)
        end, _, _ = r.run(dict(RUN_INPUT))
        self.assertEqual(end, "FailSafeError")
        audit = self.invoked(r, "FailSafeError")[0]
        self.assertEqual((audit["event"], audit["error"]), ("WORKFLOW_ERROR_NO_BROADCAST", "States.TaskFailed"))

    def test_notice_failure_is_not_recorded_as_notified(self):
        def boom(_):
            raise StatesError("States.TaskFailed", "Notify crashed")
        r = runner(DraftAndDispatchNotices=boom)
        end, _, path = r.run(dict(RUN_INPUT))
        self.assertEqual(end, "FailSafeError")
        self.assertNotIn("AuditCloseApproved", path)

    def test_every_audit_records_decision_and_execution(self):
        r = runner()
        r.run(dict(RUN_INPUT))
        audit = self.invoked(r, "AuditCloseApproved")[0]
        self.assertEqual(audit["decision_id"], DECISION_ID)
        self.assertEqual(audit["execution"], "TENANT_demo_2026-10-12_MORN")


@mock_aws
class TestIdempotentTrigger(unittest.TestCase):

    def setUp(self):
        sfn = boto3.client("stepfunctions")
        arn = sfn.create_state_machine(
            name="SaansWorkflow", definition=json.dumps({"StartAt": "A", "States": {"A": {"Type": "Succeed"}}}),
            roleArn="arn:aws:iam::123456789012:role/sfn")["stateMachineArn"]
        os.environ["STATE_MACHINE_ARN"] = arn
        self.sfn = sfn

    def test_duplicate_trigger_is_suppressed_by_step_functions(self):
        first = trigger_handler(dict(RUN_INPUT), None)
        second = trigger_handler(dict(RUN_INPUT), None)
        self.assertEqual(first["status"], "started")
        self.assertEqual(first["execution_name"], "TENANT_demo_2026-10-12_MORN")
        self.assertEqual(second["status"], "duplicate_suppressed")
        execs = self.sfn.list_executions(stateMachineArn=os.environ["STATE_MACHINE_ARN"])["executions"]
        self.assertEqual(len(execs), 1)
        started_input = json.loads(self.sfn.describe_execution(executionArn=first["execution_arn"])["input"])
        self.assertEqual(started_input, RUN_INPUT)

    def test_labelled_rerun_starts_a_separate_execution(self):
        trigger_handler(dict(RUN_INPUT), None)
        rerun = trigger_handler({**RUN_INPUT, "rerun_label": "demo2"}, None)
        self.assertEqual(rerun["status"], "started")
        self.assertEqual(rerun["execution_name"], "TENANT_demo_2026-10-12_MORN__rerun_demo2")

    def test_invalid_input_raises(self):
        for bad in ({"stage": "IX"}, {**RUN_INPUT, "rerun_label": "../x"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                trigger_handler(bad, None)

    def test_execution_name_is_valid_for_step_functions(self):
        name = execution_name("TENANT#" + "a" * 40 + "#2026-10-12#MORN", "x" * 12)
        self.assertLessEqual(len(name), 80)
        self.assertRegex(name, r"^[A-Za-z0-9_-]+$")


if __name__ == "__main__":
    unittest.main()
