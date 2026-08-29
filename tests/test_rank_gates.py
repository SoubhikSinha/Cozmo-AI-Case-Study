import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from rank_gates import severity  # noqa: E402


def test_severity_zero_when_passed():
    assert severity({"gate_name": "ceiling_height", "passed": True, "actual_value": 5.0, "threshold": 1.5}) == 0.0


def test_severity_lower_is_better_gate():
    result = {"gate_name": "ceiling_height", "passed": False, "actual_value": 69.0, "threshold": 1.5}
    assert severity(result) == 46.0


def test_severity_higher_is_better_gate_total_failure():
    # opening_widths: 0% detected vs 85% required -- maximally severe
    result = {"gate_name": "opening_widths", "passed": False, "actual_value": 0.0, "threshold": 0.85}
    assert severity(result) == 1.0


def test_severity_higher_is_better_gate_partial_failure():
    # 50% detected vs 85% required -> (0.85-0.5)/0.85
    result = {"gate_name": "opening_widths", "passed": False, "actual_value": 0.5, "threshold": 0.85}
    assert severity(result) == (0.85 - 0.5) / 0.85


def test_ranking_orders_by_severity_descending():
    results = [
        {"gate_name": "a", "passed": False, "actual_value": 3.0, "threshold": 1.0},  # 3x
        {"gate_name": "b", "passed": False, "actual_value": 10.0, "threshold": 1.0},  # 10x
        {"gate_name": "c", "passed": True, "actual_value": 0.0, "threshold": 1.0},  # 0
    ]
    ranked = sorted(results, key=severity, reverse=True)
    assert [r["gate_name"] for r in ranked] == ["b", "a", "c"]
