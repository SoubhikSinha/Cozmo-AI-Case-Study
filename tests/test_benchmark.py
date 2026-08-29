from pipeline.benchmark import (
    match_openings_by_nearest_width,
    score_ceiling_height,
    score_ceiling_repeatability,
    score_footprint_tolerance,
    score_opening_widths,
    score_repeatability_walls,
    score_video_tier_walls,
    score_wall_lengths_pct,
)


def test_opening_width_3cm_error_fails_2cm_gate():
    result = score_opening_widths([(93.0, 90.0)])  # 3cm error
    assert result.passed is False


def test_opening_width_2cm_error_passes_gate_at_boundary():
    result = score_opening_widths([(92.0, 90.0)])  # exactly 2cm error
    assert result.passed is True


def test_opening_widths_pass_at_85_percent_threshold():
    # 6 of 7 within 2cm = 85.7% -> passes
    pairs = [(90.0, 90.0)] * 6 + [(90.0, 100.0)]
    result = score_opening_widths(pairs)
    assert result.passed is True
    assert abs(result.actual_value - 6 / 7) < 1e-9


def test_opening_widths_fail_below_85_percent_threshold():
    # 5 of 7 within 2cm = 71.4% -> fails
    pairs = [(90.0, 90.0)] * 5 + [(90.0, 100.0)] * 2
    result = score_opening_widths(pairs)
    assert result.passed is False


def test_missed_opening_counts_as_a_miss():
    result = score_opening_widths([(None, 90.0)])
    assert result.passed is False


def test_phantom_opening_counts_as_a_miss():
    result = score_opening_widths([(90.0, None)])
    assert result.passed is False


def test_match_openings_by_nearest_width_flags_missed_and_phantom():
    pairs = match_openings_by_nearest_width(predicted_widths_cm=[91.0], ground_truth_widths_cm=[90.0, 60.0])
    # one real match (91 vs 90), one missed (60 has no predicted counterpart)
    matched = [p for p in pairs if p[0] is not None and p[1] is not None]
    missed = [p for p in pairs if p[0] is None]
    assert len(matched) == 1
    assert len(missed) == 1


def test_ceiling_height_gate_boundary():
    assert score_ceiling_height(271.5, 270.0).passed is True  # exactly 1.5cm
    assert score_ceiling_height(272.0, 270.0).passed is False  # 2cm error


def test_ceiling_repeatability_gate():
    assert score_ceiling_repeatability(250.0, 250.9).passed is True
    assert score_ceiling_repeatability(250.0, 251.5).passed is False


def test_repeatability_walls_passes_via_absolute_threshold():
    # 400 vs 400.9 = 0.9cm diff, 0.225% rel -- absolute threshold (1cm) saves it
    result = score_repeatability_walls([400.0], [400.9])
    assert result.passed is True


def test_repeatability_walls_passes_via_relative_threshold():
    # a big wall where 1.5cm diff is still under 0.5% relatively
    result = score_repeatability_walls([1000.0], [1001.5])
    assert result.passed is True


def test_repeatability_walls_fails_when_neither_threshold_met():
    # small wall, 2cm diff = 1% relative -- fails both
    result = score_repeatability_walls([200.0], [202.0])
    assert result.passed is False


def test_repeatability_walls_mismatched_count_fails():
    result = score_repeatability_walls([400.0, 300.0], [400.0])
    assert result.passed is False


def test_photo_tier_footprint_within_8_percent_passes():
    result = score_footprint_tolerance(predicted_area_m2=10.7, ground_truth_area_m2=10.0)  # 7% over
    assert result.passed is True


def test_photo_tier_footprint_beyond_8_percent_fails():
    result = score_footprint_tolerance(predicted_area_m2=11.0, ground_truth_area_m2=10.0)  # 10% over
    assert result.passed is False


def test_video_tier_wall_lengths_within_3_percent_passes():
    result = score_video_tier_walls([412.0], [400.0])  # 3% over exactly
    assert result.passed is True


def test_video_tier_wall_lengths_beyond_3_percent_fails():
    result = score_video_tier_walls([420.0], [400.0])  # 5% over
    assert result.passed is False


def test_wall_lengths_pct_generic_helper_matches_video_tier_thresholds():
    generic = score_wall_lengths_pct([420.0], [400.0], tolerance_fraction=0.03)
    assert generic.passed is False
    assert generic.actual_value > 0.03
