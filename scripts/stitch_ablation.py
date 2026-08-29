"""Demonstrates the drift-correction ablation on a hardcoded 3-room loop.

Not yet wired to real captured rooms -- connector-manifest authoring for
real multi-room captures is future work, and real rooms' wall geometry
isn't reliable enough yet (see the open LiDAR-noise and opening-detection
issues) to stitch meaningfully. This demonstrates the stitching math itself.
"""
from __future__ import annotations

import numpy as np

from pipeline.core.types import Tier
from pipeline.schema import Capture, Measurement, Room, Wall
from pipeline.stitching import Connector, stitch_rooms

SIDE_CM = 400.0


def _square_room(room_id: str) -> Room:
    corners = [(0.0, 0.0), (SIDE_CM, 0.0), (SIDE_CM, SIDE_CM), (0.0, SIDE_CM)]
    length = Measurement(value=SIDE_CM, confidence_interval=(SIDE_CM - 1, SIDE_CM + 1))
    walls = [
        Wall(id=f"wall-{i}", start=corners[i], end=corners[(i + 1) % 4], length=length) for i in range(4)
    ]
    return Room(
        id=room_id,
        name=room_id,
        capture=Capture(tier=Tier.LIDAR, device="demo", room_id=room_id),
        walls=walls,
        ceiling_height=Measurement(value=250.0, confidence_interval=(249.0, 251.0)),
        floor_area=Measurement(value=16.0, confidence_interval=(15.9, 16.1), unit="m2"),
    )


def _residual_gap(plan, connector: Connector) -> float:
    rooms_by_id = {r.id: r for r in plan.rooms}
    wall_a = next(w for w in rooms_by_id[connector.room_a].walls if w.id == connector.wall_a)
    wall_b = next(w for w in rooms_by_id[connector.room_b].walls if w.id == connector.wall_b)
    gap = (np.array(wall_a.start) - np.array(wall_b.end)) + (np.array(wall_a.end) - np.array(wall_b.start))
    return float(np.linalg.norm(gap))


def main() -> None:
    rooms = [_square_room("A"), _square_room("B"), _square_room("C")]
    tree_connectors = [
        Connector(room_a="A", wall_a="wall-1", room_b="B", wall_b="wall-3"),
        Connector(room_a="A", wall_a="wall-2", room_b="C", wall_b="wall-3"),
    ]
    loop_connector = Connector(room_a="B", wall_a="wall-1", room_b="C", wall_b="wall-1")
    connectors = tree_connectors + [loop_connector]

    for label, drift_correction in [("OFF", False), ("ON", True)]:
        plan = stitch_rooms(rooms, connectors, drift_correction=drift_correction)
        print(f"\n=== drift correction {label} ===")
        for room in plan.rooms:
            corners = ", ".join(f"({w.start[0]:.1f}, {w.start[1]:.1f})" for w in room.walls)
            print(f"  {room.id}: {corners}")
        gap = _residual_gap(plan, loop_connector)
        print(f"  loop-closure residual gap: {gap:.2f} cm")


if __name__ == "__main__":
    main()
