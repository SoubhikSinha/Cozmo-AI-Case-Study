import json

import pytest

from pipeline.competitor_parser import (
    feet_inches_to_cm,
    load_competitor_measurements,
    parse_length_to_cm,
)


def test_feet_inches_whole_number():
    assert feet_inches_to_cm("11' 7\"") == pytest.approx(11 * 30.48 + 7 * 2.54, abs=0.01)


def test_feet_inches_with_fraction():
    # 9' 1 1/4" = 109.25 inches = 277.495 cm
    assert feet_inches_to_cm("9' 1 1/4\"") == pytest.approx(277.495, abs=0.01)


def test_feet_inches_feet_only_no_inches():
    assert feet_inches_to_cm("11'") == pytest.approx(11 * 30.48, abs=0.01)


def test_invalid_feet_inches_format_raises():
    with pytest.raises(ValueError):
        feet_inches_to_cm("not a measurement")


def test_parse_length_normalizes_meters_and_feet_to_same_unit():
    # 3.5m and 11'6" are both ~350cm -- confirms unit normalization works
    # across formats, not just within feet-inches.
    meters_cm = parse_length_to_cm("3.5 m")
    feet_cm = parse_length_to_cm("11' 5 13/16\"")  # ~3.499m
    assert meters_cm == pytest.approx(350.0, abs=0.01)
    assert feet_cm == pytest.approx(meters_cm, abs=1.0)


def test_parse_length_plain_centimeters():
    assert parse_length_to_cm("272 cm") == pytest.approx(272.0)


def test_parse_length_plain_feet():
    assert parse_length_to_cm("10 ft") == pytest.approx(304.8, abs=0.01)


def test_load_competitor_measurements_from_sample_json(tmp_path):
    sample = {
        "rooms": {
            "bedroom_1": {
                "source_room_name": "Bedroom",
                "width": "11' 9 1/2\"",
                "length": "11' 7\"",
                "ceiling_height": "9' 1 1/4\"",
                "area_sqft": 136.59,
                "perimeter": "46' 9\"",
                "openings": ["2' 6\""],
            }
        }
    }
    json_path = tmp_path / "measurements.json"
    json_path.write_text(json.dumps(sample))

    results = load_competitor_measurements(json_path)

    assert set(results.keys()) == {"bedroom_1"}
    room = results["bedroom_1"]
    assert room.source_room_name == "Bedroom"
    assert room.width.value == pytest.approx(359.41, abs=0.1)
    assert room.length.value == pytest.approx(353.06, abs=0.1)
    assert room.width.unit == "cm"
    assert room.area_m2.unit == "m2"
    assert room.area_m2.value == pytest.approx(136.59 * 0.09290304, abs=0.01)
    assert len(room.openings) == 1
    assert room.openings[0].value == pytest.approx(76.2, abs=0.1)
    # competitor gives a point value, not a range -- represented as zero-width CI
    assert room.width.confidence_interval == (room.width.value, room.width.value)


def test_real_magicplan_export_measurements_load():
    from pathlib import Path

    json_path = Path(__file__).resolve().parent.parent / "media/competitor_benchmark/magicplan/measurements.json"
    results = load_competitor_measurements(json_path)

    assert set(results.keys()) == {"bedroom_1", "common-space"}
    assert results["bedroom_1"].ceiling_height.value == pytest.approx(277.495, abs=0.1)
    assert results["common-space"].width.value == pytest.approx(351.79, abs=0.1)
