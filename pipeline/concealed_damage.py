from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pipeline.damage_taxonomy import DamageClass
from pipeline.schema import ConcealedFlag, Room

# Named, auditable rules: every ConcealedFlag records which rule fired
# (rule_id + rule_description) and the region ids that triggered it -- no
# black-box guesses. `context` carries facts we don't (and can't reliably)
# infer from geometry alone -- e.g. "this room is below a bathroom" is
# building-topology knowledge, not something derivable from a point cloud,
# so it's hand-supplied the same way pipeline.stitching.Connector is.


@dataclass
class ConcealedDamageRule:
    rule_id: str
    description: str
    predicate: Callable[[Room, dict], list[str]]  # returns triggered region ids, [] if not fired
    predicted_issue: str
    confidence: float


def _rule_hidden_leak_below_bathroom(room: Room, context: dict) -> list[str]:
    if not context.get("below_bathroom"):
        return []
    return [
        r.id
        for r in room.damage_regions
        if r.damage_class == DamageClass.WATER and r.surface_id == "ceiling" and r.extent_area.value > 500
    ]


def _rule_mold_indicates_hidden_moisture(room: Room, context: dict) -> list[str]:
    return [r.id for r in room.damage_regions if r.damage_class == DamageClass.MOLD and r.extent_area.value > 300]


def _rule_structural_crack_on_load_bearing_wall(room: Room, context: dict) -> list[str]:
    load_bearing = set(context.get("load_bearing_walls", []))
    if not load_bearing:
        return []
    return [
        r.id
        for r in room.damage_regions
        if r.damage_class == DamageClass.STRUCTURAL and r.surface_id in load_bearing and r.extent_area.value > 50
    ]


RULES: list[ConcealedDamageRule] = [
    ConcealedDamageRule(
        rule_id="hidden_leak_below_bathroom",
        description="IF a ceiling water-damage region > 500cm^2 AND room is below a bathroom THEN flag possible hidden leak",
        predicate=_rule_hidden_leak_below_bathroom,
        predicted_issue="possible plumbing leak from the bathroom above",
        confidence=0.7,
    ),
    ConcealedDamageRule(
        rule_id="mold_indicates_hidden_moisture",
        description="IF a mold region > 300cm^2 exists THEN flag a likely hidden/ongoing moisture source",
        predicate=_rule_mold_indicates_hidden_moisture,
        predicted_issue="likely hidden or ongoing moisture source feeding the mold growth",
        confidence=0.6,
    ),
    ConcealedDamageRule(
        rule_id="structural_crack_load_bearing",
        description="IF a structural crack > 50cm^2 is on a declared load-bearing wall THEN flag possible foundational movement",
        predicate=_rule_structural_crack_on_load_bearing_wall,
        predicted_issue="possible foundational movement or settling",
        confidence=0.5,
    ),
]


def evaluate_concealed_damage(room: Room, context: dict | None = None) -> list[ConcealedFlag]:
    context = context or {}
    flags: list[ConcealedFlag] = []
    for rule in RULES:
        triggered_ids = rule.predicate(room, context)
        if triggered_ids:
            flags.append(
                ConcealedFlag(
                    id=f"flag-{rule.rule_id}",
                    rule_name=rule.rule_id,
                    rule_description=rule.description,
                    triggered_by_region_ids=triggered_ids,
                    predicted_issue=rule.predicted_issue,
                    confidence=rule.confidence,
                )
            )
    return flags
