from __future__ import annotations

import argparse
import shutil
import time
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MEDIA_ROOT = REPO_ROOT / "media"

PHOTO_EXTS = {".jpg", ".jpeg", ".heic"}
VIDEO_EXTS = {".mp4", ".mov"}


def classify(path: Path) -> str | None:
    """Return 'photos', 'video', 'lidar', or None if unrecognized."""
    suffix = path.suffix.lower()
    if suffix in PHOTO_EXTS:
        return "photos"
    if suffix in VIDEO_EXTS:
        return "video"
    if suffix == ".zip" and _looks_like_lidar_zip(path):
        return "lidar"
    if path.is_dir() and _looks_like_lidar_dir(path):
        return "lidar"
    return None


def _looks_like_lidar_dir(path: Path) -> bool:
    return any(path.glob("frame_*.json")) or (path / "info.json").exists()


def _looks_like_lidar_zip(path: Path) -> bool:
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
    return any("frame_" in n and n.endswith(".json") for n in names) or any(
        n.endswith("info.json") for n in names
    )


def sort_inbox(inbox: Path, media_root: Path, room: str) -> list[tuple[Path, Path]]:
    """Move everything in inbox into media_root/<tier>/<room>/. Returns (src, dst) pairs."""
    moved: list[tuple[Path, Path]] = []

    for item in sorted(inbox.iterdir()):
        if item.name == ".gitkeep":
            continue

        tier = classify(item)
        if tier is None:
            continue

        dest_dir = media_root / tier / room
        dest_dir.mkdir(parents=True, exist_ok=True)

        if tier == "lidar" and item.suffix.lower() == ".zip":
            with zipfile.ZipFile(item) as zf:
                zf.extractall(dest_dir)
            item.unlink()
            moved.append((item, dest_dir))
        elif item.is_dir():
            dest = dest_dir / item.name
            shutil.move(str(item), str(dest))
            moved.append((item, dest))
        else:
            dest = dest_dir / item.name
            shutil.move(str(item), str(dest))
            moved.append((item, dest))

    return moved


def _snapshot(inbox: Path) -> set[tuple[str, float]]:
    return {(p.name, p.stat().st_mtime) for p in inbox.iterdir() if p.name != ".gitkeep"}


def wait_for_burst(inbox: Path, poll_seconds: float = 1.0, quiet_seconds: float = 3.0) -> None:
    """Block until inbox is non-empty and unchanged for quiet_seconds.

    Debounces AirDrop, which drops a burst's files over ~1-2s rather than
    atomically, so we don't prompt/sort mid-drop.
    """
    stable_since: float | None = None
    last_snapshot: set[tuple[str, float]] = set()

    while True:
        snapshot = _snapshot(inbox)
        now = time.time()

        if not snapshot:
            stable_since = None
        elif snapshot != last_snapshot:
            stable_since = now
        elif stable_since is not None and now - stable_since >= quiet_seconds:
            return

        last_snapshot = snapshot
        time.sleep(poll_seconds)


def _log_moves(moved: list[tuple[Path, Path]], media_root: Path) -> None:
    log_path = media_root / "sort_log.txt"
    with log_path.open("a") as log:
        for src, dst in moved:
            line = f"{src} -> {dst}"
            print(line)
            log.write(line + "\n")

    if not moved:
        print("Nothing to sort (inbox empty or no recognized files).")


def main() -> None:
    parser = argparse.ArgumentParser(prog="sort_media")
    parser.add_argument("--room", default=None, help="Room name/take, e.g. bedroom_take2")
    parser.add_argument("--inbox", type=Path, default=MEDIA_ROOT / "inbox")
    parser.add_argument("--media-root", type=Path, default=MEDIA_ROOT)
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch inbox for bursts, prompting for a room name after each one settles.",
    )
    args = parser.parse_args()

    if args.watch:
        print(f"Watching {args.inbox} for capture bursts (Ctrl+C to stop)...")
        while True:
            wait_for_burst(args.inbox)
            room = input("Room name for this burst (e.g. bedroom, bedroom_take2): ").strip()
            if not room:
                print("Room name required, skipping this burst.")
                continue
            moved = sort_inbox(args.inbox, args.media_root, room)
            _log_moves(moved, args.media_root)
        return

    room = args.room or input("Room name (e.g. bedroom, bedroom_take2): ").strip()
    if not room:
        raise SystemExit("Room name required.")

    moved = sort_inbox(args.inbox, args.media_root, room)
    _log_moves(moved, args.media_root)


if __name__ == "__main__":
    main()
