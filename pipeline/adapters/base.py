from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pipeline.core.types import Capture


class Adapter(ABC):
    @abstractmethod
    def load(self, path: Path, room_id: str) -> Capture:
        """Normalize one tier's raw input for one room into a Capture."""
