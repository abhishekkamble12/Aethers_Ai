"""
Trigger Lambda: the only way decision runs start (EventBridge schedule, demo script, manual).

The Step Functions execution name is derived from decision_id = tenant#date#session, and
Standard workflows reject a second execution with the same name (ExecutionAlreadyExists,
for 90 days). So a duplicate scheduler event or a double click cannot plan, ask for approval
or send notices twice. Deliberate re-runs (demo resets) must pass a visible `rerun_label`.
"""

import json
import logging
import os
import re
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from services.planner.handler import parse_run_input

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RERUN_LABEL_RE = re.compile(r"^[a-z0-9]{1,12}$")


def execution_name(decision_id: str, rerun_label: str = "") -> str:
    name = re.sub(r"[^A-Za-z0-9_-]", "_", decision_id)
    if rerun_label:
        name = f"{name}__rerun_{rerun_label}"
    return name[:80]


def _sfn():
    return boto3.client("stepfunctions")


def trigger_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    run = parse_run_input(event or {})  # raises ValueError on bad input: the invocation fails visibly
    rerun_label = (event or {}).get("rerun_label", "")
    if rerun_label and not RERUN_LABEL_RE.match(str(rerun_label)):
        raise ValueError("rerun_label must match [a-z0-9]{1,12}")

    name = execution_name(run["decision_id"], rerun_label)
    execution_input = {k: run[k] for k in ("tenant_id", "stage", "date", "session", "forecast_source")}
    state_machine_arn = os.environ["STATE_MACHINE_ARN"]
    sfn = _sfn()

    # StartExecution alone cannot tell us we were a duplicate: for a RUNNING execution with the same
    # name and input it succeeds and returns the original. Look it up first so the report is honest.
    # Concurrent triggers that both pass this check still produce one execution (AWS dedupes by name).
    existing = _describe(sfn, execution_arn(state_machine_arn, name))
    if existing:
        return _duplicate(name, run, existing)
    try:
        resp = sfn.start_execution(stateMachineArn=state_machine_arn, name=name,
                                   input=json.dumps(execution_input))
    except ClientError as e:
        if e.response["Error"]["Code"] == "ExecutionAlreadyExists":  # closed run, or a different input
            return _duplicate(name, run, _describe(sfn, execution_arn(state_machine_arn, name)))
        raise
    logger.info("Started %s", name)
    return {"status": "started", "execution_name": name, "execution_arn": resp["executionArn"],
            "decision_id": run["decision_id"]}


def execution_arn(state_machine_arn: str, name: str) -> str:
    return state_machine_arn.replace(":stateMachine:", ":execution:", 1) + f":{name}"


def _describe(sfn, arn: str):
    try:
        return sfn.describe_execution(executionArn=arn)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ExecutionDoesNotExist":
            return None
        raise


def _duplicate(name: str, run: Dict[str, str], existing) -> Dict[str, Any]:
    logger.info("Duplicate trigger suppressed for %s", name)
    return {"status": "duplicate_suppressed", "execution_name": name, "decision_id": run["decision_id"],
            "existing_status": (existing or {}).get("status")}
