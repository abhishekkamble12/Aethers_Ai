"""
Deployment packaging test (hack_win.md M1).
Builds infra/.lambda_src exactly as `sam build` will see it, then imports every handler
declared in infra/template.yaml in a fresh interpreter whose sys.path holds only the
bundle, mirroring how Lambda loads code from /var/task.
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_lambda import build  # noqa: E402

TEMPLATE = ROOT / "infra" / "template.yaml"


def template_handlers():
    return re.findall(r"^\s+Handler:\s+(\S+)\s*$", TEMPLATE.read_text(encoding="utf-8"), re.M)


class TestLambdaBundle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bundle = build()

    def test_template_uses_bundle(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("CodeUri: .lambda_src/", text)
        self.assertNotIn("CodeUri: ../services", text)

    def test_bundle_contains_runtime_data(self):
        for rel in ["data/demo/timetable_sample.csv", "data/demo/forecast_stage3_sample.json",
                    "data/demo/ruleset_v1.json", "data/gold/circular_real_caqm.txt"]:
            self.assertTrue((self.bundle / rel).is_file(), rel)

    def test_every_template_handler_imports_from_bundle(self):
        handlers = template_handlers()
        self.assertGreaterEqual(len(handlers), 5)
        for handler in handlers:
            module, func = handler.rsplit(".", 1)
            code = (
                "import sys, importlib;"
                f"sys.path.insert(0, {str(self.bundle)!r});"
                f"m = importlib.import_module({module!r});"
                f"assert callable(getattr(m, {func!r}))"
            )
            # -I: ignore the repo on PYTHONPATH/cwd so only the bundle can satisfy imports
            proc = subprocess.run([sys.executable, "-I", "-c", code],
                                  cwd=str(self.bundle.parent), capture_output=True, text=True)
            with self.subTest(handler=handler):
                self.assertEqual(proc.returncode, 0, proc.stderr[-500:])


if __name__ == "__main__":
    unittest.main()
