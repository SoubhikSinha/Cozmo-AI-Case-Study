"""Runs the Part 2 gates against the real benchmark set in media/ +
media/ground_truth/, using bedroom_1 (the only room with clean rectangular
ground truth -- the others are irregular rooms, see the caveats section
this script prints, and docs/benchmark_report.md).
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.adapters.lidar_adapter import LidarAdapter
from pipeline.adapters.photo_adapter import PhotoAdapter
from pipeline.adapters.video_adapter import VideoAdapter
from pipeline.benchmark import (
    BenchmarkReport,
    match_openings_by_nearest_width,
    score_ceiling_height,
    score_ceiling_repeatability,
    score_footprint_tolerance,
    score_opening_widths,
    score_repeatability_walls,
    score_video_tier_walls,
)
from pipeline.room_reconstruction import reconstruct_room

REPO_ROOT = Path(__file__).resolve().parent.parent
GROUND_TRUTH = json.loads((REPO_ROOT / "media/ground_truth/bedroom_1/ground_truth.json").read_text())


def _sorted_walls_cm(room) -> list[float]:
    return sorted(w.length.value for w in room.walls)


def main() -> None:
    lidar_dir = next((REPO_ROOT / "media/lidar/bedroom_1").iterdir())
    lidar_capture = LidarAdapter().load(lidar_dir, room_id="bedroom_1")
    lidar_room = reconstruct_room(lidar_capture, room_id="bedroom_1", name="bedroom_1", device="iPhone17,1")

    photo_capture = PhotoAdapter().load(REPO_ROOT / "media/photos/bedroom_1", room_id="bedroom_1")
    photo_room = reconstruct_room(photo_capture, room_id="bedroom_1", name="bedroom_1", device="iPhone17,1")

    photo_recapture = PhotoAdapter().load(REPO_ROOT / "media/photos/bedroom_1_recapture", room_id="bedroom_1")
    photo_recapture_room = reconstruct_room(photo_recapture, room_id="bedroom_1", name="bedroom_1", device="iPhone17,1")

    video_capture = VideoAdapter().load(
        next((REPO_ROOT / "media/video/bedroom_1").glob("*.MOV")), room_id="bedroom_1"
    )
    video_room = reconstruct_room(video_capture, room_id="bedroom_1", name="bedroom_1", device="iPhone17,1")

    gt_walls = sorted([GROUND_TRUTH["floor_dimensions_cm"]["length"], GROUND_TRUTH["floor_dimensions_cm"]["breadth"]] * 2)
    gt_ceiling = GROUND_TRUTH["ceiling_height_cm"]
    gt_area_m2 = GROUND_TRUTH["floor_area_m2"]
    gt_opening_widths = [o["width_cm"] for o in GROUND_TRUTH["openings"]]

    report = BenchmarkReport()
    device = "iPhone17,1"  # the same physical iPhone 16 Pro captured every tier

    # tier is tracked alongside each result for the device matrix (Phase 8) --
    # kept out of GateResult itself since pipeline/benchmark.py's gate math
    # is tier-agnostic by design; this script is where tier context belongs.
    tier_by_result: dict[int, str] = {}

    def _add(result, tier: str):
        tier_by_result[id(result)] = tier
        report.results.append(result)

    # --- LiDAR tier: ceiling height, openings ---
    _add(score_ceiling_height(lidar_room.ceiling_height.value, gt_ceiling), "lidar")

    predicted_opening_widths = [o.width.value for o in lidar_room.openings]
    pairs = match_openings_by_nearest_width(predicted_opening_widths, gt_opening_widths)
    _add(score_opening_widths(pairs), "lidar")

    # --- Repeatability: bedroom_1 vs bedroom_1_recapture, photo tier ---
    ceiling_repeat = score_ceiling_repeatability(photo_room.ceiling_height.value, photo_recapture_room.ceiling_height.value)
    ceiling_repeat.detail += " [CAVEAT: photo tier's ceiling height is a fixed default, not measured -- this comparison is vacuous]"
    _add(ceiling_repeat, "photo")

    wall_repeat = score_repeatability_walls(_sorted_walls_cm(photo_room), _sorted_walls_cm(photo_recapture_room))
    wall_repeat.detail += " [CAVEAT: photo tier's wall lengths are a fixed default, not measured -- this comparison is vacuous]"
    _add(wall_repeat, "photo")

    # --- Photo-tier footprint (single-room proxy; real gate is the
    # multi-room stitched footprint, not yet wired to real captures) ---
    footprint = score_footprint_tolerance(photo_room.floor_area.value, gt_area_m2)
    footprint.detail += " [CAVEAT: this is bedroom_1's single-room footprint, a proxy -- the real gate is the whole-property stitched footprint, not yet run against real multi-room captures]"
    _add(footprint, "photo")

    # --- Video-tier wall lengths ---
    _add(score_video_tier_walls(_sorted_walls_cm(video_room), gt_walls), "video")

    print(report.to_markdown())
    print()
    print(f"Overall: {'ALL GATES PASS' if report.all_passed else 'SOME GATES FAIL'}")

    out_path = REPO_ROOT / "docs" / "benchmark_report.md"
    out_path.write_text(
        "# Benchmark Report (bedroom_1)\n\n"
        "Only bedroom_1 has ground truth in a shape (rectangular L x B) this benchmark "
        "script can automatically compare against reconstructed walls. common-space, "
        "kitchen-dining, and hallway_washer_dryer are irregular rooms (see their "
        "ground_truth.json files) and are not auto-scored here -- comparing an "
        "irregular perimeter against our box-room reconstruction model isn't well-defined "
        "without per-wall correspondence, which isn't built yet.\n\n"
        + report.to_markdown()
        + f"\n\nOverall: {'ALL GATES PASS' if report.all_passed else 'SOME GATES FAIL'}\n"
    )
    print(f"\nWritten to {out_path}")

    results_json_path = REPO_ROOT / "docs" / "benchmark_results.json"
    results_json_path.write_text(
        json.dumps(
            [
                {
                    "tier": tier_by_result[id(r)],
                    "device": device,
                    "room_id": "bedroom_1",
                    "gate_name": r.gate_name,
                    "passed": r.passed,
                    "metric_description": r.metric_description,
                    "actual_value": r.actual_value,
                    "threshold": r.threshold,
                    "detail": r.detail,
                }
                for r in report.results
            ],
            indent=2,
        )
    )
    print(f"Written to {results_json_path}")


if __name__ == "__main__":
    main()
