"""
One-command demo reset + scenario seed against the deployed stack.

    python scripts/seed_demo.py                  # Stage II -> III scenario (default)
    python scripts/seed_demo.py --to-stage IV    # another declared stage

Clears ONLY the demo school's data (decisions, audit chain, approval tokens, receipts, forecast cache), records
the stage change as audit row #1, prints /health and the next demo commands. Uses the named AWS CLI profile
(env AWS_PROFILE, default "Abhi") and region us-east-1; no keys are read from files.
"""

import argparse
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import boto3  # noqa: E402

from services.admin.seed import reset_tenant, seed_scenario  # noqa: E402
from services.forecast.ingest import load_school  # noqa: E402

STACK, REGION = "saans", "us-east-1"


def stack_outputs(session):
    cf = session.client("cloudformation", region_name=REGION)
    outs = cf.describe_stacks(StackName=STACK)["Stacks"][0]["Outputs"]
    return {o["OutputKey"]: o["OutputValue"] for o in outs}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-stage", default="II")
    ap.add_argument("--to-stage", default="III")
    ap.add_argument("--profile", default=os.environ.get("AWS_PROFILE", "Abhi"))
    args = ap.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    outputs = stack_outputs(session)
    table = session.resource("dynamodb").Table(outputs["SaansTableArn"].rsplit("/", 1)[1])
    school = load_school()

    removed = reset_tenant(table, school["tenant_id"], school["grid_cell"])
    print(f"reset  {school['tenant_id']}: removed {removed}")
    seeded = seed_scenario(table, args.from_stage, args.to_stage)
    print(f"seeded declared stage {seeded['previous_stage']} -> {seeded['declared_stage']} "
          f"(REPLAY SCENARIO) as audit row #{seeded['first_audit_seq']}")

    api = outputs["ApiUrl"].rstrip("/")
    try:
        with urllib.request.urlopen(f"{api}/health?tenant=demo", timeout=30) as resp:
            health = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # report, do not fail the reset
        health = {"status": f"unreachable ({type(e).__name__})", "checks": {}}
    c = health.get("checks", {})
    print(f"health {health.get('status')}: stage={c.get('declared_stage', {}).get('stage')} "
          f"forecast={c.get('forecast', {}).get('source')} bedrock_usable={c.get('bedrock', {}).get('usable')} "
          f"audit_rows={c.get('audit', {}).get('rows')} chain_valid={c.get('audit', {}).get('chain_valid')}")

    payload = json.dumps({"tenant_id": school["tenant_id"], "date": "<YYYY-MM-DD school day>",
                          "forecast_source": "replay", "rerun_label": seeded["run_label"]})
    print("\nnext: start a bad-air replay run (stage comes from the record):")
    print(f"  aws lambda invoke --no-cli-pager --profile {args.profile} --region {REGION} "
          f"--function-name {outputs['TriggerFunctionName']} --cli-binary-format raw-in-base64-out "
          f"--payload '{payload}' out.json")


if __name__ == "__main__":
    main()
