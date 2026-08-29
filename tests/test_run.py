import json
import subprocess
import sys
from pathlib import Path

from pipeline.schema import PropertyPlan

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_run_end_to_end_on_synthetic_photo_capture(tmp_path):
    room_dir = tmp_path / "room_photos"
    room_dir.mkdir()
    for i in range(3):
        (room_dir / f"img_{i}.jpg").touch()

    out_dir = tmp_path / "output"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pipeline.run",
            "--tier",
            "photo",
            "--room-dir",
            str(room_dir),
            "--room-id",
            "test_room",
            "--out-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    json_path = out_dir / "test_room.json"
    image_path = out_dir / "test_room.png"

    assert json_path.exists()
    assert image_path.exists()
    assert image_path.stat().st_size > 0

    payload = json.loads(json_path.read_text())
    plan = PropertyPlan.from_dict(payload)  # raises if the JSON doesn't match the schema

    assert plan.property_id == "test_room"
    assert len(plan.rooms) == 1
    assert plan.rooms[0].id == "test_room"
    assert len(plan.rooms[0].walls) == 4


def test_run_end_to_end_on_multi_room_manifest(tmp_path):
    # Two synthetic photo-tier rooms -- each defaults to the same 350cm box
    # per the sparse-tier fallback (see room_reconstruction._reconstruct_sparse),
    # so wall-1<->wall-3 is a valid connector, same pairing proven in
    # tests/test_stitching.py. Demonstrates the "photo-tier whole-property
    # stitch" gate: per-room photo folders -> one stitched plan, via the CLI.
    room_a_dir = tmp_path / "room_a"
    room_b_dir = tmp_path / "room_b"
    for room_dir in (room_a_dir, room_b_dir):
        room_dir.mkdir()
        for i in range(3):
            (room_dir / f"img_{i}.jpg").touch()

    manifest_path = tmp_path / "property.json"
    manifest_path.write_text(
        json.dumps(
            {
                "property_id": "test_property",
                "rooms": [
                    {"room_id": "room_a", "tier": "photo", "room_dir": str(room_a_dir)},
                    {"room_id": "room_b", "tier": "photo", "room_dir": str(room_b_dir)},
                ],
                "connectors": [
                    {"room_a": "room_a", "wall_a": "wall-1", "room_b": "room_b", "wall_b": "wall-3"}
                ],
            }
        )
    )

    out_dir = tmp_path / "output"
    result = subprocess.run(
        [sys.executable, "-m", "pipeline.run", "--property-manifest", str(manifest_path), "--out-dir", str(out_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    json_path = out_dir / "test_property.json"
    image_path = out_dir / "test_property.png"
    assert json_path.exists()
    assert image_path.exists()
    assert image_path.stat().st_size > 0

    plan = PropertyPlan.from_dict(json.loads(json_path.read_text()))
    assert plan.property_id == "test_property"
    assert {r.id for r in plan.rooms} == {"room_a", "room_b"}
    assert plan.adjacency == [("room_a", "room_b", "wall-1|wall-3")]
