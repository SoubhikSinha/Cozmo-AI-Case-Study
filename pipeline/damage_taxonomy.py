from __future__ import annotations

# Our own damage taxonomy (not published by the assessment). Re-exports the
# canonical enums from pipeline.schema (single source of truth for the JSON
# contract) and adds classification metadata used by damage_detection.py.
from pipeline.schema import DamageClass, Severity

__all__ = ["DamageClass", "Severity", "DAMAGE_CLASS_DESCRIPTIONS", "classify_severity"]

# ponytail: thresholds are a documented starting point, not calibrated
# against real staged-damage ground truth yet. Upgrade path: tune these
# once the benchmark has measured damage extents to compare against.
SEVERITY_THRESHOLDS_CM2 = {
    Severity.MINOR: 500.0,
    Severity.MODERATE: 2000.0,
}

DAMAGE_CLASS_DESCRIPTIONS = {
    DamageClass.WATER: "Water staining/discoloration, typically a brown-yellow tint on ceilings or walls",
    DamageClass.MOLD: "Mold growth, typically dark green/black patches with irregular texture",
    DamageClass.FIRE: "Fire or smoke damage, charring or soot discoloration",
    DamageClass.STRUCTURAL: "Structural cracks -- elongated, high-aspect-ratio surface breaks",
    DamageClass.COSMETIC: "Cosmetic wear not tied to an active damage mechanism",
}


def classify_severity(area_cm2: float) -> Severity:
    if area_cm2 < SEVERITY_THRESHOLDS_CM2[Severity.MINOR]:
        return Severity.MINOR
    if area_cm2 < SEVERITY_THRESHOLDS_CM2[Severity.MODERATE]:
        return Severity.MODERATE
    return Severity.SEVERE
