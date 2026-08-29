from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any


def capture_to_dict(capture: Any) -> dict:
    def convert(obj):
        if dataclasses.is_dataclass(obj):
            return {
                f.name: convert(getattr(obj, f.name)) for f in dataclasses.fields(obj)
            }
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, list):
            return [convert(v) for v in obj]
        if hasattr(obj, "value"):  # Enum
            return obj.value
        return obj

    return convert(capture)
