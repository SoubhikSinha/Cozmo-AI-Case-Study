"""Builds the real Part 3 head-to-head comparison: our LiDAR-tier output vs.
the named competitor vs. ground truth. Rooms are discovered dynamically --
never hardcoded -- from whichever rooms have both rectangular ground truth
(media/ground_truth/<room>/ground_truth.json with a "floor_dimensions_cm"
key) and a matching entry in the competitor's measurements.json, so this
runs unchanged against a tester's own capture and their own competitor
export.
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.adapters.lidar_adapter import LidarAdapter
from pipeline.competitor_parser import load_competitor_measurements
from pipeline.head_to_head import HeadToHeadReport, build_report
from pipeline.room_reconstruction import reconstruct_room

from _room_discovery import all_ground_truth_rooms

REPO_ROOT = Path(__file__).resolve().parent.parent

# The only two facts this script can't discover from media/ itself: which
# competitor app was used, and its version -- both come from the human who
# ran the competitor's capture, not from any file structure.
COMPETITOR_APP = "magicplan"
COMPETITOR_VERSION = "2026.34.1"
COMPETITOR_MEASUREMENTS = REPO_ROOT / "media/competitor_benchmark/magicplan/measurements.json"


def _sorted_walls_cm(room) -> list[float]:
    return sorted(w.length.value for w in room.walls)


def build_real_head_to_head_report() -> tuple[HeadToHeadReport, dict]:
    """Loads real data and builds the comparison. Returns the report plus
    narrative metadata, so every output document (table CSV/markdown, the
    written-up report) is generated from this one source -- numbers can't
    drift between documents."""
    competitor = load_competitor_measurements(COMPETITOR_MEASUREMENTS)
    all_rooms = all_ground_truth_rooms(REPO_ROOT)

    rooms_tested = [room_id for room_id, _ in all_rooms if room_id in competitor]
    rooms_scored = [room_id for room_id, gt in all_rooms if room_id in competitor and "floor_dimensions_cm" in gt]
    excluded_rooms = sorted(set(rooms_tested) - set(rooms_scored))

    dimensions = []
    for room_id, ground_truth in all_rooms:
        if room_id not in rooms_scored:
            continue

        lidar_dir = next((REPO_ROOT / "media/lidar" / room_id).iterdir())
        lidar_capture = LidarAdapter().load(lidar_dir, room_id=room_id)
        our_room = reconstruct_room(lidar_capture, room_id=room_id, name=room_id, device="iPhone17,1")

        gt_length = ground_truth["floor_dimensions_cm"]["length"]
        gt_breadth = ground_truth["floor_dimensions_cm"]["breadth"]
        gt_ceiling = ground_truth["ceiling_height_cm"]

        our_walls_sorted = _sorted_walls_cm(our_room)  # [short, short, long, long]
        our_breadth, our_length = our_walls_sorted[0], our_walls_sorted[-1]

        their = competitor[room_id]
        dimensions.extend(
            [
                (f"{room_id}_length", gt_length, our_length, their.length.value),
                (f"{room_id}_breadth", gt_breadth, our_breadth, their.width.value),
                (f"{room_id}_ceiling_height", gt_ceiling, our_room.ceiling_height.value, their.ceiling_height.value),
            ]
        )

    report = build_report(dimensions)
    excluded_note = (
        f"{', '.join(excluded_rooms)} captured with both our pipeline and {COMPETITOR_APP}, but excluded from "
        "scoring: ground truth is an irregular room (a per-wall perimeter, not a single L x B box), so there "
        "is no single width/length/ceiling-height ground-truth value to compare the competitor's box-shaped "
        "measurement against without inventing a mapping."
        if excluded_rooms
        else "No rooms excluded -- every room tested against the competitor had comparable rectangular ground truth."
    )
    metadata = {
        "competitor_app": COMPETITOR_APP,
        "competitor_version": COMPETITOR_VERSION,
        "rooms_tested": rooms_tested,
        "rooms_scored": rooms_scored,
        "excluded_room_note": excluded_note,
        "device": "iPhone17,1",
    }
    return report, metadata


def main() -> None:
    report, metadata = build_real_head_to_head_report()

    print(report.to_markdown())

    csv_path = REPO_ROOT / "docs" / "head_to_head_table.csv"
    csv_path.write_text(report.to_csv())

    scored_note = ", ".join(metadata["rooms_scored"]) or "(none)"
    md_path = REPO_ROOT / "docs" / "head_to_head_table.md"
    md_path.write_text(
        f"# Head-to-Head: Our Pipeline vs. {metadata['competitor_app']} ({metadata['competitor_version']})\n\n"
        f"LiDAR tier, {scored_note} (only rooms with ground truth in a shape comparable to both our "
        f"box-room reconstruction and {metadata['competitor_app']}'s box-room output -- see "
        "docs/head_to_head.md for why other rooms may be excluded).\n\n"
        + report.to_markdown()
        + "\n"
    )

    report_path = REPO_ROOT / "docs" / "head_to_head_report.md"
    report_path.write_text(_render_report_md(report, metadata))

    print(f"\nWritten to {csv_path}")
    print(f"Written to {md_path}")
    print(f"Written to {report_path}")


def _render_report_md(report: HeadToHeadReport, metadata: dict) -> str:
    pass_fail = "PASS" if report.win_or_tie_fraction >= 0.70 else "FAIL"
    return (
        "# Part 3: Head-to-Head Report\n\n"
        "Generated by `scripts/run_head_to_head.py` from real data -- every number below "
        "comes directly from `pipeline.head_to_head.HeadToHeadReport`, not retyped by hand.\n\n"
        f"**Competitor app:** {metadata['competitor_app']}, version {metadata['competitor_version']} (free tier)\n\n"
        f"**Device:** {metadata['device']}\n\n"
        f"**Rooms tested:** {', '.join(metadata['rooms_tested']) or '(none)'}\n\n"
        f"**Rooms scored:** {', '.join(metadata['rooms_scored']) or '(none)'}\n\n"
        f"{metadata['excluded_room_note']}\n\n"
        "## Comparison table\n\n"
        f"{report.to_markdown()}\n\n"
        "## Result\n\n"
        f"**{pass_fail}** -- {report.win_or_tie_fraction * 100:.1f}% beat-or-tie rate against the "
        "assessment's >=70% bar. "
        + (
            "This traces directly to the two known LiDAR reconstruction issues on record "
            "(box-footprint fit, ceiling-height percentile trim) -- see docs/benchmark_report.md "
            "and CLAUDE.md -- and is independent evidence for prioritizing them in the Part 4 fix loop."
            if pass_fail == "FAIL"
            else "Our pipeline meets or beats the competitor on the required fraction of shared dimensions."
        )
    )


if __name__ == "__main__":
    main()
