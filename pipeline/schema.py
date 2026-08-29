from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pipeline.core.types import Tier


class OpeningType(str, Enum):
    DOOR = "door"
    WINDOW = "window"


class DamageClass(str, Enum):
    WATER = "water"
    FIRE = "fire"
    MOLD = "mold"
    STRUCTURAL = "structural"
    COSMETIC = "cosmetic"


class Severity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class Measurement:
    """A single measured value with an honest confidence interval.

    tier-appropriate width: LiDAR tightest, Photos widest. Always populated
    via pipeline.confidence.measurement_ci, never hardcoded inline.
    """

    value: float
    confidence_interval: tuple[float, float]
    unit: str = "cm"

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "confidence_interval": list(self.confidence_interval),
            "unit": self.unit,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Measurement":
        return cls(
            value=d["value"],
            confidence_interval=tuple(d["confidence_interval"]),
            unit=d.get("unit", "cm"),
        )


@dataclass
class Wall:
    id: str
    start: tuple[float, float]
    end: tuple[float, float]
    length: Measurement

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start": list(self.start),
            "end": list(self.end),
            "length": self.length.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Wall":
        return cls(
            id=d["id"],
            start=tuple(d["start"]),
            end=tuple(d["end"]),
            length=Measurement.from_dict(d["length"]),
        )


@dataclass
class Opening:
    id: str
    wall_id: str
    type: OpeningType
    width: Measurement
    position_on_wall: float  # 0.0-1.0, distance along the wall from `start`

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "wall_id": self.wall_id,
            "type": self.type.value,
            "width": self.width.to_dict(),
            "position_on_wall": self.position_on_wall,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Opening":
        return cls(
            id=d["id"],
            wall_id=d["wall_id"],
            type=OpeningType(d["type"]),
            width=Measurement.from_dict(d["width"]),
            position_on_wall=d["position_on_wall"],
        )


@dataclass
class DamageRegion:
    id: str
    surface_id: str  # a Wall.id, or "ceiling" / "floor"
    damage_class: DamageClass
    severity: Severity
    extent_area: Measurement

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "surface_id": self.surface_id,
            "damage_class": self.damage_class.value,
            "severity": self.severity.value,
            "extent_area": self.extent_area.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DamageRegion":
        return cls(
            id=d["id"],
            surface_id=d["surface_id"],
            damage_class=DamageClass(d["damage_class"]),
            severity=Severity(d["severity"]),
            extent_area=Measurement.from_dict(d["extent_area"]),
        )


@dataclass
class ConcealedFlag:
    """A named, auditable rule firing — never a black-box guess."""

    id: str
    rule_name: str
    rule_description: str
    triggered_by_region_ids: list[str]
    predicted_issue: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "rule_description": self.rule_description,
            "triggered_by_region_ids": list(self.triggered_by_region_ids),
            "predicted_issue": self.predicted_issue,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConcealedFlag":
        return cls(
            id=d["id"],
            rule_name=d["rule_name"],
            rule_description=d["rule_description"],
            triggered_by_region_ids=list(d["triggered_by_region_ids"]),
            predicted_issue=d["predicted_issue"],
            confidence=d["confidence"],
        )


@dataclass
class ScopeItem:
    """A repair line item keyed to the surface/damage it addresses."""

    id: str
    damage_region_id: str
    description: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "damage_region_id": self.damage_region_id,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ScopeItem":
        return cls(
            id=d["id"],
            damage_region_id=d["damage_region_id"],
            description=d["description"],
        )


@dataclass
class Capture:
    """Output-side capture metadata attached to a Room's plan: which tier/
    device produced it. Distinct from pipeline.core.types.Capture, which
    holds the raw input frames the adapters loaded.
    """

    tier: Tier
    device: str
    room_id: str

    def to_dict(self) -> dict:
        return {"tier": self.tier.value, "device": self.device, "room_id": self.room_id}

    @classmethod
    def from_dict(cls, d: dict) -> "Capture":
        return cls(tier=Tier(d["tier"]), device=d["device"], room_id=d["room_id"])


@dataclass
class Room:
    id: str
    name: str
    capture: Capture
    walls: list[Wall]
    ceiling_height: Measurement
    floor_area: Measurement
    openings: list[Opening] = field(default_factory=list)
    damage_regions: list[DamageRegion] = field(default_factory=list)
    concealed_flags: list[ConcealedFlag] = field(default_factory=list)
    scope_items: list[ScopeItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "capture": self.capture.to_dict(),
            "walls": [w.to_dict() for w in self.walls],
            "ceiling_height": self.ceiling_height.to_dict(),
            "floor_area": self.floor_area.to_dict(),
            "openings": [o.to_dict() for o in self.openings],
            "damage_regions": [d.to_dict() for d in self.damage_regions],
            "concealed_flags": [c.to_dict() for c in self.concealed_flags],
            "scope_items": [s.to_dict() for s in self.scope_items],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Room":
        return cls(
            id=d["id"],
            name=d["name"],
            capture=Capture.from_dict(d["capture"]),
            walls=[Wall.from_dict(w) for w in d["walls"]],
            ceiling_height=Measurement.from_dict(d["ceiling_height"]),
            floor_area=Measurement.from_dict(d["floor_area"]),
            openings=[Opening.from_dict(o) for o in d.get("openings", [])],
            damage_regions=[DamageRegion.from_dict(r) for r in d.get("damage_regions", [])],
            concealed_flags=[ConcealedFlag.from_dict(c) for c in d.get("concealed_flags", [])],
            scope_items=[ScopeItem.from_dict(s) for s in d.get("scope_items", [])],
        )


@dataclass
class PropertyPlan:
    """The stitched whole-property plan: every room placed and connected."""

    property_id: str
    rooms: list[Room]
    adjacency: list[tuple[str, str, str]] = field(default_factory=list)  # (room_id, room_id, shared_wall_id or opening_id)

    def to_dict(self) -> dict:
        return {
            "property_id": self.property_id,
            "rooms": [r.to_dict() for r in self.rooms],
            "adjacency": [list(a) for a in self.adjacency],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PropertyPlan":
        return cls(
            property_id=d["property_id"],
            rooms=[Room.from_dict(r) for r in d["rooms"]],
            adjacency=[tuple(a) for a in d.get("adjacency", [])],
        )
