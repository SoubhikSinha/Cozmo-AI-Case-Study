from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field


@dataclass
class DimensionComparison:
    dimension_name: str
    ground_truth: float
    our_value: float
    their_value: float

    @property
    def our_error(self) -> float:
        return abs(self.our_value - self.ground_truth)

    @property
    def their_error(self) -> float:
        return abs(self.their_value - self.ground_truth)

    @property
    def winner(self) -> str:
        if abs(self.our_error - self.their_error) < 1e-9:
            return "tie"
        return "ours" if self.our_error < self.their_error else "theirs"


@dataclass
class HeadToHeadReport:
    comparisons: list[DimensionComparison] = field(default_factory=list)

    @property
    def win_or_tie_fraction(self) -> float:
        """Fraction of shared dimensions where we beat or tied the
        competitor -- the assessment's actual pass bar is >=70% here."""
        if not self.comparisons:
            return 0.0
        wins_or_ties = sum(1 for c in self.comparisons if c.winner in ("ours", "tie"))
        return wins_or_ties / len(self.comparisons)

    def to_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["dimension_name", "ground_truth", "our_value", "our_error", "their_value", "their_error", "winner"]
        )
        for c in self.comparisons:
            writer.writerow(
                [
                    c.dimension_name,
                    f"{c.ground_truth:.2f}",
                    f"{c.our_value:.2f}",
                    f"{c.our_error:.2f}",
                    f"{c.their_value:.2f}",
                    f"{c.their_error:.2f}",
                    c.winner,
                ]
            )
        return buffer.getvalue()

    def to_markdown(self) -> str:
        lines = [
            "| Dimension | Ground Truth (cm) | Our Value | Our Error | Their Value | Their Error | Winner |",
            "|---|---|---|---|---|---|---|",
        ]
        for c in self.comparisons:
            lines.append(
                f"| {c.dimension_name} | {c.ground_truth:.2f} | {c.our_value:.2f} | {c.our_error:.2f} "
                f"| {c.their_value:.2f} | {c.their_error:.2f} | {c.winner} |"
            )
        lines.append("")
        lines.append(f"**Beat-or-tie rate: {self.win_or_tie_fraction * 100:.1f}%** of {len(self.comparisons)} shared dimensions.")
        return "\n".join(lines)


def build_report(dimensions: list[tuple[str, float, float, float]]) -> HeadToHeadReport:
    """dimensions: list of (name, ground_truth, our_value, their_value)."""
    return HeadToHeadReport(
        comparisons=[DimensionComparison(name, gt, ours, theirs) for name, gt, ours, theirs in dimensions]
    )
