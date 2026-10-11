"""
S3 Object Lock Anchor Tests
Validates immutable anchoring of audit chains in S3 Object Lock (COMPLIANCE mode),
refusal of tampered/rewritten chains, receipt integration, and browser verification under Node.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

from services.audit import anchor as anchor_mod  # noqa: E402
from services.audit.handler import receipt_handler, verify_page_handler  # noqa: E402
from services.audit.hash_chain import (  # noqa: E402
    canonical_json,
    compute_payload_digest,
    compute_row_hash,
    hash_body,
)
from services.audit.store import append_audit, read_chain  # noqa: E402
from tests.test_audit_store import make_table  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
TENANT = "TENANT#demo"
RID = "testreceipt1"
BUCKET = "saans-test-anchors"


def rewrite_chain(table, tenant_id: str, at_seq: int, new_actor: str):
    rows = read_chain(table, tenant_id)
    for i in range(at_seq - 1, len(rows)):
        r = rows[i]
        if r["seq"] == at_seq:
            r["actor_role"] = new_actor
        prev_hash = rows[i - 1]["hash"] if i > 0 else "0" * 64
        r["prev_hash"] = prev_hash
        r["hash"] = compute_row_hash(prev_hash, hash_body(r["seq"], r["actor_role"], r["event"],
                                                          r["payload_digest"], r["ts"]))
        item = {
            "PK": tenant_id,
            "SK": f"AUD#{r['seq']:06d}",
            "seq": r["seq"],
            "prev_hash": r["prev_hash"],
            "hash": r["hash"],
            "actor_role": r["actor_role"],
            "event": r["event"],
            "payload_digest": r["payload_digest"],
            "ts": r["ts"],
            "payload": canonical_json(r["payload"]),
        }
        table.put_item(Item=item)
    table.put_item(Item={"PK": tenant_id, "SK": "AUDHEAD", "seq": rows[-1]["seq"], "hash": rows[-1]["hash"]})


@mock_aws
class TestAnchor(unittest.TestCase):

    def setUp(self):
        os.environ["TABLE_NAME"] = "SaansStateTable"
        os.environ["ANCHOR_BUCKET"] = BUCKET
        self.table = make_table()
        self.s3 = boto3.client("s3", region_name="ap-south-1")
        self.s3.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
            ObjectLockEnabledForBucket=True,
        )
        self.s3.put_object_lock_configuration(
            Bucket=BUCKET,
            ObjectLockConfiguration={
                "ObjectLockEnabled": "Enabled",
                "Rule": {"DefaultRetention": {"Mode": "COMPLIANCE", "Days": 365}},
            },
        )
        # Seed 3 audit rows for the tenant
        for event in ("PLAN_GENERATED", "APPROVAL_REQUESTED", "APPROVAL_RECEIVED"):
            append_audit(self.table, TENANT, "principal" if event == "APPROVAL_RECEIVED" else "workflow",
                         event, {"decision_id": "TENANT#demo#2026-10-12#MORN"})
        self.table.put_item(Item={"PK": f"RECEIPT#{RID}", "SK": "META", "tenant_id": TENANT,
                                  "decision_id": "TENANT#demo#2026-10-12#MORN"})
        self.table.put_item(Item={"PK": TENANT, "SK": "DEC#2026-10-12#MORN", "status": "APPROVED"})

    def anchor(self):
        return anchor_mod.anchor_tenant(self.table, self.s3, BUCKET, TENANT)

    def receipt(self):
        resp = receipt_handler({"httpMethod": "GET", "pathParameters": {"id": RID}}, None)
        self.assertEqual(resp["statusCode"], 200, resp["body"])
        return json.loads(resp["body"])

    def test_new_chain_ignores_old_chain_anchors(self):
        old_chain = self.anchor()["chain"]
        # Wipe the tenant's chain to start a new one
        for item in self.table.query(KeyConditionExpression="PK = :pk", ExpressionAttributeValues={":pk": TENANT})["Items"]:
            self.table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
        self.table.put_item(Item={"PK": f"RECEIPT#{RID}", "SK": "META", "tenant_id": TENANT,
                                  "decision_id": "TENANT#demo#2026-10-12#MORN"})
        append_audit(self.table, TENANT, "admin:seed", "STAGE_DECLARED", {"to_stage": "III"})
        # The locked anchors of the old chain do not break the new one...
        self.assertTrue(self.anchor()["anchored"])
        body = self.receipt()
        self.assertTrue(body["serverVerification"]["valid"])
        self.assertEqual([a["seq"] for a in body["anchor"]["anchors"]], [1])
        # ...and the receipt says another chain was anchored for this school.
        self.assertEqual([(o["chain"], o["lastSeq"]) for o in body["anchor"]["otherChains"]], [(old_chain, 3)])

    def test_empty_chain_is_not_anchored(self):
        self.assertEqual(anchor_mod.anchor_handler({"tenant_ids": ["TENANT#other"]}, None)["results"][0]["reason"],
                         "empty_chain")

    def test_broken_chain_is_refused(self):
        self.table.update_item(Key={"PK": TENANT, "SK": "AUD#000002"}, UpdateExpression="SET actor_role = :v",
                               ExpressionAttributeValues={":v": "vice_principal"})
        with self.assertRaises(anchor_mod.ChainNotAnchorable):
            self.anchor()
        self.assertEqual(anchor_mod.list_anchors(self.s3, BUCKET, TENANT), [])

    def test_rewritten_chain_is_refused_and_receipt_turns_red(self):
        self.anchor()
        rewrite_chain(self.table, TENANT, 2, "vice_principal")
        # Every hash recomputes, so the chain alone looks valid...
        rows = read_chain(self.table, TENANT)
        self.assertTrue(all(compute_payload_digest(r["payload"]) == r["payload_digest"] for r in rows))
        # ...but the anchor refuses to launder it, and the receipt reports the mismatch.
        with self.assertRaises(anchor_mod.ChainNotAnchorable):
            self.anchor()
        verdict = self.receipt()["serverVerification"]
        self.assertFalse(verdict["valid"])
        self.assertEqual((verdict["brokenSequence"], verdict["anchorMismatchSequence"]), (3, 3))
        self.assertIn("S3 anchor", verdict["message"])

    def test_receipt_shows_anchor_and_lock(self):
        self.assertEqual(self.receipt()["anchor"]["anchors"], [])  # deployed, nothing anchored yet
        self.assertEqual(self.receipt()["anchor"]["otherChains"], [])
        self.anchor()
        body = self.receipt()
        a = body["anchor"]
        self.assertEqual([x["seq"] for x in a["anchors"]], [3])
        self.assertEqual(a["anchors"][0]["hash"], body["blocks"][2]["hash"])
        self.assertEqual(a["latest"]["lockMode"], "COMPLIANCE")
        self.assertTrue(a["latest"]["retainUntil"])
        self.assertTrue(body["serverVerification"]["valid"])
        self.assertIsNone(body["serverVerification"]["anchorMismatchSequence"])

    def test_receipt_without_anchoring_deployed(self):
        os.environ.pop("ANCHOR_BUCKET")
        body = self.receipt()
        self.assertIsNone(body["anchor"])
        self.assertTrue(body["serverVerification"]["valid"])

    # --- the browser code, run under Node --------------------------------------------------
    @unittest.skipUnless(NODE, "node not installed")
    def test_frontend_verifier_catches_rewrite_against_anchor(self):
        self.anchor()
        clean = self.receipt()
        rewrite_chain(self.table, TENANT, 2, "vice_principal")
        rewritten = self.receipt()
        with tempfile.TemporaryDirectory() as tmp:
            src = (ROOT / "lib/crypto.ts").read_text(encoding="utf-8")
            src = re.sub(r"^import .*?;\s*$", "", src, flags=re.M)
            Path(tmp, "crypto.ts").write_text(src, encoding="utf-8")
            Path(tmp, "r.json").write_text(json.dumps([clean, rewritten]), encoding="utf-8")
            Path(tmp, "run.ts").write_text("""
import { readFileSync } from 'node:fs';
import { verifyChain } from './crypto.ts';
const [clean, rewritten] = JSON.parse(readFileSync(new URL('./r.json', import.meta.url), 'utf8'));
const a = await verifyChain(clean.blocks, clean.genesisHash, clean.anchor?.anchors);
const plain = await verifyChain(rewritten.blocks, rewritten.genesisHash);
const b = await verifyChain(rewritten.blocks, rewritten.genesisHash, rewritten.anchor?.anchors);
console.log(JSON.stringify({ clean: a.firstBad, plain: plain.firstBad, anchored: b.firstBad, why: b.problems[2] }));
""", encoding="utf-8")
            out = subprocess.run([NODE, "--experimental-strip-types", "--no-warnings", "run.ts"], cwd=tmp,
                                 capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        result = json.loads(out.stdout)
        self.assertEqual((result["clean"], result["plain"], result["anchored"]), (None, None, 3))
        self.assertTrue(any("S3 anchor" in p for p in result["why"]), result)

    @unittest.skipUnless(NODE, "node not installed")
    def test_verify_page_catches_rewrite_against_anchor(self):
        self.anchor()
        rewrite_chain(self.table, TENANT, 2, "vice_principal")
        receipt = self.receipt()
        page = verify_page_handler({"httpMethod": "GET", "pathParameters": {"id": RID}}, None)["body"]
        script = re.search(r"<script>(.*)</script>", page, re.S).group(1)
        harness = """
const els = {};
function el() { return { className:'', textContent:'', hidden:false, classList:{ add(){} }, children:[],
  append(...c){ this.children.push(...c); }, replaceChildren(){ this.children=[]; },
  addEventListener(t,f){ this.onclick=f; } }; }
globalThis.document = { getElementById(id){ return els[id] ||= el(); }, createElement(){ return el(); } };
globalThis.location = { pathname: '/Prod/verify/RID' };
globalThis.window = globalThis;
const receipt = JSON.parse(process.env.RECEIPT);
globalThis.fetch = async (url) => ({ ok: true, json: async () => receipt });
(async () => {
  %SCRIPT%
  await new Promise(r => setTimeout(r, 500));
  console.log(JSON.stringify({ verdict: els.verdict.textContent, anchor: els.anchor.textContent }));
})();
""".replace("%SCRIPT%", script)
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "page.mjs").write_text(harness, encoding="utf-8")
            out = subprocess.run([NODE, "page.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8",
                                 timeout=60, env={**os.environ, "RECEIPT": json.dumps(receipt)})
        self.assertEqual(out.returncode, 0, out.stderr)
        result = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertTrue(result["verdict"].startswith("✕ Broken at record #3"), result)
        self.assertIn("S3", result["anchor"])


class TestAnchorTemplate(unittest.TestCase):

    def test_bucket_is_compliance_locked_and_private(self):
        tpl = (ROOT / "infra/template.yaml").read_text(encoding="utf-8")
        bucket = tpl.split("  AnchorBucket:\n", 1)[1].split("\n\n", 1)[0]
        for needle in ("ObjectLockEnabled: true", "Mode: COMPLIANCE", "DeletionPolicy: Retain",
                       "BlockPublicPolicy: true", "Status: Enabled"):
            self.assertIn(needle, bucket)
        self.assertIn("Handler: services.audit.anchor.anchor_handler", tpl)
        self.assertIn("Tracing: Active", tpl)


if __name__ == "__main__":
    unittest.main()
