"""
Demo readiness: one-command reset + seeded stage change, stage read from the tenant record, GET /health.
"""

import json
import os
import unittest
from unittest import mock

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

import services.health.handler as health  # noqa: E402
import services.forecast.ingest as ingest  # noqa: E402
from services.admin.seed import declared_stage, reset_tenant, seed_scenario  # noqa: E402
from services.audit.store import append_audit, read_chain  # noqa: E402
from services.workflow.trigger import trigger_handler  # noqa: E402
from tests.test_audit_store import make_table  # noqa: E402
from tests.test_forecast import API_RESPONSE  # noqa: E402

DEMO, GRID = "TENANT#demo", "DELHI-28.61-77.21"


def get_health(tenant="demo"):
    resp = health.health_handler({"httpMethod": "GET", "queryStringParameters": {"tenant": tenant}}, None)
    return resp["statusCode"], json.loads(resp["body"])


@mock_aws
class TestResetAndSeed(unittest.TestCase):

    def setUp(self):
        self.table = make_table()
        os.environ["TABLE_NAME"] = "SaansStateTable"
        for tenant in (DEMO, "TENANT#other"):
            append_audit(self.table, tenant, "workflow", "OLD", {})
            self.table.put_item(Item={"PK": tenant, "SK": "DEC#2026-10-12#MORN", "status": "APPROVE_PLAN_B"})
            self.table.put_item(Item={"PK": f"TOKEN#{tenant[-4:]}", "SK": "META", "tenant_id": tenant})
            self.table.put_item(Item={"PK": f"RECEIPT#{tenant[-4:]}", "SK": "META", "tenant_id": tenant})
        self.table.put_item(Item={"PK": f"GRID#{GRID}#2026-10-12", "SK": "FCST"})

    def test_reset_clears_only_the_demo_school(self):
        removed = reset_tenant(self.table, DEMO, GRID)
        self.assertEqual(removed, {"tenant_items": 3, "tokens_and_receipts": 2, "forecast_cache": 1})  # AUD#000001, AUDHEAD, DEC
        left = {(i["PK"], i["SK"]) for i in self.table.scan()["Items"]}
        self.assertFalse(any(pk == DEMO for pk, _ in left))
        self.assertIn(("TENANT#other", "DEC#2026-10-12#MORN"), left)
        self.assertIn(("TOKEN#ther", "META"), left)

    def test_seed_starts_the_chain_at_one_with_the_stage_change(self):
        reset_tenant(self.table, DEMO, GRID)
        out = seed_scenario(self.table, "II", "III")
        self.assertEqual(out["first_audit_seq"], 1)
        self.assertRegex(out["run_label"], r"^r[0-9a-f]{8}$")
        row = read_chain(self.table, DEMO)[0]
        self.assertEqual((row["event"], row["payload"]["from_stage"], row["payload"]["to_stage"]), ("STAGE_DECLARED", "II", "III"))
        self.assertEqual(row["payload"]["basis"], "REPLAY SCENARIO")
        self.assertEqual(declared_stage(self.table, DEMO), "III")

    def test_seed_rejects_unknown_stage(self):
        with self.assertRaises(ValueError):
            seed_scenario(self.table, "II", "V")


@mock_aws
class TestTriggerUsesDeclaredStage(unittest.TestCase):

    def setUp(self):
        self.table = make_table()
        os.environ["TABLE_NAME"] = "SaansStateTable"
        sfn = boto3.client("stepfunctions")
        os.environ["STATE_MACHINE_ARN"] = sfn.create_state_machine(
            name="SaansWorkflow", definition=json.dumps({"StartAt": "A", "States": {"A": {"Type": "Succeed"}}}),
            roleArn="arn:aws:iam::123456789012:role/sfn")["stateMachineArn"]
        self.sfn = sfn

    def test_stage_comes_from_the_tenant_record(self):
        seed_scenario(self.table, "II", "IV")
        out = trigger_handler({"tenant_id": DEMO, "date": "2026-10-12"}, None)
        started = json.loads(self.sfn.describe_execution(executionArn=out["execution_arn"])["input"])
        self.assertEqual(started["stage"], "IV")

    def test_unseeded_tenant_fails_visibly(self):
        with self.assertRaisesRegex(ValueError, "No declared stage"):
            trigger_handler({"tenant_id": DEMO, "date": "2026-10-12"}, None)

    def test_explicit_stage_still_wins(self):
        seed_scenario(self.table, "II", "IV")
        out = trigger_handler({"tenant_id": DEMO, "date": "2026-10-12", "stage": "II"}, None)
        self.assertEqual(json.loads(self.sfn.describe_execution(executionArn=out["execution_arn"])["input"])["stage"], "II")


class FakeBedrock:
    def __init__(self, error=None):
        self.error, self.calls = error, 0

    def converse(self, **kw):
        self.calls += 1
        if self.error:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "ValidationException", "Message": self.error}}, "Converse")
        return {"output": {"message": {"content": [{"text": "o"}]}}}


@mock_aws
class TestHealth(unittest.TestCase):

    def setUp(self):
        self.table = make_table()
        os.environ["TABLE_NAME"] = "SaansStateTable"
        health._bedrock_cache.clear()
        self.bedrock = FakeBedrock()
        patches = [mock.patch.object(health, "_bedrock_client", lambda: self.bedrock),
                   mock.patch.object(ingest, "http_get_json", lambda url: {
                       "hourly": {"time": [t.replace("2026-10-12", url.split("start_date=")[1][:10]) for t in API_RESPONSE["hourly"]["time"]],
                                  "pm2_5": API_RESPONSE["hourly"]["pm2_5"]}})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_all_green(self):
        seed_scenario(self.table)
        code, body = get_health()
        self.assertEqual((code, body["status"]), (200, "ok"), body)
        c = body["checks"]
        self.assertEqual(c["declared_stage"]["stage"], "III")
        self.assertEqual(c["forecast"]["source"], "live")
        self.assertTrue(c["bedrock"]["usable"])
        self.assertEqual((c["audit"]["rows"], c["audit"]["head_seq"], c["audit"]["chain_valid"]), (1, 1, True))
        self.assertEqual(c["ruleset"]["version"], "2026-10-08-r1")
        self.assertEqual(len(c["ruleset"]["sha256"]), 64)

    def test_degraded_says_why(self):
        seed_scenario(self.table)
        self.bedrock.error = "Operation not allowed"
        with mock.patch.object(ingest, "http_get_json", side_effect=TimeoutError("timed out")):
            code, body = get_health()
        self.assertEqual((code, body["status"]), (200, "degraded"))
        self.assertEqual(body["checks"]["forecast"]["source"], "replay")
        self.assertIn("TimeoutError", body["checks"]["forecast"]["fallback_reason"])
        self.assertIn("Operation not allowed", body["checks"]["bedrock"]["error"])
        self.assertIn("static template", body["checks"]["bedrock"]["effect"])

    def test_bedrock_probe_is_cached(self):
        seed_scenario(self.table)
        get_health()
        _, body = get_health()
        self.assertEqual(self.bedrock.calls, 1)
        self.assertTrue(body["checks"]["bedrock"]["cached"])

    def test_tampered_chain_is_down(self):
        seed_scenario(self.table)
        append_audit(self.table, DEMO, "workflow", "X", {})
        self.table.update_item(Key={"PK": DEMO, "SK": "AUD#000001"}, UpdateExpression="SET actor_role = :v",
                               ExpressionAttributeValues={":v": "intruder"})
        code, body = get_health()
        self.assertEqual((code, body["status"], body["checks"]["audit"]["broken_seq"]), (503, "down", 1))

    def test_unseeded_is_degraded_with_instruction(self):
        code, body = get_health()
        self.assertEqual(body["status"], "degraded")
        self.assertIn("seed_demo.py", body["checks"]["declared_stage"]["note"])

    def test_table_unreachable_is_down_without_details(self):
        with mock.patch.object(health, "_table", side_effect=RuntimeError("internal host 10.0.0.1")):
            code, body = get_health()
        self.assertEqual((code, body["status"]), (503, "down"))
        self.assertNotIn("10.0.0.1", json.dumps(body))

    def test_bad_tenant(self):
        self.assertEqual(get_health("../x")[0], 400)


if __name__ == "__main__":
    unittest.main()
