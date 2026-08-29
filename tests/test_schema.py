import json

from pipeline.core.types import Tier
from pipeline.schema import (
    Capture,
    ConcealedFlag,
    DamageClass,
    DamageRegion,
    Measurement,
    Opening,
    OpeningType,
    PropertyPlan,
    Room,
    ScopeItem,
    Severity,
    Wall,
)


def _sample_plan() -> PropertyPlan:
    wall = Wall(
        id="wall-1",
        start=(0.0, 0.0),
        end=(400.0, 0.0),
        length=Measurement(value=400.0, confidence_interval=(398.0, 402.0)),
    )
    opening = Opening(
        id="opening-1",
        wall_id="wall-1",
        type=OpeningType.DOOR,
        width=Measurement(value=90.0, confidence_interval=(88.5, 91.5)),
        position_on_wall=0.5,
    )
    damage = DamageRegion(
        id="damage-1",
        surface_id="ceiling",
        damage_class=DamageClass.WATER,
        severity=Severity.MODERATE,
        extent_area=Measurement(value=0.6, confidence_interval=(0.4, 0.8), unit="m2"),
    )
    flag = ConcealedFlag(
        id="flag-1",
        rule_name="ceiling_stain_below_bathroom",
        rule_description="IF ceiling_stain_area > 0.3m2 AND below_bathroom THEN flag possible leak",
        triggered_by_region_ids=["damage-1"],
        predicted_issue="possible plumbing leak from bathroom above",
        confidence=0.72,
    )
    scope = ScopeItem(
        id="scope-1",
        damage_region_id="damage-1",
        description="Remove and replace water-damaged ceiling drywall, 0.6m2",
    )
    room = Room(
        id="room-1",
        name="living_room",
        capture=Capture(tier=Tier.LIDAR, device="iPhone16,2", room_id="room-1"),
        walls=[wall],
        ceiling_height=Measurement(value=243.0, confidence_interval=(242.0, 244.0)),
        floor_area=Measurement(value=16.5, confidence_interval=(16.0, 17.0), unit="m2"),
        openings=[opening],
        damage_regions=[damage],
        concealed_flags=[flag],
        scope_items=[scope],
    )
    return PropertyPlan(property_id="property-1", rooms=[room], adjacency=[("room-1", "room-2", "wall-1")])


def test_property_plan_round_trips_through_json():
    plan = _sample_plan()

    payload = json.dumps(plan.to_dict())
    restored = PropertyPlan.from_dict(json.loads(payload))

    assert restored == plan
