from __future__ import annotations

from dataclasses import dataclass, field

# Part 2 gate thresholds, straight from the assessment doc.
OPENING_WIDTH_THRESHOLD_CM = 2.0
OPENING_MIN_PASS_FRACTION = 0.85
CEILING_HEIGHT_THRESHOLD_CM = 1.5
CEILING_REPEATABILITY_THRESHOLD_CM = 1.0
REPEATABILITY_ABS_THRESHOLD_CM = 1.0
REPEATABILITY_REL_THRESHOLD = 0.005  # 0.5% per wall
PHOTO_FOOTPRINT_TOLERANCE = 0.08
VIDEO_WALL_TOLERANCE = 0.03


@dataclass
class GateResult:
    gate_name: str
    passed: bool
    metric_description: str
    actual_value: float
    threshold: float
    detail: str = ""

    def to_markdown_row(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"| {self.gate_name} | {status} | {self.metric_description} | {self.actual_value:.3f} | {self.threshold:.3f} | {self.detail} |"


@dataclass
class BenchmarkReport:
    results: list[GateResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    def to_markdown(self) -> str:
        lines = [
            "| Gate | Status | Metric | Actual | Threshold | Detail |",
            "|---|---|---|---|---|---|",
        ]
        lines.extend(r.to_markdown_row() for r in self.results)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Opening widths: <=2cm error on >=85% of openings. A missed opening
# (ground truth exists, nothing predicted) and a phantom opening (predicted,
# no matching ground truth) both count as a miss for that pair.
# ---------------------------------------------------------------------------


def score_opening_widths(
    pairs: list[tuple[float | None, float | None]],
    threshold_cm: float = OPENING_WIDTH_THRESHOLD_CM,
    min_pass_fraction: float = OPENING_MIN_PASS_FRACTION,
) -> GateResult:
    if not pairs:
        return GateResult("opening_widths", False, "fraction within threshold", 0.0, min_pass_fraction, "no openings to score")

    passed_count = 0
    details = []
    for predicted, ground_truth in pairs:
        if predicted is None or ground_truth is None:
            details.append(f"miss (predicted={predicted}, ground_truth={ground_truth})")
            continue
        error = abs(predicted - ground_truth)
        ok = error <= threshold_cm
        passed_count += int(ok)
        details.append(f"{'ok' if ok else 'fail'} error={error:.2f}cm")

    fraction = passed_count / len(pairs)
    return GateResult(
        gate_name="opening_widths",
        passed=fraction >= min_pass_fraction,
        metric_description=f"fraction within {threshold_cm}cm",
        actual_value=fraction,
        threshold=min_pass_fraction,
        detail="; ".join(details),
    )


def match_openings_by_nearest_width(
    predicted_widths_cm: list[float], ground_truth_widths_cm: list[float]
) -> list[tuple[float | None, float | None]]:
    """Greedy nearest-width matching between predicted and ground-truth
    openings. Unmatched ground truth = missed opening; unmatched predicted =
    phantom opening. A real correspondence (e.g. by wall position) would be
    more accurate -- this is a documented, simple stand-in."""
    remaining_predicted = list(predicted_widths_cm)
    pairs: list[tuple[float | None, float | None]] = []

    for gt in ground_truth_widths_cm:
        if not remaining_predicted:
            pairs.append((None, gt))
            continue
        nearest = min(remaining_predicted, key=lambda p: abs(p - gt))
        remaining_predicted.remove(nearest)
        pairs.append((nearest, gt))

    for leftover in remaining_predicted:
        pairs.append((leftover, None))  # phantom opening

    return pairs


# ---------------------------------------------------------------------------
# Ceiling height: <=1.5cm error per room; repeatability spread <=1cm.
# ---------------------------------------------------------------------------


def score_ceiling_height(
    predicted_cm: float, ground_truth_cm: float, threshold_cm: float = CEILING_HEIGHT_THRESHOLD_CM
) -> GateResult:
    error = abs(predicted_cm - ground_truth_cm)
    return GateResult(
        gate_name="ceiling_height",
        passed=error <= threshold_cm,
        metric_description="absolute error (cm)",
        actual_value=error,
        threshold=threshold_cm,
        detail=f"predicted={predicted_cm:.2f}cm, ground_truth={ground_truth_cm:.2f}cm",
    )


def score_ceiling_repeatability(
    capture_a_cm: float, capture_b_cm: float, threshold_cm: float = CEILING_REPEATABILITY_THRESHOLD_CM
) -> GateResult:
    spread = abs(capture_a_cm - capture_b_cm)
    return GateResult(
        gate_name="ceiling_repeatability",
        passed=spread <= threshold_cm,
        metric_description="spread across captures (cm)",
        actual_value=spread,
        threshold=threshold_cm,
        detail=f"capture_a={capture_a_cm:.2f}cm, capture_b={capture_b_cm:.2f}cm",
    )


# ---------------------------------------------------------------------------
# Repeatability: two captures of the same room/tier agree within 1cm OR
# 0.5% per wall. Gate passes only if every paired wall satisfies the OR.
# ---------------------------------------------------------------------------


def score_repeatability_walls(
    walls_a_cm: list[float],
    walls_b_cm: list[float],
    abs_threshold_cm: float = REPEATABILITY_ABS_THRESHOLD_CM,
    rel_threshold: float = REPEATABILITY_REL_THRESHOLD,
) -> GateResult:
    if len(walls_a_cm) != len(walls_b_cm):
        return GateResult(
            "repeatability_walls", False, "wall count mismatch", float(len(walls_a_cm)), float(len(walls_b_cm)),
            f"captures produced different wall counts: {len(walls_a_cm)} vs {len(walls_b_cm)}",
        )

    worst_ratio = 0.0
    details = []
    for a, b in zip(walls_a_cm, walls_b_cm):
        diff = abs(a - b)
        rel_diff = diff / max(a, b, 1e-9)
        ok = diff <= abs_threshold_cm or rel_diff <= rel_threshold
        # "worst ratio" lets the actual_value show how far the worst wall is
        # from passing, normalized against whichever criterion is looser
        ratio = min(diff / abs_threshold_cm, rel_diff / rel_threshold)
        worst_ratio = max(worst_ratio, ratio)
        details.append(f"{'ok' if ok else 'fail'} diff={diff:.2f}cm ({rel_diff*100:.2f}%)")

    return GateResult(
        gate_name="repeatability_walls",
        passed=worst_ratio <= 1.0,
        metric_description="worst-wall ratio to threshold (<=1.0 passes)",
        actual_value=worst_ratio,
        threshold=1.0,
        detail="; ".join(details),
    )


# ---------------------------------------------------------------------------
# Photo-tier whole-property stitch: footprint within +/-8%.
# Video-tier wall lengths: within +/-3%.
# ---------------------------------------------------------------------------


def score_footprint_tolerance(
    predicted_area_m2: float, ground_truth_area_m2: float, tolerance_fraction: float = PHOTO_FOOTPRINT_TOLERANCE
) -> GateResult:
    rel_error = abs(predicted_area_m2 - ground_truth_area_m2) / max(ground_truth_area_m2, 1e-9)
    return GateResult(
        gate_name="photo_tier_footprint",
        passed=rel_error <= tolerance_fraction,
        metric_description="relative footprint error",
        actual_value=rel_error,
        threshold=tolerance_fraction,
        detail=f"predicted={predicted_area_m2:.2f}m2, ground_truth={ground_truth_area_m2:.2f}m2",
    )


def score_wall_lengths_pct(
    predicted_cm: list[float], ground_truth_cm: list[float], tolerance_fraction: float
) -> GateResult:
    if len(predicted_cm) != len(ground_truth_cm):
        return GateResult(
            "wall_lengths_pct", False, "wall count mismatch", float(len(predicted_cm)), float(len(ground_truth_cm)),
            f"predicted {len(predicted_cm)} walls, ground truth has {len(ground_truth_cm)}",
        )

    worst_rel_error = 0.0
    details = []
    for p, g in zip(predicted_cm, ground_truth_cm):
        rel_error = abs(p - g) / max(g, 1e-9)
        worst_rel_error = max(worst_rel_error, rel_error)
        details.append(f"predicted={p:.1f}cm ground_truth={g:.1f}cm err={rel_error*100:.2f}%")

    return GateResult(
        gate_name="wall_lengths_pct",
        passed=worst_rel_error <= tolerance_fraction,
        metric_description="worst-wall relative error",
        actual_value=worst_rel_error,
        threshold=tolerance_fraction,
        detail="; ".join(details),
    )


def score_video_tier_walls(predicted_cm: list[float], ground_truth_cm: list[float]) -> GateResult:
    result = score_wall_lengths_pct(predicted_cm, ground_truth_cm, VIDEO_WALL_TOLERANCE)
    result.gate_name = "video_tier_wall_lengths"
    return result
