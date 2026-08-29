# Output Schema (Part 2 contract)

Defined in `pipeline/schema.py`. Every field with a numeric measurement carries
a `confidence_interval` — never a bare number — so tier-honest widening
(LiDAR tightest, Photos widest) is structural, not something a consumer of
the JSON has to know to ask for.

## Type reference

| Type | Fields | Notes |
|---|---|---|
| `Measurement` | `value`, `confidence_interval: [low, high]`, `unit` (default `cm`) | Populated via `pipeline.core.confidence.measurement_ci`, never hardcoded per-tier. |
| `Wall` | `id`, `start: [x,y]`, `end: [x,y]`, `length: Measurement` | Coordinates in the room's local 2D frame. |
| `Opening` | `id`, `wall_id`, `type: door\|window`, `width: Measurement`, `position_on_wall: 0.0-1.0` | Detection itself is scored (missed/phantom openings both count as misses), so an opening only appears here if the pipeline is confident it exists. |
| `DamageRegion` | `id`, `surface_id` (a `Wall.id`, or `"ceiling"`/`"floor"`), `damage_class: water\|fire\|mold\|structural\|cosmetic`, `severity: minor\|moderate\|severe`, `extent_area: Measurement` | Our own damage taxonomy (not published by the assessment — defined here). |
| `ConcealedFlag` | `id`, `rule_name`, `rule_description`, `triggered_by_region_ids: [DamageRegion.id]`, `predicted_issue`, `confidence` | Named, auditable rule — every flag must cite the rule that fired and the evidence (`triggered_by_region_ids`). No black-box guesses. |
| `ScopeItem` | `id`, `damage_region_id`, `description` | Repair line item, keyed to the damage region that requires it. |
| `Capture` (schema-level) | `tier`, `device`, `room_id` | Output-side capture metadata: which tier/device produced this room's plan. **Distinct from** `pipeline.core.types.Capture`, which holds the raw input frames an adapter loaded — don't confuse the two despite the shared name. |
| `Room` | `id`, `name`, `capture`, `walls`, `ceiling_height: Measurement`, `floor_area: Measurement`, `openings`, `damage_regions`, `concealed_flags`, `scope_items` | The per-room plan. |
| `PropertyPlan` | `property_id`, `rooms: [Room]`, `adjacency: [[room_id, room_id, shared_wall_or_opening_id]]` | The stitched whole-property plan — the product surface, produced from every tier including photos-only. |

## Serialization

Every dataclass has `to_dict()` / `from_dict(d)` (not generic reflection —
each type controls its own shape, including its `Enum` fields, so the JSON
stays stable even if internal field order changes). `PropertyPlan.to_dict()`
is the JSON actually written to disk per capture; `json.dumps(plan.to_dict())`
round-trips losslessly back to an equal `PropertyPlan` via
`PropertyPlan.from_dict(json.loads(payload))` — see
`tests/test_schema.py::test_property_plan_round_trips_through_json`.

## Example: one room, one water-damage flag

```json
{
  "property_id": "property-1",
  "rooms": [
    {
      "id": "room-1",
      "name": "living_room",
      "capture": { "tier": "lidar", "device": "iPhone16,2", "room_id": "room-1" },
      "walls": [
        {
          "id": "wall-1",
          "start": [0.0, 0.0],
          "end": [400.0, 0.0],
          "length": { "value": 400.0, "confidence_interval": [398.0, 402.0], "unit": "cm" }
        }
      ],
      "ceiling_height": { "value": 243.0, "confidence_interval": [242.0, 244.0], "unit": "cm" },
      "floor_area": { "value": 16.5, "confidence_interval": [16.0, 17.0], "unit": "m2" },
      "openings": [
        {
          "id": "opening-1",
          "wall_id": "wall-1",
          "type": "door",
          "width": { "value": 90.0, "confidence_interval": [88.5, 91.5], "unit": "cm" },
          "position_on_wall": 0.5
        }
      ],
      "damage_regions": [
        {
          "id": "damage-1",
          "surface_id": "ceiling",
          "damage_class": "water",
          "severity": "moderate",
          "extent_area": { "value": 0.6, "confidence_interval": [0.4, 0.8], "unit": "m2" }
        }
      ],
      "concealed_flags": [
        {
          "id": "flag-1",
          "rule_name": "ceiling_stain_below_bathroom",
          "rule_description": "IF ceiling_stain_area > 0.3m2 AND below_bathroom THEN flag possible leak",
          "triggered_by_region_ids": ["damage-1"],
          "predicted_issue": "possible plumbing leak from bathroom above",
          "confidence": 0.72
        }
      ],
      "scope_items": [
        {
          "id": "scope-1",
          "damage_region_id": "damage-1",
          "description": "Remove and replace water-damaged ceiling drywall, 0.6m2"
        }
      ]
    }
  ],
  "adjacency": [["room-1", "room-2", "wall-1"]]
}
```

## What's not in the schema yet

The concealed-damage **rule definitions themselves** (the actual `IF ... THEN
FLAG ...` catalog) live separately once written — `ConcealedFlag.rule_name`
is a reference key into that catalog, not the rule's implementation.
