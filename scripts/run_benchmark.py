"""Runs the Part 2 gates against whichever room in media/ground_truth/ has
clean rectangular ground truth (a "floor_dimensions_cm" key) -- irregular
rooms (perimeter-list ground truth) aren't comparable against the box-room
reconstruction model without per-wall correspondence, which isn't built
yet, and are skipped with a note in the report. Room selection is dynamic:
no room name is hardcoded, so this runs unchanged against a tester's own
capture as long as one scoreable room's ground truth exists.
"""
from __future__ import annotations

import json
import time
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

from _room_discovery import find_scoreable_room

REPO_ROOT = Path(__file__).resolve().parent.parent


def _sorted_walls_cm(room) -> list[float]:
    return sorted(w.length.value for w in room.walls)


def _timed_reconstruct(capture, room_id, timings, label):
    """Wraps adapter-load + reconstruct_room with a wall-clock timer, so the
    benchmark report can state real timing per tier (Deliverable #5), not
    just accuracy. Timing starts once the Capture is already loaded (i.e.
    measures reconstruction cost, not file-load I/O, which is dominated by
    disk speed rather than pipeline design)."""
    t0 = time.perf_counter()
    room = reconstruct_room(capture, room_id=room_id, name=room_id, device="iPhone17,1")
    timings[label] = time.perf_counter() - t0
    return room


def main() -> None:
    timings: dict[str, float] = {}
    room_id, ground_truth = find_scoreable_room(REPO_ROOT)

    lidar_dir = next((REPO_ROOT / "media/lidar" / room_id).iterdir())
    lidar_capture = LidarAdapter().load(lidar_dir, room_id=room_id)
    lidar_room = _timed_reconstruct(lidar_capture, room_id, timings, f"lidar_reconstruct_{room_id}")

    photo_capture = PhotoAdapter().load(REPO_ROOT / "media/photos" / room_id, room_id=room_id)
    photo_room = _timed_reconstruct(photo_capture, room_id, timings, f"photo_reconstruct_{room_id}")

    recapture_gate = ground_truth.get("repeatability_gate")
    if recapture_gate is None or recapture_gate.get("tier") != "photo":
        raise SystemExit(f"{room_id}/ground_truth.json is missing a photo-tier 'repeatability_gate' entry.")
    photo_recapture = PhotoAdapter().load(REPO_ROOT / recapture_gate["recapture_folder"], room_id=room_id)
    photo_recapture_room = _timed_reconstruct(photo_recapture, room_id, timings, f"photo_reconstruct_{room_id}_recapture")

    video_files = list((REPO_ROOT / "media/video" / room_id).glob("*.[Mm][Oo][Vv]")) + list(
        (REPO_ROOT / "media/video" / room_id).glob("*.[Mm][Pp]4")
    )
    video_capture = VideoAdapter().load(video_files[0], room_id=room_id)
    video_room = _timed_reconstruct(video_capture, room_id, timings, f"video_reconstruct_{room_id}")

    gt_walls = sorted([ground_truth["floor_dimensions_cm"]["length"], ground_truth["floor_dimensions_cm"]["breadth"]] * 2)
    gt_ceiling = ground_truth["ceiling_height_cm"]
    gt_area_m2 = ground_truth["floor_area_m2"]
    gt_opening_widths = [o["width_cm"] for o in ground_truth["openings"]]

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

    # --- Repeatability: room vs. its recapture, photo tier ---
    ceiling_repeat = score_ceiling_repeatability(photo_room.ceiling_height.value, photo_recapture_room.ceiling_height.value)
    ceiling_repeat.detail += " [CAVEAT: photo tier's ceiling height is a fixed default, not measured -- this comparison is vacuous]"
    _add(ceiling_repeat, "photo")

    wall_repeat = score_repeatability_walls(_sorted_walls_cm(photo_room), _sorted_walls_cm(photo_recapture_room))
    wall_repeat.detail += " [CAVEAT: photo tier's wall lengths are a fixed default, not measured -- this comparison is vacuous]"
    _add(wall_repeat, "photo")

    # --- Photo-tier footprint (single-room proxy; real gate is the
    # multi-room stitched footprint, not yet wired to real captures) ---
    footprint = score_footprint_tolerance(photo_room.floor_area.value, gt_area_m2)
    footprint.detail += f" [CAVEAT: this is {room_id}'s single-room footprint, a proxy -- the real gate is the whole-property stitched footprint, not yet run against real multi-room captures]"
    _add(footprint, "photo")

    # --- Video-tier wall lengths ---
    _add(score_video_tier_walls(_sorted_walls_cm(video_room), gt_walls), "video")

    print(report.to_markdown())
    print()
    print(f"Overall: {'ALL GATES PASS' if report.all_passed else 'SOME GATES FAIL'}")

    irregular_rooms = sorted(
        p.parent.name
        for p in (REPO_ROOT / "media/ground_truth").glob("*/ground_truth.json")
        if p.parent.name != room_id
    )

    out_path = REPO_ROOT / "docs" / "benchmark_report.md"
    out_path.write_text(
        f"# Benchmark Report ({room_id})\n\n"
        f"Only {room_id} has ground truth in a shape (rectangular L x B) this benchmark "
        f"script can automatically compare against reconstructed walls. {', '.join(irregular_rooms) or '(none)'} "
        "are irregular rooms (see their ground_truth.json files) and are not auto-scored "
        "here -- comparing an irregular perimeter against our box-room reconstruction "
        "model isn't well-defined without per-wall correspondence, which isn't built yet.\n\n"
        + report.to_markdown()
        + f"\n\nOverall: {'ALL GATES PASS' if report.all_passed else 'SOME GATES FAIL'}\n"
    )
    print(f"\nWritten to {out_path}")

    results_json_path = REPO_ROOT / "docs" / "benchmark_results.json"
    timing_path = REPO_ROOT / "docs" / "timing.md"
    timing_lines = [
        f"# Reconstruction Timing ({room_id}, on this machine)",
        "",
        "Wall-clock time for `reconstruct_room()` only (adapter load / file I/O excluded, since that's disk-speed-bound, not pipeline design). Measured via `time.perf_counter()` in `scripts/run_benchmark.py`, regenerated every run -- not a one-off manual measurement.",
        "",
        "| Run | Seconds |",
        "|---|---|",
    ]
    timing_lines += [f"| {label} | {seconds:.3f} |" for label, seconds in timings.items()]
    timing_path.write_text("\n".join(timing_lines) + "\n")
    print(f"Written to {timing_path}")

    results_json_path.write_text(
        json.dumps(
            [
                {
                    "tier": tier_by_result[id(r)],
                    "device": device,
                    "room_id": room_id,
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
