import sys
import threading
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sort_media import classify, sort_inbox, wait_for_burst  # noqa: E402


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def test_classify_by_extension(tmp_path):
    assert classify(_touch(tmp_path / "a.jpg")) == "photos"
    assert classify(_touch(tmp_path / "a.heic")) == "photos"
    assert classify(_touch(tmp_path / "a.mp4")) == "video"
    assert classify(_touch(tmp_path / "a.mov")) == "video"
    assert classify(_touch(tmp_path / "a.txt")) is None


def test_classify_lidar_dir(tmp_path):
    lidar_dir = tmp_path / "scan_export"
    _touch(lidar_dir / "frame_00000.json")
    _touch(lidar_dir / "frame_00000.jpg")
    assert classify(lidar_dir) == "lidar"


def test_classify_lidar_zip(tmp_path):
    zip_path = tmp_path / "scan_export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("frame_00000.json", "{}")
        zf.writestr("frame_00000.jpg", "")
    assert classify(zip_path) == "lidar"


def test_sort_inbox_routes_each_tier(tmp_path):
    inbox = tmp_path / "inbox"
    media_root = tmp_path / "media"
    inbox.mkdir()
    _touch(inbox / "photo1.jpg")
    _touch(inbox / "clip.mp4")

    lidar_dir = inbox / "lidar_export"
    _touch(lidar_dir / "frame_00000.json")
    _touch(lidar_dir / "frame_00000.jpg")

    moved = sort_inbox(inbox, media_root, room="bedroom")

    assert (media_root / "photos" / "bedroom" / "photo1.jpg").exists()
    assert (media_root / "video" / "bedroom" / "clip.mp4").exists()
    assert (media_root / "lidar" / "bedroom" / "lidar_export" / "frame_00000.json").exists()
    assert len(list(inbox.iterdir())) == 0
    assert len(moved) == 3


def test_sort_inbox_extracts_lidar_zip(tmp_path):
    inbox = tmp_path / "inbox"
    media_root = tmp_path / "media"
    inbox.mkdir()

    zip_path = inbox / "scan_export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("frame_00000.json", "{}")

    sort_inbox(inbox, media_root, room="kitchen_take2")

    assert (media_root / "lidar" / "kitchen_take2" / "frame_00000.json").exists()
    assert not zip_path.exists()


def test_wait_for_burst_debounces(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()

    def drop_files_over_time():
        _touch(inbox / "a.jpg")
        time.sleep(0.05)
        _touch(inbox / "b.jpg")  # arrives mid-quiet-window, should reset the timer

    threading.Thread(target=drop_files_over_time).start()

    start = time.monotonic()
    wait_for_burst(inbox, poll_seconds=0.02, quiet_seconds=0.1)
    elapsed = time.monotonic() - start

    # must wait past the second file's quiet window, not return right after the first file
    assert elapsed >= 0.1
    assert (inbox / "b.jpg").exists()


def test_sort_inbox_ignores_unrecognized_files(tmp_path):
    inbox = tmp_path / "inbox"
    media_root = tmp_path / "media"
    inbox.mkdir()
    _touch(inbox / "readme.txt")

    moved = sort_inbox(inbox, media_root, room="bedroom")

    assert moved == []
    assert (inbox / "readme.txt").exists()
