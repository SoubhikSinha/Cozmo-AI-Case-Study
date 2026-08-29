from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.schema import PropertyPlan


def render_plan(plan: PropertyPlan, out_path: Path) -> None:
    """Top-down rendered floor plan, poly.cam/magicplan style: room outlines,
    doors/windows marked on their walls, room names labeled."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 8))

    for room in plan.rooms:
        xs = [w.start[0] for w in room.walls] + [room.walls[0].start[0]]
        ys = [w.start[1] for w in room.walls] + [room.walls[0].start[1]]
        ax.plot(xs, ys, marker="o", linewidth=2)

        cx, cy = sum(xs[:-1]) / len(xs[:-1]), sum(ys[:-1]) / len(ys[:-1])
        ax.text(cx, cy, room.name, ha="center", va="center", fontsize=9)

        for opening in room.openings:
            wall = next((w for w in room.walls if w.id == opening.wall_id), None)
            if wall is None:
                continue
            start, end = np.array(wall.start), np.array(wall.end)
            mid = start + (end - start) * opening.position_on_wall
            ax.plot(mid[0], mid[1], marker="s", color="red", markersize=8)

    ax.set_aspect("equal")
    ax.set_xlabel("cm")
    ax.set_ylabel("cm")
    ax.set_title(f"Floor plan: {plan.property_id}")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
