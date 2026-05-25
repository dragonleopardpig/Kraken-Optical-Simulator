"""Element, detector, and scene-target metadata normalization helpers."""

from __future__ import annotations

import re

import numpy as np

DETECTOR_DEFAULT_SETTINGS = {
    "active_width_mm": 0.0,
    "active_height_mm": 0.0,
    "bins": "",
    "pixel_pitch_um": 0.0,
}
SCENE_TARGET_DEFAULT_SETTINGS = {
    "role": "",
    "label": "",
}
SCENE_TARGET_ROLE_VALUES = {
    "",
    "analysis_target",
    "aperture",
    "detector",
    "object_reference",
    "object_target",
}
SCENE_TARGET_EDITOR_KIND_LABELS = {
    "auto": "Auto / from surface",
    "analysis_target": "Analysis Target",
    "detector": "Detector",
    "object_target": "Object Target",
    "diffuse_object": "Diffuse Object",
    "aperture": "Aperture",
}
SCENE_TARGET_EDITOR_KIND_CHOICES = tuple(SCENE_TARGET_EDITOR_KIND_LABELS.values())
SCENE_NORMAL_TARGET_LABELS = {
    "active_target": "Active target",
    "detector": "Detector",
    "object": "Object",
}
SCENE_NORMAL_TARGET_CHOICES = tuple(SCENE_NORMAL_TARGET_LABELS.values())

ELEMENT_ARM_ROLE_DEFAULT = "Unassigned"
ELEMENT_ARM_ROLE_VALUES = (
    ELEMENT_ARM_ROLE_DEFAULT,
    "Common",
    "Transmit",
    "Reflect",
    "Return",
    "Detector",
)
ELEMENT_BRANCH_SELECTOR_VALUES = (
    "Auto",
    "primary",
    "transmit",
    "reflect",
    "all",
)
ELEMENT_METADATA_NUMERIC_FIELDS = (
    "arm_distance",
    "local_decenter_x",
    "local_decenter_y",
    "local_tilt_x",
    "local_tilt_y",
    "local_tilt_z",
)


def _normalize_element_metadata(value) -> dict[str, object]:
    metadata: dict[str, object] = {
        "element_id": "",
        "element_name": "",
        "leg_id": "",
        "arm_role": ELEMENT_ARM_ROLE_DEFAULT,
        "parent_splitter": "",
        "branch_selector": "",
        "branch_path": "",
        "arm_distance": 0.0,
        "local_decenter_x": 0.0,
        "local_decenter_y": 0.0,
        "local_tilt_x": 0.0,
        "local_tilt_y": 0.0,
        "local_tilt_z": 0.0,
    }
    incoming = dict(value) if isinstance(value, dict) else {}
    metadata.update(incoming)

    role_aliases = {
        "": ELEMENT_ARM_ROLE_DEFAULT,
        "none": ELEMENT_ARM_ROLE_DEFAULT,
        "unassigned": ELEMENT_ARM_ROLE_DEFAULT,
        "common": "Common",
        "shared": "Common",
        "transmit": "Transmit",
        "transmitted": "Transmit",
        "transmission": "Transmit",
        "reflect": "Reflect",
        "reflected": "Reflect",
        "reflection": "Reflect",
        "return": "Return",
        "detector": "Detector",
        "image": "Detector",
    }
    role_key = re.sub(r"[^a-z0-9]", "", str(metadata.get("arm_role", "")).strip().lower())
    metadata["arm_role"] = role_aliases.get(role_key, ELEMENT_ARM_ROLE_DEFAULT)

    selector = str(metadata.get("branch_selector", "") or "").strip().lower()
    if selector in {"auto", "none", "default"}:
        selector = ""
    metadata["branch_selector"] = selector

    leg_id = str(metadata.get("leg_id", "") or "").strip().lower()
    if leg_id in {"auto", "none", "default"}:
        leg_id = ""
    metadata["leg_id"] = leg_id

    for key in ("element_id", "element_name", "parent_splitter", "branch_path"):
        metadata[key] = str(metadata.get(key, "") or "").strip()
    for key in ELEMENT_METADATA_NUMERIC_FIELDS:
        try:
            value_float = float(metadata.get(key, 0.0))
        except Exception:
            value_float = 0.0
        metadata[key] = value_float if np.isfinite(value_float) else 0.0
    return metadata


def _element_metadata_is_default(metadata: dict[str, object]) -> bool:
    normalized = _normalize_element_metadata(metadata)
    if str(normalized["arm_role"]) != ELEMENT_ARM_ROLE_DEFAULT:
        return False
    if any(
        str(normalized.get(key, "") or "").strip()
        for key in ("element_id", "element_name", "leg_id", "parent_splitter", "branch_selector", "branch_path")
    ):
        return False
    return all(abs(float(normalized.get(key, 0.0))) <= 1e-12 for key in ELEMENT_METADATA_NUMERIC_FIELDS)


def _normalize_detector_settings(value) -> dict[str, object]:
    settings = dict(DETECTOR_DEFAULT_SETTINGS)
    if isinstance(value, dict):
        settings.update(value)
    for key in ("active_width_mm", "active_height_mm", "pixel_pitch_um"):
        try:
            number = float(settings.get(key, 0.0))
        except Exception:
            number = 0.0
        settings[key] = max(number, 0.0) if np.isfinite(number) else 0.0
    bins = str(settings.get("bins", "") or "").strip()
    if bins.lower() in {"auto", "default", "none"}:
        bins = ""
    if bins:
        try:
            bins = str(int(np.clip(int(float(bins)), 4, 512)))
        except Exception:
            bins = ""
    settings["bins"] = bins
    return settings


def _normalize_scene_target_role(value: object) -> str:
    role = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "auto": "",
        "from_surface": "",
        "auto/from_surface": "",
        "target": "analysis_target",
        "analysis": "analysis_target",
        "analysis_target_only": "analysis_target",
        "object": "object_reference",
        "object_ref": "object_reference",
        "object_target_proxy": "object_target",
        "diffuse_object": "object_target",
    }
    role = aliases.get(role, role)
    return role if role in SCENE_TARGET_ROLE_VALUES else ""


def _normalize_scene_target_settings(value) -> dict[str, object]:
    settings = dict(SCENE_TARGET_DEFAULT_SETTINGS)
    if isinstance(value, dict):
        settings.update(value)
    settings["role"] = _normalize_scene_target_role(settings.get("role"))
    settings["label"] = str(settings.get("label", "") or "").strip()
    return settings


def _scene_target_settings_is_default(settings: dict[str, object]) -> bool:
    normalized = _normalize_scene_target_settings(settings)
    return not str(normalized.get("role", "") or "").strip() and not str(normalized.get("label", "") or "").strip()


def _normalize_scene_target_editor_kind(value: object) -> str:
    text = str(value or "").strip()
    for key, label in SCENE_TARGET_EDITOR_KIND_LABELS.items():
        if text == label:
            return key
    key = text.lower().replace("-", "_").replace(" ", "_").replace("/", "_")
    aliases = {
        "": "auto",
        "auto_from_surface": "auto",
        "auto": "auto",
        "analysis": "analysis_target",
        "analysis_target": "analysis_target",
        "target": "analysis_target",
        "scene_target": "analysis_target",
        "detector": "detector",
        "image": "detector",
        "object_target": "object_target",
        "object": "object_target",
        "diffuse": "diffuse_object",
        "diffuse_object": "diffuse_object",
        "aperture": "aperture",
    }
    return aliases.get(key, "auto")


def _scene_target_role_for_editor_kind(kind: object) -> str:
    normalized = _normalize_scene_target_editor_kind(kind)
    if normalized == "auto":
        return ""
    if normalized == "diffuse_object":
        return "object_target"
    return normalized


def _normalize_scene_normal_target_kind(value: object) -> str:
    text = str(value or "").strip()
    for key, label in SCENE_NORMAL_TARGET_LABELS.items():
        if text == label:
            return key
    key = text.lower().replace("-", "_").replace(" ", "_").replace("/", "_")
    aliases = {
        "": "detector",
        "active": "active_target",
        "active_target": "active_target",
        "analysis_target": "active_target",
        "target": "active_target",
        "targsurf": "active_target",
        "detector": "detector",
        "image": "detector",
        "sensor": "detector",
        "object": "object",
        "object_reference": "object",
        "object_target": "object",
        "diffuse_object": "object",
    }
    return aliases.get(key, "detector")


def _detector_settings_is_default(settings: dict[str, object]) -> bool:
    normalized = _normalize_detector_settings(settings)
    return (
        abs(float(normalized.get("active_width_mm", 0.0))) <= 1e-12
        and abs(float(normalized.get("active_height_mm", 0.0))) <= 1e-12
        and abs(float(normalized.get("pixel_pitch_um", 0.0))) <= 1e-12
        and not str(normalized.get("bins", "") or "").strip()
    )
