from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

from pipeline.schema import PropertyPlan, Room, Wall

# ponytail: loop-closure error is distributed linearly along the loop's path
# rather than solved via full pose-graph bundle adjustment. Real, explainable,
# and enough to demonstrate the ablation; upgrade path is g2o/GTSAM-style
# optimization once there are enough real multi-room captures to justify it.


@dataclass
class Connector:
    """Declares that wall_a on room_a is the same physical wall as wall_b on room_b."""

    room_a: str
    wall_a: str
    room_b: str
    wall_b: str


@dataclass
class _Transform:
    angle: float  # radians
    translation: np.ndarray  # shape (2,)

    def apply(self, point: tuple[float, float]) -> tuple[float, float]:
        c, s = math.cos(self.angle), math.sin(self.angle)
        x, y = point
        rotated = np.array([c * x - s * y, s * x + c * y])
        result = rotated + self.translation
        return (float(result[0]), float(result[1]))


def _wall_by_id(room: Room, wall_id: str) -> Wall:
    for wall in room.walls:
        if wall.id == wall_id:
            return wall
    raise ValueError(f"room {room.id} has no wall {wall_id}")


def _solve_rigid_transform(local_start, local_end, global_start, global_end) -> _Transform:
    """Rigid (rotation + translation, no scale) transform mapping local_start/end
    onto global_start/end -- the two-point closed-form solution."""
    local_vec = np.array(local_end) - np.array(local_start)
    global_vec = np.array(global_end) - np.array(global_start)
    angle = math.atan2(global_vec[1], global_vec[0]) - math.atan2(local_vec[1], local_vec[0])

    c, s = math.cos(angle), math.sin(angle)
    rotated_start = np.array([c * local_start[0] - s * local_start[1], s * local_start[0] + c * local_start[1]])
    translation = np.array(global_start) - rotated_start

    return _Transform(angle=angle, translation=translation)


def _build_graph(connectors: list[Connector]) -> dict[str, list[tuple[Connector, str]]]:
    graph: dict[str, list[tuple[Connector, str]]] = {}
    for c in connectors:
        graph.setdefault(c.room_a, []).append((c, c.room_b))
        graph.setdefault(c.room_b, []).append((c, c.room_a))
    return graph


def stitch_rooms(rooms: list[Room], connectors: list[Connector], drift_correction: bool = True) -> PropertyPlan:
    rooms_by_id = {r.id: r for r in rooms}
    graph = _build_graph(connectors)

    transforms: dict[str, _Transform] = {rooms[0].id: _Transform(angle=0.0, translation=np.zeros(2))}
    bfs_order: list[str] = [rooms[0].id]
    used_connectors: set[int] = set()
    parent_of: dict[str, str] = {}

    queue = deque([rooms[0].id])
    while queue:
        current_id = queue.popleft()
        for connector, neighbor_id in graph.get(current_id, []):
            if neighbor_id in transforms:
                continue

            # orient the connector as (placed room -> new room)
            if connector.room_a == current_id:
                parent_wall_id, child_wall_id = connector.wall_a, connector.wall_b
            else:
                parent_wall_id, child_wall_id = connector.wall_b, connector.wall_a

            parent_transform = transforms[current_id]
            parent_wall = _wall_by_id(rooms_by_id[current_id], parent_wall_id)
            global_start = parent_transform.apply(parent_wall.start)
            global_end = parent_transform.apply(parent_wall.end)

            child_wall = _wall_by_id(rooms_by_id[neighbor_id], child_wall_id)
            # shared wall is traversed in opposite winding by the other room
            transform = _solve_rigid_transform(
                child_wall.start, child_wall.end, global_end, global_start
            )

            transforms[neighbor_id] = transform
            parent_of[neighbor_id] = current_id
            bfs_order.append(neighbor_id)
            used_connectors.add(id(connector))
            queue.append(neighbor_id)

    if drift_correction:
        _apply_loop_closure_correction(rooms_by_id, connectors, used_connectors, transforms, bfs_order)

    placed_rooms: list[Room] = []
    for room in rooms:
        transform = transforms[room.id]
        new_walls = [
            Wall(id=w.id, start=transform.apply(w.start), end=transform.apply(w.end), length=w.length)
            for w in room.walls
        ]
        placed_rooms.append(
            Room(
                id=room.id,
                name=room.name,
                capture=room.capture,
                walls=new_walls,
                ceiling_height=room.ceiling_height,
                floor_area=room.floor_area,
                openings=room.openings,
                damage_regions=room.damage_regions,
                concealed_flags=room.concealed_flags,
                scope_items=room.scope_items,
            )
        )

    adjacency = [(c.room_a, c.room_b, f"{c.wall_a}|{c.wall_b}") for c in connectors]
    return PropertyPlan(property_id="stitched", rooms=placed_rooms, adjacency=adjacency)


def _loop_closure_error(rooms_by_id, connector: Connector, transforms: dict[str, _Transform]) -> np.ndarray:
    wall_a = _wall_by_id(rooms_by_id[connector.room_a], connector.wall_a)
    wall_b = _wall_by_id(rooms_by_id[connector.room_b], connector.wall_b)
    a_start = np.array(transforms[connector.room_a].apply(wall_a.start))
    a_end = np.array(transforms[connector.room_a].apply(wall_a.end))
    b_start = np.array(transforms[connector.room_b].apply(wall_b.start))
    b_end = np.array(transforms[connector.room_b].apply(wall_b.end))
    # b's wall should coincide with a's wall, reversed
    return ((a_start - b_end) + (a_end - b_start)) / 2


def _apply_loop_closure_correction(rooms_by_id, connectors, used_connectors, transforms, bfs_order) -> None:
    loop_edges = [c for c in connectors if id(c) not in used_connectors]
    for connector in loop_edges:
        error = _loop_closure_error(rooms_by_id, connector, transforms)
        # ponytail: distributes across the whole BFS order, which is only
        # correct when the room graph is a single chain-plus-one-loop (true
        # for the assessment's multi-room capture case). A graph with
        # multiple independent loops or branches needs per-loop path
        # isolation -- not built, since every real capture here is a
        # simple walkthrough loop.
        n = len(bfs_order) - 1
        if n <= 0:
            continue
        for i, room_id in enumerate(bfs_order):
            if i == 0:
                continue
            fraction = i / n
            transforms[room_id].translation = transforms[room_id].translation + error * fraction


def total_loop_closure_error(rooms: list[Room], connectors: list[Connector], transforms_from: PropertyPlan) -> float:
    """Sum of residual gap distances at every connector, using the room
    positions already baked into a stitched PropertyPlan. Used to compare
    drift_correction on vs off."""
    rooms_by_id = {r.id: r for r in transforms_from.rooms}
    total = 0.0
    for c in connectors:
        wall_a = _wall_by_id(rooms_by_id[c.room_a], c.wall_a)
        wall_b = _wall_by_id(rooms_by_id[c.room_b], c.wall_b)
        gap = (np.array(wall_a.start) - np.array(wall_b.end)) + (np.array(wall_a.end) - np.array(wall_b.start))
        total += float(np.linalg.norm(gap))
    return total


def check_no_overlaps(plan: PropertyPlan) -> list[tuple[str, str]]:
    overlapping = []
    footprints = {r.id: [w.start for w in r.walls] for r in plan.rooms}
    ids = list(footprints)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if _polygons_overlap(footprints[ids[i]], footprints[ids[j]]):
                overlapping.append((ids[i], ids[j]))
    return overlapping


def _polygons_overlap(poly_a: list[tuple[float, float]], poly_b: list[tuple[float, float]]) -> bool:
    """Separating axis theorem for two convex polygons."""
    for polygon in (poly_a, poly_b):
        for i in range(len(polygon)):
            p1, p2 = np.array(polygon[i]), np.array(polygon[(i + 1) % len(polygon)])
            edge = p2 - p1
            axis = np.array([-edge[1], edge[0]])
            norm = np.linalg.norm(axis)
            if norm < 1e-9:
                continue
            axis = axis / norm

            proj_a = [np.dot(axis, np.array(p)) for p in poly_a]
            proj_b = [np.dot(axis, np.array(p)) for p in poly_b]
            if max(proj_a) <= min(proj_b) or max(proj_b) <= min(proj_a):
                return False  # found a separating axis
    return True
