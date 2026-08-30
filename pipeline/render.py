from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.schema import OpeningType, PropertyPlan, Room, Wall


def _cm_to_feet_inches(value_cm: float) -> str:
    total_inches = value_cm / 2.54
    feet, inches = divmod(total_inches, 12)
    return f"{int(feet)}' {round(inches)}\""


def _outward_normal(wall: Wall, centroid: np.ndarray) -> np.ndarray:
    direction = np.array(wall.end) - np.array(wall.start)
    normal = np.array([-direction[1], direction[0]])
    norm = np.linalg.norm(normal)
    if norm < 1e-9:
        return np.array([0.0, 0.0])
    normal = normal / norm
    midpoint = (np.array(wall.start) + np.array(wall.end)) / 2
    if np.dot(normal, midpoint - centroid) < 0:
        normal = -normal
    return normal


def _dimension_offset(corners: np.ndarray) -> float:
    span = corners.max(axis=0) - corners.min(axis=0)
    return max(float(span.min()) * 0.12, 25.0)


def _draw_dimension_line(ax, start: np.ndarray, end: np.ndarray, normal: np.ndarray, offset: float, label: str) -> None:
    d_start, d_end = start + normal * offset, end + normal * offset
    # extension lines from the wall corners out to the dimension line
    ax.plot(*zip(start, d_start), color="gray", linewidth=0.6, linestyle="--", zorder=2)
    ax.plot(*zip(end, d_end), color="gray", linewidth=0.6, linestyle="--", zorder=2)
    # dimension line with tick marks at both ends
    ax.plot(*zip(d_start, d_end), color="black", linewidth=0.8, zorder=2)
    tick = normal[::-1] * np.array([1, -1]) * (offset * 0.15)
    for p in (d_start, d_end):
        ax.plot(*zip(p - tick, p + tick), color="black", linewidth=0.8, zorder=2)

    mid = (d_start + d_end) / 2
    angle = float(np.degrees(np.arctan2((end - start)[1], (end - start)[0])))
    if angle > 90 or angle < -90:
        angle += 180
    ax.text(
        mid[0], mid[1], label, ha="center", va="center", fontsize=8, color="black",
        rotation=angle, rotation_mode="anchor", zorder=5,
        bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.85),
    )


def _render_room(ax, room: Room) -> None:
    import matplotlib.patches as mpatches

    corners = np.array([w.start for w in room.walls])
    centroid = corners.mean(axis=0)
    dim_offset = _dimension_offset(corners)

    # filled interior, like a real floor plan rather than a bare outline
    ax.add_patch(mpatches.Polygon(corners, closed=True, facecolor="#f2f2f2", edgecolor="none", zorder=1))

    for wall in room.walls:
        start, end = np.array(wall.start), np.array(wall.end)
        opening_here = next((o for o in room.openings if o.wall_id == wall.id), None)

        if opening_here is None:
            ax.plot(*zip(start, end), color="black", linewidth=5, solid_capstyle="projecting", zorder=2)
        else:
            # draw the wall with a gap at the opening, plus a door-swing arc
            direction = end - start
            wall_len = np.linalg.norm(direction)
            unit = direction / wall_len if wall_len > 0 else direction
            gap_half = (opening_here.width.value / 2) / wall_len if wall_len > 0 else 0
            center_t = opening_here.position_on_wall
            gap_start = start + direction * max(center_t - gap_half, 0)
            gap_end = start + direction * min(center_t + gap_half, 1)

            ax.plot(*zip(start, gap_start), color="black", linewidth=5, solid_capstyle="projecting", zorder=2)
            ax.plot(*zip(gap_end, end), color="black", linewidth=5, solid_capstyle="projecting", zorder=2)

            if opening_here.type == OpeningType.DOOR:
                radius = float(np.linalg.norm(gap_end - gap_start))
                angle = float(np.degrees(np.arctan2(unit[1], unit[0])))
                arc = mpatches.Arc(
                    gap_start, 2 * radius, 2 * radius, angle=angle, theta1=0, theta2=90,
                    color="saddlebrown", linewidth=1.5, zorder=2,
                )
                ax.add_patch(arc)
                ax.plot(*zip(gap_start, gap_start + unit[::-1] * [-1, 1] * radius), color="saddlebrown", linewidth=1.5, zorder=2)
            else:
                mid = (gap_start + gap_end) / 2
                normal = _outward_normal(wall, centroid) * 4
                ax.plot(*zip(mid - normal, mid + normal), color="steelblue", linewidth=3, zorder=3)

            # opening width label, offset inward (toward room interior) so it
            # doesn't collide with the wall-length dimension line outside
            opening_mid = (gap_start + gap_end) / 2
            inward = -_outward_normal(wall, centroid)
            label_pos = opening_mid + inward * (dim_offset * 0.35)
            opening_label = f"{opening_here.width.value:.0f}cm ({_cm_to_feet_inches(opening_here.width.value)})"
            ax.text(
                label_pos[0], label_pos[1], opening_label, ha="center", va="center",
                fontsize=7, color="saddlebrown", zorder=5,
                bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.85),
            )

        # dimension line + label, offset outward from the wall
        normal = _outward_normal(wall, centroid)
        label = f"{wall.length.value:.0f}cm ({_cm_to_feet_inches(wall.length.value)})"
        _draw_dimension_line(ax, start, end, normal, dim_offset, label)

    area_label = f"{room.name}\n{room.floor_area.value:.2f} {room.floor_area.unit}"
    ax.text(centroid[0], centroid[1], area_label, ha="center", va="center", fontsize=10, fontweight="bold", zorder=4)


def render_plan(plan: PropertyPlan, out_path: Path) -> None:
    """Top-down rendered floor plan, poly.cam/magicplan style: filled room
    outlines with real wall thickness, dimension labels per wall (cm and
    feet-inches), door-swing arcs / window ticks at detected openings, and
    room name + floor area centered in each room."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 9))

    for room in plan.rooms:
        _render_room(ax, room)

    ax.set_aspect("equal")
    ax.set_xlabel("cm")
    ax.set_ylabel("cm")
    ax.set_title(f"Floor plan: {plan.property_id}")
    ax.margins(0.2)
    ax.autoscale_view()

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
