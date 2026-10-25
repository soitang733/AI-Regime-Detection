"""One local command: optional append-only download -> C1 -> C2 -> C3 -> verification."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Append new closed UTC candles from Binance")
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ.update(
        PYTHONIOENCODING="utf-8", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1"
    )
    if args.download:
        from src.data.refresh import run
        from src.utils.config import load_config

        run(load_config())
    for arguments in (
        ["run_pipeline.py", "--steps", "clean", "features", "reports", "extensions"],
        ["scripts/complete_c2.py"],
    ):
        result = subprocess.run([sys.executable, *arguments], cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
