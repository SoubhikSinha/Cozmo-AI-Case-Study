"""Shared room discovery for the benchmark and head-to-head scripts.

No room name is ever hardcoded in the scripts that import this: everything
is discovered from what's actually present under media/ground_truth/, so a
tester's own capture (with entirely different room names) drives these
scripts unchanged, the same way pipeline/run.py already does for a single
room via --room-dir.
"""
from __future__ import annotations

import json
from pathlib import Path


def all_ground_truth_rooms(repo_root: Path) -> list[tuple[str, dict]]:
    """Every room under media/ground_truth/, as (room_id, ground_truth dict) pairs."""
    return [
        (path.parent.name, json.loads(path.read_text()))
        for path in sorted((repo_root / "media/ground_truth").glob("*/ground_truth.json"))
    ]


def find_scoreable_room(repo_root: Path) -> tuple[str, dict]:
    """The first room with rectangular ground truth (a "floor_dimensions_cm"
    key) -- irregular rooms use a per-wall perimeter list instead and aren't
    comparable against the box-room reconstruction model without per-wall
    correspondence, which isn't built yet."""
    rooms = all_ground_truth_rooms(repo_root)
    for room_id, ground_truth in rooms:
        if "floor_dimensions_cm" in ground_truth:
            return room_id, ground_truth
    irregular = [room_id for room_id, _ in rooms]
    raise SystemExit(
        "No room with rectangular ground truth (floor_dimensions_cm) found under "
        f"media/ground_truth/. Irregular rooms present, not scoreable: {irregular}"
    )
