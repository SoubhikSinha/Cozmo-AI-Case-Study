from __future__ import annotations

import json
from pathlib import Path

from pipeline.core.types import Capture, Frame, Intrinsics, Pose, Tier

from .base import Adapter


class LidarAdapter(Adapter):
    """3D Scanner App 'All Data' export directory for one room.

    Expects per-frame frame_NNNNN.json (cameraPoseARFrame, intrinsics),
    frame_NNNNN.jpg, depth_NNNNN.png, conf_NNNNN.png, plus info.json
    and world_map.arkit at the export root.
    """

    def load(self, path: Path, room_id: str) -> Capture:
        root = Path(path)
        frames: list[Frame] = []

        for meta_path in sorted(root.glob("frame_*.json")):
            index_str = meta_path.stem.split("_")[1]
            meta = json.loads(meta_path.read_text())

            pose = None
            if "cameraPoseARFrame" in meta:
                m = meta["cameraPoseARFrame"]
                pose = Pose(matrix=[m[0:4], m[4:8], m[8:12], m[12:16]])

            intrinsics = None
            if "intrinsics" in meta:
                k = meta["intrinsics"]
                intrinsics = Intrinsics(fx=k[0], fy=k[4], cx=k[2], cy=k[5])

            image_path = root / f"frame_{index_str}.jpg"
            depth_path = root / f"depth_{index_str}.png"
            conf_path = root / f"conf_{index_str}.png"

            frames.append(
                Frame(
                    image_path=image_path,
                    depth_path=depth_path if depth_path.exists() else None,
                    confidence_path=conf_path if conf_path.exists() else None,
                    pose=pose,
                    intrinsics=intrinsics,
                    timestamp=meta.get("time"),
                    source_index=int(index_str),
                )
            )

        world_map = root / "world_map.arkit"
        return Capture(
            tier=Tier.LIDAR,
            room_id=room_id,
            frames=frames,
            world_map_path=world_map if world_map.exists() else None,
            raw_source=root,
        )
