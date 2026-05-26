"""Shared tolerance UI constants."""

from __future__ import annotations

TOLERANCE_COMPENSATORS_ADVANCED_ATTR = "ToleranceCompensators"
TOLERANCE_COUPLING_ADVANCED_ATTR = "ToleranceCoupling"
TOLERANCE_MANUFACTURING_ADVANCED_ATTR = "ToleranceManufacturing"
TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS = "tolerance_manufacturing_templates"

TOLERANCE_COMPARE_VIEW_DEFAULT = "Spot overlay"
TOLERANCE_COMPARE_VIEW_VALUES = (
    TOLERANCE_COMPARE_VIEW_DEFAULT,
    "Stack-up bars",
    "MTF overlay",
    "Wavefront delta",
)
TOLERANCE_SOLVE_PRESET_DEFAULTS = {
    "sample_count": 25,
    "seed": 12345,
    "compensator_steps": 9,
    "multi_steps": 5,
    "multi_passes": 2,
}
