from pathlib import Path

from pipeline.adapters.lidar_adapter import LidarAdapter
from pipeline.adapters.photo_adapter import PhotoAdapter
from pipeline.adapters.video_adapter import VideoAdapter
from pipeline.core.types import Tier

FIXTURES = Path(__file__).parent / "fixtures"


def test_photo_adapter():
    capture = PhotoAdapter().load(FIXTURES / "photo_room", room_id="living_room")
    assert capture.tier == Tier.PHOTO
    assert len(capture.frames) == 2
    assert all(f.pose is None and f.depth_path is None for f in capture.frames)


def test_video_adapter():
    capture = VideoAdapter().load(FIXTURES / "video_room" / "clip.mp4", room_id="kitchen")
    assert capture.tier == Tier.VIDEO
    assert len(capture.frames) > 0
    assert all(f.pose is None for f in capture.frames)


def test_lidar_adapter():
    capture = LidarAdapter().load(FIXTURES / "lidar_room", room_id="bedroom")
    assert capture.tier == Tier.LIDAR
    assert len(capture.frames) == 1
    frame = capture.frames[0]
    assert frame.pose is not None
    assert frame.intrinsics is not None
    assert frame.depth_path is not None
    assert capture.world_map_path is not None
