from __future__ import annotations

from pipeline.damage_taxonomy import DamageClass
from pipeline.schema import Room, ScopeItem

_REPAIR_ACTIONS = {
    DamageClass.WATER: "Remove and dry affected material; treat for water damage",
    DamageClass.MOLD: "Remediate mold growth and treat affected surface",
    DamageClass.FIRE: "Remove charred material and treat for smoke/soot damage",
    DamageClass.STRUCTURAL: "Inspect and repair structural crack",
    DamageClass.COSMETIC: "Patch and repaint affected surface",
}


def generate_scope_items(room: Room) -> list[ScopeItem]:
    """Convert each damage region into a repair line item keyed to its surface."""
    items = []
    for region in room.damage_regions:
        action = _REPAIR_ACTIONS.get(region.damage_class, "Inspect and repair affected surface")
        area_desc = f"{region.extent_area.value:.0f} {region.extent_area.unit}"
        items.append(
            ScopeItem(
                id=f"scope-{region.id}",
                damage_region_id=region.id,
                description=f"{action} on {region.surface_id} ({region.severity.value} severity, {area_desc})",
            )
        )
    return items
