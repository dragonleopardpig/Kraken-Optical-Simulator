"""Shared 3-D placement metadata for scene authoring.

The helpers in this module intentionally stay independent of tkinter, VTK, and
KrakenOS tracing objects.  They define the row-backed state that direct 3-D
placement tools and scene-bundle consumers can share.
"""

from __future__ import annotations

import math
from typing import Any

SCENE_PLACEMENT_ADVANCED_ATTR = "ScenePlacement"

SCENE_PLACEMENT_ANCHORS = ("row_pose", "target_center", "face_anchor")
SCENE_PLACEMENT_DEFAULT_SETTINGS: dict[str, object] = {
    "enabled": True,
    "anchor": "row_pose",
    "snap_enabled": False,
    "snap_mm": 1.0,
    "snap_deg": 5.0,
    "grid_visible": True,
    "grid_spacing_mm": 10.0,
    "grid_extent_mm": 100.0,
}


def scene_placement_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return bool(value)
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "enabled"}:
        return True
    if text in {"0", "false", "no", "off", "disabled"}:
        return False
    return bool(default)


def scene_placement_float(
    value: object,
    default: float,
    *,
    minimum: float = 0.0,
    maximum: float | None = None,
) -> float:
    try:
        number = float(value)
    except Exception:
        number = float(default)
    if not math.isfinite(number):
        number = float(default)
    number = max(float(number), float(minimum))
    if maximum is not None:
        number = min(number, float(maximum))
    return float(number)


def normalize_scene_placement_anchor(value: object) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "": "row_pose",
        "row": "row_pose",
        "pose": "row_pose",
        "surface": "row_pose",
        "target": "target_center",
        "target_pose": "target_center",
        "center": "target_center",
        "face": "face_anchor",
        "face_axis": "face_anchor",
        "picked_face": "face_anchor",
    }
    anchor = aliases.get(text, text)
    return anchor if anchor in SCENE_PLACEMENT_ANCHORS else "row_pose"


def normalize_scene_placement_settings(value: object) -> dict[str, object]:
    settings = dict(SCENE_PLACEMENT_DEFAULT_SETTINGS)
    if isinstance(value, dict):
        settings.update(value)
    settings["enabled"] = scene_placement_bool(settings.get("enabled"), True)
    settings["anchor"] = normalize_scene_placement_anchor(settings.get("anchor"))
    settings["snap_enabled"] = scene_placement_bool(settings.get("snap_enabled"), False)
    settings["snap_mm"] = scene_placement_float(settings.get("snap_mm"), 1.0, minimum=1e-6, maximum=1e6)
    settings["snap_deg"] = scene_placement_float(settings.get("snap_deg"), 5.0, minimum=1e-6, maximum=360.0)
    settings["grid_visible"] = scene_placement_bool(settings.get("grid_visible"), True)
    settings["grid_spacing_mm"] = scene_placement_float(
        settings.get("grid_spacing_mm"),
        10.0,
        minimum=1e-6,
        maximum=1e6,
    )
    settings["grid_extent_mm"] = scene_placement_float(
        settings.get("grid_extent_mm"),
        100.0,
        minimum=settings["grid_spacing_mm"],
        maximum=1e9,
    )
    return settings


def scene_placement_settings_is_default(settings: dict[str, object]) -> bool:
    normalized = normalize_scene_placement_settings(settings)
    defaults = normalize_scene_placement_settings({})
    return all(normalized.get(key) == defaults.get(key) for key in defaults)


def row_scene_placement_settings(row: Any) -> dict[str, object]:
    advanced = getattr(row, "advanced", {}) or {}
    raw = advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}) if isinstance(advanced, dict) else {}
    return normalize_scene_placement_settings(raw)


def row_has_scene_placement_metadata(row: Any) -> bool:
    advanced = getattr(row, "advanced", {}) or {}
    return isinstance(advanced, dict) and isinstance(advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR), dict)
