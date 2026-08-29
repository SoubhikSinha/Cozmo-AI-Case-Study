from __future__ import annotations

from pathlib import Path

from pipeline.core.types import Capture, Frame, Tier

from .base import Adapter

# ponytail: fixed sample rate, tune once real footage/accuracy tradeoffs are measured
SAMPLE_EVERY_N_SECONDS = 0.5


class VideoAdapter(Adapter):
    """Handheld walkthrough clip for one room/property. No poses."""

    def load(self, path: Path, room_id: str) -> Capture:
        import cv2

        video = cv2.VideoCapture(str(path))
        fps = video.get(cv2.CAP_PROP_FPS) or 30.0
        step = max(1, round(fps * SAMPLE_EVERY_N_SECONDS))

        frames: list[Frame] = []
        frame_idx = 0
        out_dir = Path(path).with_suffix("").parent / f"{Path(path).stem}_frames"
        out_dir.mkdir(parents=True, exist_ok=True)

        while True:
            ok, image = video.read()
            if not ok:
                break
            if frame_idx % step == 0:
                out_path = out_dir / f"frame_{frame_idx:05d}.jpg"
                cv2.imwrite(str(out_path), image)
                frames.append(
                    Frame(
                        image_path=out_path,
                        timestamp=frame_idx / fps,
                        source_index=frame_idx,
                    )
                )
            frame_idx += 1
        video.release()

        return Capture(tier=Tier.VIDEO, room_id=room_id, frames=frames, raw_source=Path(path))
