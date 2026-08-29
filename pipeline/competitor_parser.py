from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.schema import Measurement

# ponytail: competitor exports (PDF/image floor plans) aren't structured
# data -- values are hand-transcribed into a small JSON first (see
# media/competitor_benchmark/<app>/measurements.json), and this module only
# parses/normalizes *that*. Re-deriving numbers from a rendered PDF
# automatically (OCR + layout inference) is a much harder, separate problem,
# out of scope here.

SQFT_TO_M2 = 0.09290304

_FEET_INCHES_RE = re.compile(r"""^\s*(\d+)'\s*(?:(\d+)(?:\s+(\d+)\s*/\s*(\d+))?\s*")?\s*$""")
_METERS_RE = re.compile(r"^\s*([\d.]+)\s*m\s*$", re.IGNORECASE)
_CM_RE = re.compile(r"^\s*([\d.]+)\s*cm\s*$", re.IGNORECASE)
_FT_PLAIN_RE = re.compile(r"^\s*([\d.]+)\s*ft\s*$", re.IGNORECASE)


def feet_inches_to_cm(value: str) -> float:
    """Parses a feet-and-inches string like `11' 9 1/2"` (fractional
    inches optional) into centimeters."""
    match = _FEET_INCHES_RE.match(value)
    if not match:
        raise ValueError(f"unrecognized feet-inches format: {value!r}")

    feet = int(match.group(1))
    whole_inches = int(match.group(2)) if match.group(2) else 0
    fraction = 0.0
    if match.group(3) and match.group(4):
        fraction = int(match.group(3)) / int(match.group(4))

    total_inches = feet * 12 + whole_inches + fraction
    return total_inches * 2.54


def parse_length_to_cm(value: str) -> float:
    """Normalizes a length string in feet-inches, meters, feet, or plain
    centimeters into centimeters -- one unit, regardless of source format."""
    text = value.strip()

    if "'" in text:
        return feet_inches_to_cm(text)

    if m := _METERS_RE.match(text):
        return float(m.group(1)) * 100

    if m := _CM_RE.match(text):
        return float(m.group(1))

    if m := _FT_PLAIN_RE.match(text):
        return float(m.group(1)) * 30.48

    raise ValueError(f"unrecognized length format: {value!r}")


def _point_measurement(value_cm: float, unit: str = "cm") -> Measurement:
    """A competitor export gives a single number, no stated uncertainty --
    represented as a zero-width interval rather than fabricating a CI."""
    return Measurement(value=round(value_cm, 2), confidence_interval=(value_cm, value_cm), unit=unit)


@dataclass
class CompetitorRoomMeasurements:
    room_id: str
    source_room_name: str
    width: Measurement
    length: Measurement
    ceiling_height: Measurement
    area_m2: Measurement
    perimeter: Measurement
    openings: list[Measurement] = field(default_factory=list)


def load_competitor_measurements(json_path: Path | str) -> dict[str, CompetitorRoomMeasurements]:
    data = json.loads(Path(json_path).read_text())

    results: dict[str, CompetitorRoomMeasurements] = {}
    for room_id, entry in data["rooms"].items():
        area_m2 = entry["area_sqft"] * SQFT_TO_M2
        results[room_id] = CompetitorRoomMeasurements(
            room_id=room_id,
            source_room_name=entry.get("source_room_name", room_id),
            width=_point_measurement(parse_length_to_cm(entry["width"])),
            length=_point_measurement(parse_length_to_cm(entry["length"])),
            ceiling_height=_point_measurement(parse_length_to_cm(entry["ceiling_height"])),
            area_m2=_point_measurement(area_m2, unit="m2"),
            perimeter=_point_measurement(parse_length_to_cm(entry["perimeter"])),
            openings=[_point_measurement(parse_length_to_cm(o)) for o in entry.get("openings", [])],
        )
    return results
