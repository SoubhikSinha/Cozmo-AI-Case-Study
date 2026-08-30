import math

import cv2
import numpy as np

from pipeline.core.types import Capture, Frame, Intrinsics, Pose, Tier
from pipeline.room_reconstruction import reconstruct_room

# Synthetic 4m x 4m x 2.5m box room, camera at room center (2, 1.25, 2),
# one frame facing each wall head-on. Depth is stored as a flat plane
# (constant per-pixel Z-forward distance), which is exactly what a
# frontal flat wall produces under this back-projection convention.
FX = FY = 32.0
CX, CY = 32.0, 20.0
IMG_W, IMG_H = 64, 40
WALL_DISTANCE_M = 2.0
CAM_HEIGHT_M = 1.25
ROOM_CENTER = (2.0, CAM_HEIGHT_M, 2.0)

# North wall gets a synthetic doorway: columns 25-39 at row=CY read a much
# larger depth (open space beyond), everywhere else is flat wall depth.
DOOR_COLS = (25, 39)
DOOR_ROW = int(CY)


def _pose_for_yaw(position: tuple[float, float, float], yaw_deg: float) -> Pose:
    theta = math.radians(yaw_deg)
    right = (math.cos(theta), 0.0, -math.sin(theta))
    down = (0.0, -1.0, 0.0)
    forward = (math.sin(theta), 0.0, math.cos(theta))
    matrix = [
        [right[0], down[0], forward[0], position[0]],
        [right[1], down[1], forward[1], position[1]],
        [right[2], down[2], forward[2], position[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]
    return Pose(matrix=matrix)


def _make_wall_frame(tmp_path, index: int, yaw_deg: float, with_door: bool) -> Frame:
    depth = np.full((IMG_H, IMG_W), WALL_DISTANCE_M, dtype=np.float64)
    if with_door:
        depth[DOOR_ROW, DOOR_COLS[0] : DOOR_COLS[1] + 1] = WALL_DISTANCE_M * 2.5

    depth_mm = (depth * 1000).astype(np.uint16)
    depth_path = tmp_path / f"depth_{index:05d}.png"
    cv2.imwrite(str(depth_path), depth_mm)

    image_path = tmp_path / f"frame_{index:05d}.jpg"
    cv2.imwrite(str(image_path), np.zeros((IMG_H, IMG_W, 3), dtype=np.uint8))

    return Frame(
        image_path=image_path,
        depth_path=depth_path,
        pose=_pose_for_yaw(ROOM_CENTER, yaw_deg),
        intrinsics=Intrinsics(fx=FX, fy=FY, cx=CX, cy=CY),
        source_index=index,
    )


def _synthetic_box_room_capture(tmp_path) -> Capture:
    frames = [
        _make_wall_frame(tmp_path, 0, yaw_deg=0, with_door=True),  # north, has doorway
        _make_wall_frame(tmp_path, 1, yaw_deg=90, with_door=False),  # east
        _make_wall_frame(tmp_path, 2, yaw_deg=180, with_door=False),  # south
        _make_wall_frame(tmp_path, 3, yaw_deg=-90, with_door=False),  # west
    ]
    return Capture(tier=Tier.LIDAR, room_id="test_room", frames=frames)


def test_lidar_reconstruction_estimates_box_room_dimensions(tmp_path):
    capture = _synthetic_box_room_capture(tmp_path)
    room = reconstruct_room(capture, room_id="r1", name="test_room", device="iPhone17,1")

    assert len(room.walls) == 4
    for wall in room.walls:
        assert 300.0 <= wall.length.value <= 500.0  # designed as a 4m room
        lo, hi = wall.length.confidence_interval
        assert lo < wall.length.value < hi

    assert 180.0 <= room.ceiling_height.value <= 280.0  # designed as 2.5m
    assert room.floor_area.unit == "m2"
    assert 8.0 <= room.floor_area.value <= 25.0  # roughly 4m x 4m


def _make_two_door_frame(tmp_path, index: int) -> Frame:
    """North wall with two separate doorways (columns 2-8 and 25-39,
    separated by a wide gap of flat wall) -- exercises the run-splitting fix
    that lets one wall report more than one opening."""
    depth = np.full((IMG_H, IMG_W), WALL_DISTANCE_M, dtype=np.float64)
    depth[DOOR_ROW, 2:9] = WALL_DISTANCE_M * 2.0
    depth[DOOR_ROW, DOOR_COLS[0] : DOOR_COLS[1] + 1] = WALL_DISTANCE_M * 2.5

    depth_mm = (depth * 1000).astype(np.uint16)
    depth_path = tmp_path / f"depth_{index:05d}.png"
    cv2.imwrite(str(depth_path), depth_mm)
    image_path = tmp_path / f"frame_{index:05d}.jpg"
    cv2.imwrite(str(image_path), np.zeros((IMG_H, IMG_W, 3), dtype=np.uint8))

    return Frame(
        image_path=image_path,
        depth_path=depth_path,
        pose=_pose_for_yaw(ROOM_CENTER, yaw_deg=0),
        intrinsics=Intrinsics(fx=FX, fy=FY, cx=CX, cy=CY),
        source_index=index,
    )


def test_lidar_reconstruction_detects_multiple_openings_on_same_wall(tmp_path):
    frames = [
        _make_two_door_frame(tmp_path, 0),
        _make_wall_frame(tmp_path, 1, yaw_deg=90, with_door=False),
        _make_wall_frame(tmp_path, 2, yaw_deg=180, with_door=False),
        _make_wall_frame(tmp_path, 3, yaw_deg=-90, with_door=False),
    ]
    capture = Capture(tier=Tier.LIDAR, room_id="test_room", frames=frames)
    room = reconstruct_room(capture, room_id="r1", name="test_room", device="iPhone17,1")

    assert len(room.openings) == 2
    assert len({o.wall_id for o in room.openings}) == 1  # both on the same (north) wall


def test_lidar_reconstruction_detects_doorway_opening(tmp_path):
    capture = _synthetic_box_room_capture(tmp_path)
    room = reconstruct_room(capture, room_id="r1", name="test_room", device="iPhone17,1")

    assert len(room.openings) == 1
    opening = room.openings[0]
    # Width is now measured at each edge pixel's own depth (fixed a real bug:
    # using the wall's near depth for both edges collapsed a real ~60cm
    # bedroom_1 door down to 19.5cm -- see room_reconstruction.py). This
    # fixture's doorway anomaly sits at 2.5x the wall's distance (open space
    # beyond), so its correctly-computed apparent width scales up with that
    # depth too -- ~218cm here, not the old wall-plane-depth estimate of
    # ~87.5cm. 150-300cm brackets that with room for pose-derivation noise.
    assert 150.0 <= opening.width.value <= 300.0
    assert 0.0 <= opening.position_on_wall <= 1.0


def test_photo_tier_falls_back_to_wide_confidence_defaults():
    frames = [Frame(image_path=f"img_{i}.jpg") for i in range(4)]
    capture = Capture(tier=Tier.PHOTO, room_id="dark_room", frames=frames)

    room = reconstruct_room(capture, room_id="r2", name="dark_room", device="iPhone16,1")

    assert len(room.walls) == 4
    assert room.openings == []
    for wall in room.walls:
        lo, hi = wall.length.confidence_interval
        relative_width = (hi - lo) / wall.length.value
        assert relative_width > 0.2  # honestly wide -- no real geometric signal
        # matches pipeline.confidence's photo-tier floor (_MIN_RELATIVE_ERROR),
        # since 4 sample images already saturates sqrt(N) averaging below the floor


def test_video_tier_uses_duration_but_wider_ci_than_lidar(tmp_path):
    capture_lidar = _synthetic_box_room_capture(tmp_path)
    lidar_room = reconstruct_room(capture_lidar, room_id="r1", name="room", device="iPhone17,1")

    frames = [Frame(image_path=f"frame_{i}.jpg", timestamp=float(i) * 2.0) for i in range(10)]
    video_capture = Capture(tier=Tier.VIDEO, room_id="room", frames=frames)
    video_room = reconstruct_room(video_capture, room_id="r3", name="room", device="iPhone16,1")

    lidar_rel_width = _relative_ci_width(lidar_room.walls[0].length)
    video_rel_width = _relative_ci_width(video_room.walls[0].length)
    assert video_rel_width > lidar_rel_width


def _relative_ci_width(measurement) -> float:
    lo, hi = measurement.confidence_interval
    return (hi - lo) / measurement.value
