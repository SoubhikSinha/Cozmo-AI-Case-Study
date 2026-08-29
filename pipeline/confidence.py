from __future__ import annotations

import math

from pipeline.core.types import Tier

# ponytail: the per-tier base error priors below are still hand-set constants
# (iPhone LiDAR depth-sensor spec noise, typical handheld-SfM triangulation
# error, monocular-photogrammetry literature) -- what's NOT hardcoded is the
# actual interval WIDTH a given measurement gets: that's computed from how
# many real samples (depth points / video frames / photos) backed it, via
# sqrt(N) averaging. Two measurements at the same tier get different CIs if
# they were backed by different sample counts. Upgrade path: replace the
# base priors with values calibrated against the benchmark's laser ground
# truth once it exists.

_BASE_RELATIVE_ERROR = {
    Tier.LIDAR: 0.02,  # ~2%: iPhone LiDAR depth-sensor noise floor
    Tier.VIDEO: 0.20,  # handheld walkthrough, no direct depth
    Tier.PHOTO: 0.45,  # 2-8 sparse stills, no motion or depth cue at all
}

_MIN_RELATIVE_ERROR = {
    Tier.LIDAR: 0.005,
    Tier.VIDEO: 0.05,
    Tier.PHOTO: 0.20,
}

_MIN_ABS_CM = {
    Tier.LIDAR: 0.5,
    Tier.VIDEO: 3.0,
    Tier.PHOTO: 8.0,
}


def measurement_ci(tier: Tier, value: float, sample_count: int, unit: str = "cm") -> tuple[float, float]:
    """Confidence interval for one measurement, computed from how many
    independent samples (LiDAR depth points, video frames, photo images)
    actually informed it.

    More samples -> tighter interval (sqrt(N) averaging), floored at a
    tier-specific minimum relative/absolute error since no amount of
    averaging beats the sensor's or method's fundamental noise floor.
    """
    n = max(1, sample_count)
    base = _BASE_RELATIVE_ERROR[tier]
    floor = _MIN_RELATIVE_ERROR[tier]
    relative_error = max(base / math.sqrt(n), floor)

    min_abs = _MIN_ABS_CM[tier]
    if unit == "m2":
        min_abs = (min_abs / 100) ** 2
    elif unit == "cm2":
        min_abs = min_abs**2

    half_width = max(abs(value) * relative_error, min_abs) / 2
    return (round(value - half_width, 3), round(value + half_width, 3))
