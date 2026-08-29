from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.adapters.lidar_adapter import LidarAdapter
from pipeline.adapters.photo_adapter import PhotoAdapter
from pipeline.adapters.video_adapter import VideoAdapter
from pipeline.core.types import Tier
from pipeline.room_reconstruction import reconstruct_room
from pipeline.schema import Room

MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media"

VIDEO_EXTS = {".mp4", ".mov"}


def _load_lidar_capture(room: str):
    room_dir = MEDIA_ROOT / "lidar" / room
    if not room_dir.exists():
        raise SystemExit(f"No LiDAR data for room '{room}' at {room_dir}")
    export_dirs = [p for p in room_dir.iterdir() if p.is_dir()]
    if not export_dirs:
        raise SystemExit(f"No LiDAR export subfolder found under {room_dir}")
    return LidarAdapter().load(export_dirs[0], room_id=room)


def _load_photo_capture(room: str):
    room_dir = MEDIA_ROOT / "photos" / room
    if not room_dir.exists():
        raise SystemExit(f"No photo data for room '{room}' at {room_dir}")
    return PhotoAdapter().load(room_dir, room_id=room)


def _load_video_capture(room: str):
    room_dir = MEDIA_ROOT / "video" / room
    if not room_dir.exists():
        raise SystemExit(f"No video data for room '{room}' at {room_dir}")
    video_files = [p for p in room_dir.iterdir() if p.suffix.lower() in VIDEO_EXTS]
    if not video_files:
        raise SystemExit(f"No video file found under {room_dir}")
    return VideoAdapter().load(video_files[0], room_id=room)


_LOADERS = {
    Tier.LIDAR: _load_lidar_capture,
    Tier.PHOTO: _load_photo_capture,
    Tier.VIDEO: _load_video_capture,
}


def _print_room(tier: Tier, room: Room) -> None:
    print(f"\n=== {tier.value.upper()} ===")
    for wall in room.walls:
        lo, hi = wall.length.confidence_interval
        print(f"  {wall.id}: {wall.length.value:.1f} cm  (CI: {lo:.1f}-{hi:.1f})")
    print(f"  ceiling height: {room.ceiling_height.value:.1f} cm")
    print(f"  floor area: {room.floor_area.value:.2f} {room.floor_area.unit}")
    if room.openings:
        for o in room.openings:
            print(f"  opening on {o.wall_id}: {o.width.value:.1f} cm wide ({o.type.value})")
    else:
        print("  openings: none detected")


def main() -> None:
    parser = argparse.ArgumentParser(prog="test_reconstruction")
    parser.add_argument("--room", required=True, help="Room folder name, e.g. bedroom_1, kitchen-dining")
    parser.add_argument(
        "--tier",
        choices=[t.value for t in Tier] + ["all"],
        default="all",
        help="Which tier to test (default: all three)",
    )
    parser.add_argument("--device", default="iPhone17,1", help="Device string for the output metadata")
    args = parser.parse_args()

    tiers = list(Tier) if args.tier == "all" else [Tier(args.tier)]

    for tier in tiers:
        try:
            capture = _LOADERS[tier](args.room)
        except SystemExit as e:
            print(f"\n=== {tier.value.upper()} ===\n  skipped: {e}")
            continue

        room = reconstruct_room(capture, room_id=args.room, name=args.room, device=args.device)
        _print_room(tier, room)


if __name__ == "__main__":
    main()
