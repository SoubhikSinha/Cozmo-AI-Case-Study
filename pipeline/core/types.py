from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Tier(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    LIDAR = "lidar"


@dataclass
class Intrinsics:
    fx: float
    fy: float
    cx: float
    cy: float


@dataclass
class Pose:
    """Camera-to-world 4x4 matrix, row-major."""

    matrix: list[list[float]]


@dataclass
class Frame:
    image_path: Path
    depth_path: Path | None = None
    confidence_path: Path | None = None
    pose: Pose | None = None
    intrinsics: Intrinsics | None = None
    timestamp: float | None = None
    source_index: int | None = None


@dataclass
class Capture:
    tier: Tier
    room_id: str
    frames: list[Frame] = field(default_factory=list)
    world_map_path: Path | None = None
    raw_source: Path | None = None
