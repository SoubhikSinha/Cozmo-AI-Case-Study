"""Builds the real Part 3 head-to-head comparison: our LiDAR-tier output vs.
magicplan vs. ground truth, on bedroom_1 and common-space.

Shared dimensions only: a dimension is compared only when both our output
and the competitor's parsed export have a value for it. Only bedroom_1
qualifies -- common-space's ground truth is an irregular room (see
media/ground_truth/common-space/ground_truth.json) with no single L x B /
single-ceiling-height representation to compare magicplan's box-shaped
measurement against, so it's excluded here rather than force-matched.
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.adapters.lidar_adapter import LidarAdapter
from pipeline.competitor_parser import load_competitor_measurements
from pipeline.head_to_head import build_report
from pipeline.room_reconstruction import reconstruct_room

REPO_ROOT = Path(__file__).resolve().parent.parent


def _sorted_walls_cm(room) -> list[float]:
    return sorted(w.length.value for w in room.walls)


def main() -> None:
    ground_truth = json.loads((REPO_ROOT / "media/ground_truth/bedroom_1/ground_truth.json").read_text())
    competitor = load_competitor_measurements(REPO_ROOT / "media/competitor_benchmark/magicplan/measurements.json")

    lidar_dir = next((REPO_ROOT / "media/lidar/bedroom_1").iterdir())
    lidar_capture = LidarAdapter().load(lidar_dir, room_id="bedroom_1")
    our_room = reconstruct_room(lidar_capture, room_id="bedroom_1", name="bedroom_1", device="iPhone17,1")

    gt_length = ground_truth["floor_dimensions_cm"]["length"]
    gt_breadth = ground_truth["floor_dimensions_cm"]["breadth"]
    gt_ceiling = ground_truth["ceiling_height_cm"]

    our_walls_sorted = _sorted_walls_cm(our_room)  # [short, short, long, long]
    our_breadth, our_length = our_walls_sorted[0], our_walls_sorted[-1]

    their = competitor["bedroom_1"]
    their_length, their_breadth = their.length.value, their.width.value

    dimensions = [
        ("bedroom_1_length", gt_length, our_length, their_length),
        ("bedroom_1_breadth", gt_breadth, our_breadth, their_breadth),
        ("bedroom_1_ceiling_height", gt_ceiling, our_room.ceiling_height.value, their.ceiling_height.value),
    ]

    report = build_report(dimensions)

    print(report.to_markdown())

    csv_path = REPO_ROOT / "docs" / "head_to_head_table.csv"
    csv_path.write_text(report.to_csv())

    md_path = REPO_ROOT / "docs" / "head_to_head_table.md"
    md_path.write_text(
        "# Head-to-Head: Our Pipeline vs. magicplan (2026.34.1)\n\n"
        "LiDAR tier, bedroom_1 (the only benchmark room with ground truth in a shape "
        "comparable to both our box-room reconstruction and magicplan's box-room output -- "
        "see docs/head_to_head.md for why common-space is excluded).\n\n"
        + report.to_markdown()
        + "\n"
    )

    print(f"\nWritten to {csv_path}")
    print(f"Written to {md_path}")


if __name__ == "__main__":
    main()
