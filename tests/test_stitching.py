import numpy as np

from pipeline.core.types import Tier
from pipeline.schema import Capture, Measurement, Room, Wall
from pipeline.stitching import Connector, check_no_overlaps, stitch_rooms

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
        capture=Capture(tier=Tier.LIDAR, device="test", room_id=room_id),
        walls=walls,
        ceiling_height=Measurement(value=250.0, confidence_interval=(249.0, 251.0)),
        floor_area=Measurement(value=16.0, confidence_interval=(15.9, 16.1), unit="m2"),
    )


def _wall_start(room, wall_id) -> np.ndarray:
    return np.array(next(w for w in room.walls if w.id == wall_id).start)


def test_three_rooms_in_a_line_place_at_expected_offsets_with_no_overlap():
    room_a, room_b, room_c = _square_room("A"), _square_room("B"), _square_room("C")
    connectors = [
        Connector(room_a="A", wall_a="wall-1", room_b="B", wall_b="wall-3"),
        Connector(room_a="B", wall_a="wall-1", room_b="C", wall_b="wall-3"),
    ]

    plan = stitch_rooms([room_a, room_b, room_c], connectors)
    placed = {r.id: r for r in plan.rooms}

    # A stays at the origin (anchor)
    assert np.allclose(_wall_start(placed["A"], "wall-0"), (0.0, 0.0))
    # B is shifted one room-width east of A
    assert np.allclose(_wall_start(placed["B"], "wall-0"), (SIDE_CM, 0.0))
    # C is shifted two room-widths east of A
    assert np.allclose(_wall_start(placed["C"], "wall-0"), (2 * SIDE_CM, 0.0))

    assert check_no_overlaps(plan) == []


def test_drift_correction_reduces_loop_closure_gap():
    # Hub topology: A connects directly to both B (east) and C (north), so
    # BFS always uses those two edges as the spanning tree regardless of
    # dict iteration order, leaving the B-C connector as the one genuine
    # loop-closure edge to test against.
    room_a, room_b, room_c = _square_room("A"), _square_room("B"), _square_room("C")
    connectors = [
        Connector(room_a="A", wall_a="wall-1", room_b="B", wall_b="wall-3"),
        Connector(room_a="A", wall_a="wall-2", room_b="C", wall_b="wall-3"),
    ]
    # Declared loop-closure claim between the two leaves -- B and C end up
    # nowhere near each other once placed via the hub, so this connector's
    # implied wall correspondence is inherently unsatisfied by a nonzero
    # amount, exactly like real accumulated drift on a walkthrough loop.
    loop_connector = Connector(room_a="B", wall_a="wall-1", room_b="C", wall_b="wall-1")

    plan_off = stitch_rooms([room_a, room_b, room_c], connectors + [loop_connector], drift_correction=False)
    plan_on = stitch_rooms([room_a, room_b, room_c], connectors + [loop_connector], drift_correction=True)

    gap_off = _residual_gap(plan_off, loop_connector)
    gap_on = _residual_gap(plan_on, loop_connector)

    assert gap_on < gap_off


def _residual_gap(plan, connector) -> float:
    rooms_by_id = {r.id: r for r in plan.rooms}
    wall_a = next(w for w in rooms_by_id[connector.room_a].walls if w.id == connector.wall_a)
    wall_b = next(w for w in rooms_by_id[connector.room_b].walls if w.id == connector.wall_b)
    gap = (np.array(wall_a.start) - np.array(wall_b.end)) + (np.array(wall_a.end) - np.array(wall_b.start))
    return float(np.linalg.norm(gap))


def test_overlapping_rooms_are_detected():
    from pipeline.schema import PropertyPlan

    room_a, room_b = _square_room("A"), _square_room("B")
    # Two identical-footprint rooms at the same coordinates -- a direct
    # check_no_overlaps case, independent of stitch_rooms placement.
    overlapping_plan = PropertyPlan(property_id="p", rooms=[room_a, room_b])
    assert check_no_overlaps(overlapping_plan) == [("A", "B")]
