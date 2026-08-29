from __future__ import annotations

from pathlib import Path

from pipeline.core.types import Capture, Frame, Tier

from .base import Adapter

_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}


class PhotoAdapter(Adapter):
    """One folder of 2-8 stills for one room. No depth, no poses."""

    def load(self, path: Path, room_id: str) -> Capture:
        images = sorted(p for p in Path(path).iterdir() if p.suffix.lower() in _EXTENSIONS)
        frames = [
            Frame(image_path=img, source_index=i) for i, img in enumerate(images)
        ]
        return Capture(tier=Tier.PHOTO, room_id=room_id, frames=frames, raw_source=Path(path))
