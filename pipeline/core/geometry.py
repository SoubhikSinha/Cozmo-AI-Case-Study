from __future__ import annotations

import numpy as np


def confidence_interval(value: float, relative_width: float, min_abs: float) -> tuple[float, float]:
    """Shared CI helper: half-width is the larger of a relative fraction of
    the value or a minimum absolute floor, so small values don't get a
    vanishingly tight (falsely confident) interval."""
    half = max(value * relative_width, min_abs) / 2
    return (round(value - half, 3), round(value + half, 3))


def load_depth_meters(depth_path) -> np.ndarray:
    """Load a depth PNG (assumed uint16 millimeters, the 3D Scanner App
    convention) as a float meters array."""
    import cv2

    raw = cv2.imread(str(depth_path), cv2.IMREAD_UNCHANGED)
    if raw is None:
        return np.zeros((0, 0))
    return raw.astype(np.float64) / 1000.0
