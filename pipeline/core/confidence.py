from __future__ import annotations

from .types import Tier


def measurement_ci(tier: Tier, method: str, raw_stats: dict) -> tuple[float, float]:
    """Return (low, high) confidence interval for a measurement.

    Every downstream measurement must call through here rather than
    hardcoding a tier-specific tolerance inline, so calibration lives
    in one place. Real formulas land once reconstruction produces
    real raw_stats to calibrate against:
      - LIDAR: sensor-error-based (depth noise model, pose covariance)
      - VIDEO: multi-view triangulation reprojection error
      - PHOTO: sparse-view geometric bound (widest)
    """
    raise NotImplementedError(f"CI method '{method}' not implemented for tier {tier}")
