"""
hack_win M3b: public receipts served from the real chain, and cross-language verification:
the frontend's lib/crypto.ts and the backend-served verify page's own <script> logic are run
under Node against a chain written by the backend.
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

from moto import mock_aws  # noqa: E402

from services.audit.handler import receipt_handler, verify_page_handler  # noqa: E402
import tests.test_audit_wiring as wiring  # noqa: E402  (module import: avoid re-discovering its tests)

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")


def get(handler, rid):
    resp = handler({"httpMethod": "GET", "pathParameters": {"id": rid}}, None)
    return resp["statusCode"], resp


@mock_aws
class TestReceipts(wiring.TestAuditWiring):
    """Reuses TestAuditWiring's setUp/run_workflow; its own tests are not re-run here."""

    def setUp(self):
        super().setUp()
        self.run_workflow("APPROVE_PLAN_B")
        self.receipt_id = self.table.get_item(Key={"PK": "TENANT#demo", "SK": "DEC#2026-10-12#MORN"})["Item"]["receipt_id"]

    def receipt(self):
        status, resp = get(receipt_handler, self.receipt_id)
        self.assertEqual(status, 200, resp["body"])
        return json.loads(resp["body"])

    def test_receipt_serves_real_chain_and_server_verdict(self):
        body = self.receipt()
        self.assertRegex(self.receipt_id, r"^[A-Za-z0-9_-]{12}$")
        self.assertEqual(body["decisionId"], "TENANT#demo#2026-10-12#MORN")
        self.assertEqual(body["decisionStatus"], "APPROVED_AND_NOTIFIED")  # closed by the terminal audit step
        self.assertEqual([b["eventType"] for b in body["blocks"]],
                         ["PLAN_GENERATED", "APPROVAL_REQUESTED", "APPROVAL_RECEIVED", "NOTICES_DRAFTED",
                          "RUN_CLOSED_APPROVED_AND_NOTIFIED"])
        self.assertEqual(body["decisionSequences"], [1, 2, 3, 4, 5])
        self.assertEqual(body["auditHead"], body["blocks"][-1]["hash"])
        self.assertTrue(body["serverVerification"]["valid"])
        self.assertEqual(json.loads(body["blocks"][0]["payloadJson"])["receipt_id"], self.receipt_id)

    def test_receipt_contains_no_credentials(self):
        raw = get(receipt_handler, self.receipt_id)[1]["body"]
        for item in self.table.scan()["Items"]:
            if item["PK"].startswith("TOKEN#"):
                self.assertNotIn(item["PK"].split("#", 1)[1], raw)
        self.assertNotIn("TASK-TOKEN", raw)
        self.assertNotIn("approve_url", raw)

    def test_bad_and_unknown_ids(self):
        self.assertEqual(get(receipt_handler, "../../etc")[0], 400)
        self.assertEqual(get(receipt_handler, "AAAAAAAAAAAA")[0], 404)
        self.assertEqual(get(verify_page_handler, "<script>")[0], 400)

    def test_server_reports_tampered_row(self):
        self.table.update_item(Key={"PK": "TENANT#demo", "SK": "AUD#000003"}, UpdateExpression="SET actor_role = :v",
                               ExpressionAttributeValues={":v": "vice_principal"})
        verdict = self.receipt()["serverVerification"]
        self.assertFalse(verdict["valid"])
        self.assertEqual(verdict["brokenSequence"], 3)

    def test_verify_page_is_served_with_strict_csp(self):
        status, resp = get(verify_page_handler, self.receipt_id)
        self.assertEqual(status, 200)
        self.assertIn("text/html", resp["headers"]["Content-Type"])
        self.assertIn("connect-src 'self'", resp["headers"]["Content-Security-Policy"])
        self.assertIn('fetch("../receipts/"', resp["body"])

    # --- the browser code itself, run under Node ----------------------------------------
    @unittest.skipUnless(NODE, "node not installed")
    def test_frontend_lib_crypto_verifies_backend_chain(self):
        """lib/crypto.ts verifyAuditChain (unchanged) accepts the real chain and flags an edited row."""
        blocks = self.receipt()["blocks"]
        with tempfile.TemporaryDirectory() as tmp:
            src = (ROOT / "lib/crypto.ts").read_text(encoding="utf-8")
            src = re.sub(r"^import .*?;\s*$", "", src, flags=re.M)  # drop type-only import of '@/types/...'
            Path(tmp, "crypto.ts").write_text(src, encoding="utf-8")
            Path(tmp, "blocks.json").write_text(json.dumps(blocks), encoding="utf-8")
            Path(tmp, "run.ts").write_text("""
import { readFileSync } from 'node:fs';
import { verifyAuditChain } from './crypto.ts';
const blocks = JSON.parse(readFileSync(new URL('./blocks.json', import.meta.url), 'utf8'));
const clean = await verifyAuditChain(blocks);
blocks[2].actor = 'vice_principal';
const tampered = await verifyAuditChain(blocks);
console.log(JSON.stringify({ clean: clean.isValid, tampered: tampered.isValid, at: tampered.tamperIndex }));
""", encoding="utf-8")
            out = subprocess.run([NODE, "--experimental-strip-types", "--no-warnings", "run.ts"], cwd=tmp,
                                 capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), {"clean": True, "tampered": False, "at": 2})

    @unittest.skipUnless(NODE, "node not installed")
    def test_verify_page_script_verifies_backend_chain(self):
        """The verify page's own <script>, executed in Node with a stubbed DOM and fetch."""
        receipt = self.receipt()
        page = get(verify_page_handler, self.receipt_id)[1]["body"]
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
const settle = () => new Promise(r => setTimeout(r, 200));
(async () => {
  %SCRIPT%
  await settle(); const clean = els.verdict.textContent;
  await els.tamper.onclick(); await settle(); const tampered = els.verdict.textContent;
  console.log(JSON.stringify({ clean, tampered }));
})();
""".replace("%SCRIPT%", script)
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "page.mjs").write_text(harness, encoding="utf-8")
            out = subprocess.run([NODE, "page.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", timeout=60,
                                 env={**os.environ, "RECEIPT": json.dumps(receipt)})
        self.assertEqual(out.returncode, 0, out.stderr)
        result = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertTrue(result["clean"].startswith("✓ Valid: all 5 records"), result)
        self.assertTrue(result["tampered"].startswith("✕ Broken at record #3"), result)


# Don't re-run the inherited wiring tests under this class.
for _name in [n for n in dir(wiring.TestAuditWiring) if n.startswith("test_")]:
    setattr(TestReceipts, _name, None)


if __name__ == "__main__":
    unittest.main()
