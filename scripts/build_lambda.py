"""
Assemble the single Lambda source bundle used by every function in infra/template.yaml.

Lambda puts the CodeUri directory on sys.path, and our handlers import `services.<pkg>`
and read `data/demo` / `data/gold`, so the bundle must contain both at its root:

    infra/.lambda_src/
        services/...
        data/demo/...
        data/gold/...
        requirements.txt   (empty: boto3 ships with the Lambda Python runtime)

Usage:  python scripts/build_lambda.py
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "infra" / ".lambda_src"
SOURCES = ["services", "data/demo", "data/gold"]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


def build() -> Path:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for rel in SOURCES:
        src = ROOT / rel
        if not src.is_dir():
            sys.exit(f"build_lambda: missing source directory {src}")
        shutil.copytree(src, OUT / rel, ignore=IGNORE)

    (OUT / "requirements.txt").write_text(
        "# boto3/botocore are provided by the AWS Lambda Python runtime\n", encoding="utf-8"
    )
    return OUT


if __name__ == "__main__":
    out = build()
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"build_lambda: wrote {files} files to {out.relative_to(ROOT)}")
