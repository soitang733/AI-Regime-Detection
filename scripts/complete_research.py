"""Rebuild optional data/core, research, diagnostics and full verification with raw logs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download", action="store_true", help="Refresh core/external data before rebuilding"
    )
    parser.add_argument("--rebuild-core", action="store_true", help="Recreate the C1/C2/C3 baseline as well")
    args = parser.parse_args()
    os.chdir(ROOT)
    env = os.environ.copy()
    env.update(
        PYTHONIOENCODING="utf-8",
        PYTHONHASHSEED="0",
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    commands = []
    if args.download:
        commands += [
            (
                "core_download",
                [
                    "-c",
                    "from src.data.refresh import run; from src.utils.config import load_config; run(load_config())",
                ],
            ),
            ("external_download", ["-m", "src.data.refresh_extensions"]),
            ("coinmetrics_download", ["-m", "src.data.coinmetrics_collector"]),
        ]
    if args.download or args.rebuild_core:
        commands.append(
            (
                "core",
                [
                    "run_pipeline.py",
                    "--steps",
                    "clean",
                    "features",
                    "reports",
                    "extensions",
                    "models",
                    "backtest",
                ],
            )
        )
    commands += [
        ("rv_diagnostics", ["-m", "src.models.diagnostics"]),
        ("research", ["-m", "src.research.run"]),
        ("verification", ["scripts/verify_c2.py"]),
    ]
    metadata = ROOT / "outputs/metadata"
    metadata.mkdir(exist_ok=True, parents=True)
    destination = metadata / "project_completion.json"
    report = {"status": "running", "started_at_utc": datetime.now(timezone.utc).isoformat(), "steps": []}
    try:
        for name, arguments in commands:
            print(f"Project: {name}", flush=True)
            log = metadata / f"project_{name}.log"
            with log.open("w", encoding="utf-8") as handle:
                process = subprocess.run(
                    [sys.executable, *arguments],
                    cwd=ROOT,
                    env=env,
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
            report["steps"].append(
                {
                    "step": name,
                    "arguments": arguments,
                    "exit_code": process.returncode,
                    "log": str(log.relative_to(ROOT)),
                }
            )
            destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
            if process.returncode:
                print(log.read_text(encoding="utf-8"), flush=True)
                raise RuntimeError(f"{name} failed; see {log.name}")
        report["status"] = "passed"
        report["source_warnings"] = []
        for name in ("external_refresh_manifest.json", "coinmetrics_refresh.json"):
            path = metadata / name
            if path.exists():
                acquisition = json.loads(path.read_text(encoding="utf-8"))
                if acquisition.get("status") != "complete":
                    report["source_warnings"].append({"manifest": name, "status": acquisition.get("status")})
        report["verification"] = json.loads((metadata / "C2_verification.json").read_text(encoding="utf-8"))[
            "pytest"
        ]
    except Exception as exc:
        report["status"], report["error"] = "failed", str(exc)
        raise
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "tests": report.get("verification")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
