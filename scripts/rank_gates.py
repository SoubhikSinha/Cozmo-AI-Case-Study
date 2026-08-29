"""Part 4, Step 1: ranks every real gate result by how badly it fails.
Report only -- ships no fix. Reads docs/benchmark_results.json, the real
output of scripts/run_benchmark.py, never hand-typed numbers.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = REPO_ROOT / "docs" / "benchmark_results.json"

# opening_widths is the only gate where a HIGHER actual_value is better
# (it's a pass-fraction, >=0.85 required); every other gate's actual_value
# is an error/ratio where lower is better (<=threshold required).
HIGHER_IS_BETTER = {"opening_widths"}

VACUOUS_MARKER = "[CAVEAT"


def severity(result: dict) -> float:
    """0 = fully passing. For a failed gate, how many multiples past the
    threshold boundary the actual value is -- the ranking key."""
    if result["passed"]:
        return 0.0
    actual, threshold = result["actual_value"], result["threshold"]
    if threshold == 0:
        return float("inf")
    if result["gate_name"] in HIGHER_IS_BETTER:
        return (threshold - actual) / threshold
    return actual / threshold


def main() -> None:
    if not RESULTS_PATH.exists():
        raise SystemExit(f"{RESULTS_PATH} not found -- run scripts/run_benchmark.py first")

    results = json.loads(RESULTS_PATH.read_text())
    ranked = sorted(results, key=severity, reverse=True)

    print(f"{'Gate':<26} {'Tier':<7} {'Status':<6} {'Actual':>10} {'Threshold':>10} {'Severity':>9}  Note")
    print("-" * 100)
    for r in ranked:
        sev = severity(r)
        vacuous = VACUOUS_MARKER in r["detail"]
        status = "PASS" if r["passed"] else "FAIL"
        note = "(vacuous -- photo tier's fixed-default value, not a real measurement)" if vacuous else ""
        print(
            f"{r['gate_name']:<26} {r['tier']:<7} {status:<6} {r['actual_value']:>10.4f} "
            f"{r['threshold']:>10.4f} {sev:>8.2f}x  {note}"
        )

    failing = [r for r in ranked if not r["passed"]]
    if not failing:
        print("\nNo failing gates.")
        return

    worst = failing[0]
    print("\n=== WORST GATE ===")
    print(f"gate_name : {worst['gate_name']}")
    print(f"tier/room : {worst['tier']} / {worst['room_id']}")
    print(f"actual    : {worst['actual_value']}")
    print(f"threshold : {worst['threshold']}")
    print(f"severity  : {severity(worst):.2f}x past the gate boundary")
    print(f"detail    : {worst['detail']}")


if __name__ == "__main__":
    main()
