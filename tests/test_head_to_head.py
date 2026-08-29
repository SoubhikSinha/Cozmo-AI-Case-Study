from pipeline.head_to_head import build_report


def test_winner_ours_when_our_error_is_smaller():
    report = build_report([("wall_a", 100.0, 101.0, 105.0)])  # our_error=1, their_error=5
    assert report.comparisons[0].winner == "ours"


def test_winner_theirs_when_their_error_is_smaller():
    report = build_report([("wall_a", 100.0, 108.0, 101.0)])  # our_error=8, their_error=1
    assert report.comparisons[0].winner == "theirs"


def test_winner_tie_when_errors_equal():
    report = build_report([("wall_a", 100.0, 103.0, 97.0)])  # our_error=3, their_error=3
    assert report.comparisons[0].winner == "tie"


def test_errors_computed_correctly():
    report = build_report([("ceiling", 250.0, 245.0, 260.0)])
    c = report.comparisons[0]
    assert c.our_error == 5.0
    assert c.their_error == 10.0


def test_win_or_tie_fraction_counts_ties_as_wins():
    dims = [
        ("a", 100.0, 101.0, 105.0),  # ours
        ("b", 100.0, 108.0, 101.0),  # theirs
        ("c", 100.0, 103.0, 97.0),  # tie
        ("d", 100.0, 100.5, 110.0),  # ours
    ]
    report = build_report(dims)
    # 3 of 4 are ours-or-tie -> 75%
    assert report.win_or_tie_fraction == 0.75


def test_win_or_tie_fraction_meets_70_percent_threshold_example():
    # 7 dimensions, exactly 5 ours-or-tie -> 71.4%, should pass a >=70% bar
    dims = [("d0", 100.0, 100.0, 100.0)] * 5 + [("d5", 100.0, 120.0, 100.0), ("d6", 100.0, 130.0, 100.0)]
    report = build_report(dims)
    assert report.win_or_tie_fraction >= 0.70


def test_empty_comparisons_gives_zero_fraction():
    report = build_report([])
    assert report.win_or_tie_fraction == 0.0


def test_csv_and_markdown_render_without_error():
    report = build_report([("wall_a", 100.0, 101.0, 105.0)])
    csv_text = report.to_csv()
    md_text = report.to_markdown()
    assert "wall_a" in csv_text
    assert "wall_a" in md_text
    assert "ours" in csv_text
    assert "Beat-or-tie rate" in md_text
