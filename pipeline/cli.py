from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.adapters.lidar_adapter import LidarAdapter
from pipeline.adapters.photo_adapter import PhotoAdapter
from pipeline.adapters.video_adapter import VideoAdapter
from pipeline.core.serialize import capture_to_dict
from pipeline.core.types import Tier

_ADAPTERS = {
    Tier.PHOTO: PhotoAdapter(),
    Tier.VIDEO: VideoAdapter(),
    Tier.LIDAR: LidarAdapter(),
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    capture_cmd = sub.add_parser("capture", help="Load one room's raw input into a Capture")
    capture_cmd.add_argument("tier", choices=[t.value for t in Tier])
    capture_cmd.add_argument("path", type=Path)
    capture_cmd.add_argument("--room-id", required=True)
    capture_cmd.add_argument("--out", type=Path, default=None)

    args = parser.parse_args()

    if args.command == "capture":
        tier = Tier(args.tier)
        capture = _ADAPTERS[tier].load(args.path, args.room_id)
        payload = json.dumps(capture_to_dict(capture), indent=2)
        if args.out:
            args.out.write_text(payload)
        else:
            print(payload)


if __name__ == "__main__":
    main()
