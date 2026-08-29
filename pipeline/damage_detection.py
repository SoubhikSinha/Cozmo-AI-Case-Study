from __future__ import annotations

import numpy as np

from pipeline.core.geometry import confidence_interval, load_depth_meters
from pipeline.core.types import Capture, Frame, Tier
from pipeline.damage_taxonomy import DamageClass, classify_severity
from pipeline.schema import DamageRegion, Measurement, Room

# ponytail: HSV color thresholds and crack aspect-ratio heuristics, not a
# trained model or VLM -- a real damage classifier (a chosen vision model
# run against DAMAGE_CLASS_DESCRIPTIONS) is future work once that model is
# picked. These are a documented starting point: real enough to test
# rule-firing logic against staged mock imagery, not calibrated against
# real photos yet -- color thresholds still confuse wood furniture/skin
# tones with water stains, and the assessment's own framing acknowledges
# this is a hard problem the whole field struggled with. Upgrade path:
# swap _detect_color_stains/_detect_cracks for a model call; detect_damage's
# signature and DamageRegion output stay the same either way.
#
# ponytail: thresholds below are relative to image area/dimensions, not
# fixed pixel counts -- verified against a real ~1800-frame LiDAR capture,
# where fixed-pixel thresholds (150px stain, 40px crack on a 1920x1440
# image) let through 200+ false positives per frame (54,609 total on one
# room) because ordinary photo texture and JPEG noise trivially clear a
# small fixed pixel count on a multi-megapixel image.

_MIN_STAIN_AREA_FRACTION = 0.01  # 1% of the frame's pixel area
_MIN_CRACK_AREA_FRACTION = 0.001
_CRACK_MIN_ASPECT_RATIO = 8.0
_ASSUMED_PHOTO_FRAME_WIDTH_M = 2.5  # no depth on photo/video tiers -- rough scale only

_STAIN_HSV_RANGES: dict[DamageClass, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    DamageClass.WATER: ((10, 60, 40), (30, 255, 200)),
    DamageClass.MOLD: ((35, 40, 20), (90, 255, 120)),
}


def detect_damage(room: Room, capture: Capture) -> list[DamageRegion]:
    """Runs per-frame stain/crack detection, then deduplicates to at most
    one region per (surface, damage_class): the same physical damage shows
    up in many frames as the camera passes it, so keeping every frame's hit
    would report the same spot dozens of times. Keeping only the
    largest-area hit per surface+class also bounds total output to a small,
    explainable number regardless of how noisy any single frame is --
    "confident garbage on thin input caps your score," so fewer, stronger
    candidates beats a flood of duplicates."""
    best_by_key: dict[tuple[str, DamageClass], DamageRegion] = {}

    for index, frame in enumerate(capture.frames):
        import cv2

        image = cv2.imread(str(frame.image_path))
        if image is None:
            continue

        surface_id = _surface_for_frame(room, frame, capture.tier) or f"frame-{index}"
        scale = _area_scale_cm2_per_px(frame, capture.tier, image.shape)

        region_id_prefix = f"damage-{index}"
        candidates = _detect_color_stains(image, surface_id, region_id_prefix, scale) + _detect_cracks(
            image, surface_id, region_id_prefix, scale
        )
        for region in candidates:
            key = (region.surface_id, region.damage_class)
            current_best = best_by_key.get(key)
            if current_best is None or region.extent_area.value > current_best.extent_area.value:
                best_by_key[key] = region

    return list(best_by_key.values())


def _surface_for_frame(room: Room, frame: Frame, tier: Tier) -> str | None:
    """Best-effort wall attribution for LiDAR frames (real geometry
    available); Photo/Video have no pose, so surface attribution falls back
    to a frame index elsewhere (documented limitation, not guessed)."""
    if tier != Tier.LIDAR or frame.pose is None or not room.walls:
        return None

    centroid = np.mean([w.start for w in room.walls], axis=0)
    matrix = np.array(frame.pose.matrix)
    forward = matrix[:3, 2]
    forward_xz = np.array([forward[0], forward[2]])
    norm = np.linalg.norm(forward_xz)
    if norm < 1e-6:
        return None
    forward_xz = forward_xz / norm

    best_wall_id, best_dot = None, 0.5  # minimum alignment to attribute confidently
    for wall in room.walls:
        direction = np.array(wall.end) - np.array(wall.start)
        wall_normal = np.array([-direction[1], direction[0]])
        wall_normal_norm = np.linalg.norm(wall_normal)
        if wall_normal_norm < 1e-9:
            continue
        wall_normal = wall_normal / wall_normal_norm
        midpoint = (np.array(wall.start) + np.array(wall.end)) / 2
        if np.dot(wall_normal, midpoint - centroid) < 0:
            wall_normal = -wall_normal

        dot = float(np.dot(forward_xz, wall_normal))
        if dot > best_dot:
            best_dot, best_wall_id = dot, wall.id

    return best_wall_id


def _area_scale_cm2_per_px(frame: Frame, tier: Tier, image_shape: tuple) -> tuple[str, float]:
    """Returns ('depth', frame) if per-pixel real-world scale can be
    computed from LiDAR depth, else ('flat', cm2_per_px) using a rough
    fixed assumption for tiers without depth."""
    if tier == Tier.LIDAR and frame.depth_path and frame.intrinsics:
        return ("depth", frame)

    height, width = image_shape[:2]
    assumed_width_cm = _ASSUMED_PHOTO_FRAME_WIDTH_M * 100
    cm_per_px = assumed_width_cm / width
    return ("flat", cm_per_px * cm_per_px)


def _pixel_area_to_cm2(mask: np.ndarray, scale) -> float:
    kind, value = scale
    pixel_count = int(np.count_nonzero(mask))
    if kind == "flat":
        return pixel_count * value

    frame = value
    depth_img = load_depth_meters(frame.depth_path)
    if depth_img.size == 0 or pixel_count == 0:
        return 0.0
    ys, xs = np.where(mask)
    ys = np.clip(ys, 0, depth_img.shape[0] - 1)
    xs = np.clip(xs, 0, depth_img.shape[1] - 1)
    depths = depth_img[ys, xs]
    depths = depths[(depths > 0.1) & (depths < 10.0)]
    if len(depths) == 0:
        return 0.0
    avg_depth = float(np.mean(depths))
    # one pixel spans ~depth/fx meters horizontally, depth/fy vertically
    per_pixel_area_m2 = (avg_depth / frame.intrinsics.fx) * (avg_depth / frame.intrinsics.fy)
    return pixel_count * per_pixel_area_m2 * 10000  # m2 -> cm2


def _detect_color_stains(image, surface_id: str, id_prefix: str, scale) -> list[DamageRegion]:
    import cv2

    image_area = image.shape[0] * image.shape[1]
    min_area_px = image_area * _MIN_STAIN_AREA_FRACTION

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    regions = []
    for damage_class, (lo, hi) in _STAIN_HSV_RANGES.items():
        mask = cv2.inRange(hsv, np.array(lo), np.array(hi))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for i, contour in enumerate(contours):
            if cv2.contourArea(contour) < min_area_px:
                continue
            blob_mask = np.zeros(mask.shape, dtype=np.uint8)
            cv2.drawContours(blob_mask, [contour], -1, 255, thickness=cv2.FILLED)
            area_cm2 = _pixel_area_to_cm2(blob_mask > 0, scale)
            if area_cm2 <= 0:
                continue
            regions.append(_make_region(f"{id_prefix}-{damage_class.value}-{i}", surface_id, damage_class, area_cm2))
    return regions


def _detect_cracks(image, surface_id: str, id_prefix: str, scale) -> list[DamageRegion]:
    import cv2

    image_area = image.shape[0] * image.shape[1]
    min_area_px = image_area * _MIN_CRACK_AREA_FRACTION

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)  # suppresses fine texture/JPEG noise before edge detection
    edges = cv2.Canny(blurred, 100, 200)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area < min_area_px:
            continue
        _, (w, h), _ = cv2.minAreaRect(contour)
        short, long_ = sorted([max(w, 1e-6), max(h, 1e-6)])
        if long_ / short < _CRACK_MIN_ASPECT_RATIO:
            continue

        blob_mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(blob_mask, [contour], -1, 255, thickness=cv2.FILLED)
        area_cm2 = _pixel_area_to_cm2(blob_mask > 0, scale)
        if area_cm2 <= 0:
            continue
        regions.append(_make_region(f"{id_prefix}-structural-{i}", surface_id, DamageClass.STRUCTURAL, area_cm2))
    return regions


def _make_region(region_id: str, surface_id: str, damage_class: DamageClass, area_cm2: float) -> DamageRegion:
    return DamageRegion(
        id=region_id,
        surface_id=surface_id,
        damage_class=damage_class,
        severity=classify_severity(area_cm2),
        extent_area=Measurement(
            value=round(area_cm2, 1),
            confidence_interval=confidence_interval(area_cm2, relative_width=0.4, min_abs=20.0),
            unit="cm2",
        ),
    )
