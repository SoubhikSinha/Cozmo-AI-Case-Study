import cv2
import numpy as np

from pipeline.concealed_damage import evaluate_concealed_damage
from pipeline.core.types import Capture, Frame, Tier
from pipeline.damage_detection import detect_damage
from pipeline.damage_taxonomy import DamageClass, Severity, classify_severity
from pipeline.schema import Capture as CaptureMeta
from pipeline.schema import DamageRegion, Measurement, Room, Wall
from pipeline.scope_generator import generate_scope_items

IMG_SIZE = (300, 400)  # h, w


def _blank_room_image() -> np.ndarray:
    return np.full((*IMG_SIZE, 3), (200, 200, 200), dtype=np.uint8)  # neutral gray, BGR


def _draw_water_stain(image: np.ndarray) -> np.ndarray:
    # brownish-yellow patch -- BGR so B low, G mid, R high => brown/yellow in HSV
    cv2.rectangle(image, (50, 50), (150, 130), (30, 110, 150), thickness=-1)
    return image


def _draw_mold_patch(image: np.ndarray) -> np.ndarray:
    # dark green/black patch
    cv2.rectangle(image, (200, 180), (280, 250), (20, 60, 20), thickness=-1)
    return image


def _draw_crack(image: np.ndarray) -> np.ndarray:
    # thin, long, dark diagonal line -- high aspect ratio
    cv2.line(image, (10, 290), (390, 10), (10, 10, 10), thickness=3)
    return image


def _simple_box_room(room_id: str = "test_room") -> Room:
    corners = [(0.0, 0.0), (400.0, 0.0), (400.0, 400.0), (0.0, 400.0)]
    length = Measurement(value=400.0, confidence_interval=(395.0, 405.0))
    walls = [Wall(id=f"wall-{i}", start=corners[i], end=corners[(i + 1) % 4], length=length) for i in range(4)]
    return Room(
        id=room_id,
        name=room_id,
        capture=CaptureMeta(tier=Tier.PHOTO, device="test", room_id=room_id),
        walls=walls,
        ceiling_height=Measurement(value=250.0, confidence_interval=(248.0, 252.0)),
        floor_area=Measurement(value=16.0, confidence_interval=(15.5, 16.5), unit="m2"),
    )


def test_classify_severity_thresholds():
    assert classify_severity(100) == Severity.MINOR
    assert classify_severity(1000) == Severity.MODERATE
    assert classify_severity(5000) == Severity.SEVERE


def test_detect_damage_finds_staged_water_stain(tmp_path):
    image_path = tmp_path / "img_0.jpg"
    cv2.imwrite(str(image_path), _draw_water_stain(_blank_room_image()))

    capture = Capture(tier=Tier.PHOTO, room_id="r1", frames=[Frame(image_path=image_path)])
    room = _simple_box_room()

    regions = detect_damage(room, capture)

    water_regions = [r for r in regions if r.damage_class == DamageClass.WATER]
    assert len(water_regions) == 1
    assert water_regions[0].extent_area.value > 0


def test_detect_damage_finds_staged_mold_patch(tmp_path):
    image_path = tmp_path / "img_0.jpg"
    cv2.imwrite(str(image_path), _draw_mold_patch(_blank_room_image()))

    capture = Capture(tier=Tier.PHOTO, room_id="r1", frames=[Frame(image_path=image_path)])
    room = _simple_box_room()

    regions = detect_damage(room, capture)

    mold_regions = [r for r in regions if r.damage_class == DamageClass.MOLD]
    assert len(mold_regions) == 1


def test_detect_damage_finds_staged_crack(tmp_path):
    image_path = tmp_path / "img_0.jpg"
    cv2.imwrite(str(image_path), _draw_crack(_blank_room_image()))

    capture = Capture(tier=Tier.PHOTO, room_id="r1", frames=[Frame(image_path=image_path)])
    room = _simple_box_room()

    regions = detect_damage(room, capture)

    structural_regions = [r for r in regions if r.damage_class == DamageClass.STRUCTURAL]
    assert len(structural_regions) >= 1


def test_detect_damage_finds_nothing_on_clean_room(tmp_path):
    image_path = tmp_path / "img_0.jpg"
    cv2.imwrite(str(image_path), _blank_room_image())

    capture = Capture(tier=Tier.PHOTO, room_id="r1", frames=[Frame(image_path=image_path)])
    room = _simple_box_room()

    assert detect_damage(room, capture) == []


def _region(damage_class, surface_id, area_cm2, region_id="d1"):
    return DamageRegion(
        id=region_id,
        surface_id=surface_id,
        damage_class=damage_class,
        severity=classify_severity(area_cm2),
        extent_area=Measurement(value=area_cm2, confidence_interval=(area_cm2 * 0.8, area_cm2 * 1.2), unit="cm2"),
    )


def test_hidden_leak_rule_fires_with_context_and_evidence():
    room = _simple_box_room()
    room.damage_regions = [_region(DamageClass.WATER, "ceiling", 800, "d1")]

    flags = evaluate_concealed_damage(room, context={"below_bathroom": True})

    assert len(flags) == 1
    assert flags[0].rule_name == "hidden_leak_below_bathroom"
    assert flags[0].triggered_by_region_ids == ["d1"]


def test_hidden_leak_rule_does_not_fire_without_context():
    room = _simple_box_room()
    room.damage_regions = [_region(DamageClass.WATER, "ceiling", 800, "d1")]

    flags = evaluate_concealed_damage(room, context={})  # no below_bathroom fact

    assert flags == []


def test_hidden_leak_rule_does_not_fire_below_area_threshold():
    room = _simple_box_room()
    room.damage_regions = [_region(DamageClass.WATER, "ceiling", 100, "d1")]  # under 500cm^2

    flags = evaluate_concealed_damage(room, context={"below_bathroom": True})

    assert flags == []


def test_mold_rule_fires_without_needing_context():
    room = _simple_box_room()
    room.damage_regions = [_region(DamageClass.MOLD, "wall-0", 500, "d2")]

    flags = evaluate_concealed_damage(room, context={})

    assert len(flags) == 1
    assert flags[0].rule_name == "mold_indicates_hidden_moisture"


def test_structural_crack_rule_requires_declared_load_bearing_wall():
    room = _simple_box_room()
    room.damage_regions = [_region(DamageClass.STRUCTURAL, "wall-1", 200, "d3")]

    no_context_flags = evaluate_concealed_damage(room, context={})
    assert no_context_flags == []

    with_context_flags = evaluate_concealed_damage(room, context={"load_bearing_walls": ["wall-1"]})
    assert len(with_context_flags) == 1
    assert with_context_flags[0].rule_name == "structural_crack_load_bearing"


def test_scope_generator_produces_one_item_per_damage_region():
    room = _simple_box_room()
    room.damage_regions = [
        _region(DamageClass.WATER, "ceiling", 800, "d1"),
        _region(DamageClass.MOLD, "wall-0", 500, "d2"),
    ]

    items = generate_scope_items(room)

    assert len(items) == 2
    assert {i.damage_region_id for i in items} == {"d1", "d2"}
    assert "water" in items[0].description.lower() or "damage" in items[0].description.lower()
