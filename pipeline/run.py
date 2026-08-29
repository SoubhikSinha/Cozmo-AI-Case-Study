from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.adapters.lidar_adapter import LidarAdapter
from pipeline.adapters.photo_adapter import PhotoAdapter
from pipeline.adapters.video_adapter import VideoAdapter
from pipeline.concealed_damage import evaluate_concealed_damage
from pipeline.core.types import Tier
from pipeline.damage_detection import detect_damage
from pipeline.render import render_plan
from pipeline.room_reconstruction import reconstruct_room
from pipeline.schema import PropertyPlan, Room
from pipeline.scope_generator import generate_scope_items
from pipeline.stitching import Connector, stitch_rooms

_VIDEO_EXTS = {".mp4", ".mov"}

_ADAPTERS = {
    Tier.PHOTO: PhotoAdapter(),
    Tier.VIDEO: VideoAdapter(),
    Tier.LIDAR: LidarAdapter(),
}


def _resolve_video_path(room_dir: Path) -> Path:
    if room_dir.is_file():
        return room_dir
    matches = [p for p in room_dir.iterdir() if p.suffix.lower() in _VIDEO_EXTS]
    if not matches:
        raise SystemExit(f"No video file found under {room_dir}")
    return matches[0]


def _reconstruct_one_room(tier: Tier, room_dir: Path, room_id: str, device: str, context: dict | None = None) -> Room:
    """adapter -> Capture -> reconstruct_room -> damage detection ->
    concealed-damage rules -> scope items, for one room. Shared by both the
    single-room and multi-room (manifest) CLI paths.

    `context` carries building-topology facts a rule needs but can't infer
    from geometry (e.g. "below_bathroom") -- see pipeline/concealed_damage.py.
    Defaults to {}, so no flag fires unless the caller supplies the fact.
    """
    load_path = _resolve_video_path(room_dir) if tier == Tier.VIDEO else room_dir
    capture = _ADAPTERS[tier].load(load_path, room_id=room_id)

    room = reconstruct_room(capture, room_id=room_id, name=room_id, device=device)
    room.damage_regions = detect_damage(room, capture)
    room.concealed_flags = evaluate_concealed_damage(room, context)
    room.scope_items = generate_scope_items(room)
    return room


def run_capture(tier: Tier, room_dir: Path, room_id: str, device: str, context: dict | None = None) -> PropertyPlan:
    """One capture -> one Room -> a trivially single-room PropertyPlan (same
    output contract a multi-room property uses, with connectors=[])."""
    room = _reconstruct_one_room(tier, room_dir, room_id, device, context)
    plan = stitch_rooms([room], connectors=[])
    plan.property_id = room_id
    return plan


def run_property(manifest_path: Path) -> PropertyPlan:
    """A real multi-room property: reconstructs every room named in the
    manifest, then stitches them via the hand-declared connectors. Adjacency
    is never auto-inferred from geometry -- see pipeline/stitching.py."""
    manifest = json.loads(manifest_path.read_text())

    rooms = [
        _reconstruct_one_room(
            Tier(entry["tier"]),
            Path(entry["room_dir"]),
            entry["room_id"],
            entry.get("device", "unknown"),
            entry.get("context"),
        )
        for entry in manifest["rooms"]
    ]
    connectors = [
        Connector(room_a=c["room_a"], wall_a=c["wall_a"], room_b=c["room_b"], wall_b=c["wall_b"])
        for c in manifest.get("connectors", [])
    ]
    drift_correction = manifest.get("drift_correction", True)

    plan = stitch_rooms(rooms, connectors, drift_correction=drift_correction)
    plan.property_id = manifest.get("property_id", manifest_path.stem)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(prog="pipeline.run")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--room-dir", type=Path, help="Single-room capture directory")
    mode.add_argument("--property-manifest", type=Path, help="Multi-room property manifest JSON")

    parser.add_argument("--tier", choices=[t.value for t in Tier], help="Required with --room-dir")
    parser.add_argument("--room-id", default=None, help="Defaults to the room-dir folder name")
    parser.add_argument("--device", default="unknown")
    parser.add_argument("--out-dir", type=Path, default=Path("output"))
    parser.add_argument(
        "--context",
        default=None,
        help='JSON string of concealed-damage rule context, e.g. \'{"below_bathroom": true}\'',
    )
    args = parser.parse_args()

    if args.property_manifest:
        plan = run_property(args.property_manifest)
    else:
        if not args.tier:
            raise SystemExit("--tier is required with --room-dir")
        tier = Tier(args.tier)
        room_id = args.room_id or args.room_dir.stem
        context = json.loads(args.context) if args.context else None
        plan = run_capture(tier, args.room_dir, room_id, args.device, context)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"{plan.property_id}.json"
    image_path = args.out_dir / f"{plan.property_id}.png"

    json_path.write_text(json.dumps(plan.to_dict(), indent=2))
    render_plan(plan, image_path)

    print(f"JSON:     {json_path}")
    print(f"Rendered: {image_path}")


if __name__ == "__main__":
    main()
