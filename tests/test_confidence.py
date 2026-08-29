from pipeline.confidence import measurement_ci
from pipeline.core.types import Tier


def _relative_width(ci: tuple[float, float], value: float) -> float:
    lo, hi = ci
    return (hi - lo) / value


def test_lidar_ci_tighter_than_video_tighter_than_photo_same_sample_count():
    """Same room, same 'how many samples backed this measurement' -- tier
    alone should still order LiDAR < Video < Photo, since the base sensor/
    method error priors differ even before sample-count averaging."""
    value = 400.0
    n = 20

    lidar_ci = measurement_ci(Tier.LIDAR, value, n)
    video_ci = measurement_ci(Tier.VIDEO, value, n)
    photo_ci = measurement_ci(Tier.PHOTO, value, n)

    lidar_width = _relative_width(lidar_ci, value)
    video_width = _relative_width(video_ci, value)
    photo_width = _relative_width(photo_ci, value)

    assert lidar_width < video_width < photo_width


def test_more_samples_tighten_the_interval_within_a_tier():
    value = 400.0

    ci_few = measurement_ci(Tier.LIDAR, value, sample_count=4)
    ci_many = measurement_ci(Tier.LIDAR, value, sample_count=4000)

    assert _relative_width(ci_many, value) < _relative_width(ci_few, value)


def test_interval_floors_at_a_minimum_and_does_not_keep_shrinking_forever():
    value = 400.0

    ci_huge = measurement_ci(Tier.LIDAR, value, sample_count=10_000_000)
    width = _relative_width(ci_huge, value)

    assert width >= 0.005  # the tier's documented relative-error floor


def test_reconstruct_room_end_to_end_orders_ci_by_tier(tmp_path):
    """The actual requirement: same room, different tiers, run through the
    real reconstruction pipeline -> LiDAR CI < Video CI < Photo CI on the
    resulting wall-length Measurement."""
    import math

    import cv2
    import numpy as np

    from pipeline.core.types import Capture, Frame, Intrinsics, Pose
    from pipeline.room_reconstruction import reconstruct_room

    # --- LiDAR: reuse the same synthetic box-room setup as test_room_reconstruction.py ---
    fx = fy = 32.0
    cx, cy = 32.0, 20.0
    img_w, img_h = 64, 40
    wall_distance_m = 2.0
    cam_height_m = 1.25
    center = (2.0, cam_height_m, 2.0)

    def pose_for_yaw(yaw_deg):
        theta = math.radians(yaw_deg)
        right = (math.cos(theta), 0.0, -math.sin(theta))
        down = (0.0, -1.0, 0.0)
        forward = (math.sin(theta), 0.0, math.cos(theta))
        return Pose(
            matrix=[
                [right[0], down[0], forward[0], center[0]],
                [right[1], down[1], forward[1], center[1]],
                [right[2], down[2], forward[2], center[2]],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )

    def make_frame(index, yaw_deg):
        depth = np.full((img_h, img_w), wall_distance_m, dtype=np.float64)
        depth_mm = (depth * 1000).astype(np.uint16)
        depth_path = tmp_path / f"depth_{index:05d}.png"
        cv2.imwrite(str(depth_path), depth_mm)
        image_path = tmp_path / f"frame_{index:05d}.jpg"
        cv2.imwrite(str(image_path), np.zeros((img_h, img_w, 3), dtype=np.uint8))
        return Frame(
            image_path=image_path,
            depth_path=depth_path,
            pose=pose_for_yaw(yaw_deg),
            intrinsics=Intrinsics(fx=fx, fy=fy, cx=cx, cy=cy),
            source_index=index,
        )

    lidar_capture = Capture(
        tier=Tier.LIDAR,
        room_id="room",
        frames=[make_frame(i, yaw) for i, yaw in enumerate([0, 90, 180, -90])],
    )
    video_capture = Capture(
        tier=Tier.VIDEO,
        room_id="room",
        frames=[Frame(image_path=f"v_{i}.jpg", timestamp=float(i) * 2.0) for i in range(10)],
    )
    photo_capture = Capture(
        tier=Tier.PHOTO,
        room_id="room",
        frames=[Frame(image_path=f"p_{i}.jpg") for i in range(4)],
    )

    lidar_room = reconstruct_room(lidar_capture, room_id="r", name="room", device="test")
    video_room = reconstruct_room(video_capture, room_id="r", name="room", device="test")
    photo_room = reconstruct_room(photo_capture, room_id="r", name="room", device="test")

    lidar_width = _relative_width(lidar_room.walls[0].length.confidence_interval, lidar_room.walls[0].length.value)
    video_width = _relative_width(video_room.walls[0].length.confidence_interval, video_room.walls[0].length.value)
    photo_width = _relative_width(photo_room.walls[0].length.confidence_interval, photo_room.walls[0].length.value)

    assert lidar_width < video_width < photo_width
