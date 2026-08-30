"""Reproduction bundle entrypoint: regenerates every reported number in
docs/ from the raw captures in media/, live -- no cached model outputs to
go stale, because nothing in this pipeline calls an external model (see
CLAUDE.md / docs/technical_report.md for why: heuristic CV only, no VLM
wired in yet). Running this script end to end is the reproduction check.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STEPS = [
    ("Benchmark gates + timing", ["scripts/run_benchmark.py"]),
    ("Device matrix (from the benchmark run above)", ["scripts/generate_device_matrix.py"]),
    ("Head-to-head vs. magicplan", ["scripts/run_head_to_head.py"]),
]


def main() -> None:
    for label, args in STEPS:
        print(f"\n=== {label} ===")
        result = subprocess.run([sys.executable] + args, cwd=REPO_ROOT)
        if result.returncode != 0:
            raise SystemExit(f"FAILED: {label} (exit {result.returncode})")

    print("\n=== Regenerated files ===")
    for path in [
        "docs/benchmark_report.md",
        "docs/benchmark_results.json",
        "docs/timing.md",
        "docs/device_matrix.md",
        "docs/head_to_head_table.md",
        "docs/head_to_head_table.csv",
        "docs/head_to_head_report.md",
    ]:
        exists = "OK" if (REPO_ROOT / path).exists() else "MISSING"
        print(f"  [{exists}] {path}")

    print("\nAll reported numbers regenerated live from media/ + media/ground_truth/.")
    print("Run `pytest tests/ -q` separately to confirm the 77 unit/integration tests.")


if __name__ == "__main__":
    main()
