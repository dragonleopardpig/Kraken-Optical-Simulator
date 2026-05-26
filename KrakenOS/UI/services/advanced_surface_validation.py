"""Advanced surface metadata validation helpers."""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.custom_surfaces import decode_custom_surface_value
from KrakenOS.UI.lens_drawing_properties import DRAWING_PROPERTIES_ATTR, validate_drawing_properties
from KrakenOS.UI.services.beam_scatter_metadata import (
    BEAM_SPLITTER_ADVANCED_ATTR,
    DIFFUSE_SCATTER_ADVANCED_ATTR,
    _validate_beam_splitter_settings,
    _validate_diffuse_scatter_settings,
)
from KrakenOS.UI.services.element_scene_metadata import _normalize_element_metadata
from KrakenOS.UI.services.error_map_metadata import _finite_numeric_array, _validate_error_map
from KrakenOS.UI.services.optical_solid_geometry import (
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    OPTICAL_SOLID_FACE_SIDE_DEFAULT,
    OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER,
    _normalize_optical_solid_face_function,
    _normalize_optical_solid_face_side,
    _normalize_optical_solid_virtual_plane_kind,
    normalize_optical_solid_face_metadata,
    normalize_optical_solid_virtual_plane_record,
)

ELEMENT_ADVANCED_ATTR = "Element"


def _validate_coating_table(value) -> list[str]:
    coating = value
    if not isinstance(coating, (list, tuple)) or len(coating) != 4:
        return ["Coating must be [R, A, W, THETA]."]
    r_table, a_table, wavelengths, angles = coating
    if all(isinstance(item, (list, tuple, np.ndarray)) and len(item) == 0 for item in coating):
        return []
    messages: list[str] = []
    try:
        r_arr = _finite_numeric_array(r_table)
        a_arr = _finite_numeric_array(a_table)
        w_arr = _finite_numeric_array(wavelengths).ravel()
        theta_arr = _finite_numeric_array(angles).ravel()
    except Exception as exc:
        return [f"Coating contains invalid numeric data: {exc}."]
    expected_shape = (theta_arr.size, w_arr.size)
    if r_arr.shape != expected_shape:
        messages.append(f"Coating R table shape {r_arr.shape} should be {expected_shape} = len(THETA) x len(W).")
    if a_arr.shape != expected_shape:
        messages.append(f"Coating A table shape {a_arr.shape} should be {expected_shape} = len(THETA) x len(W).")
    if np.any((r_arr < 0.0) | (r_arr > 1.0)):
        messages.append("Coating R values should be in [0, 1].")
    if np.any((a_arr < 0.0) | (a_arr > 1.0)):
        messages.append("Coating A values should be in [0, 1].")
    if r_arr.shape == a_arr.shape and np.any((r_arr + a_arr) > 1.0 + 1e-9):
        messages.append("Coating R + A should not exceed 1.")
    if np.any(w_arr <= 0.0):
        messages.append("Coating wavelengths must be positive microns.")
    if np.any(np.diff(w_arr) < 0.0):
        messages.append("Coating wavelengths should be sorted ascending.")
    if np.any(np.diff(theta_arr) < 0.0):
        messages.append("Coating incidence angles should be sorted ascending.")
    return messages


def _validate_coating_met(value) -> list[str]:
    try:
        coating_met = float(value)
    except Exception as exc:
        return [f"CoatingMet must be an integer metal index: {exc}."]
    if not np.isfinite(coating_met) or int(coating_met) != coating_met:
        return ["CoatingMet must be an integer metal index."]
    if coating_met < 0:
        return ["CoatingMet should not be negative."]
    return []


def _validate_drawing_properties(value) -> list[str]:
    return validate_drawing_properties(value)


def _validate_custom_extra_data(value) -> list[str]:
    if value is None or (isinstance(value, str) and value == "None"):
        return []
    try:
        if np.all(np.asarray(value, dtype=object) == 0):
            return []
    except Exception:
        pass
    try:
        decoded = decode_custom_surface_value(value)
    except Exception as exc:
        return [f"ExtraData preset cannot be decoded: {exc}."]
    if isinstance(decoded, np.ndarray):
        return []
    if not isinstance(decoded, (list, tuple)) or len(decoded) != 2:
        return ["ExtraData must be a zero/default value, [callable, params], or a supported preset dict."]
    func, params = decoded
    if not callable(func):
        return ["ExtraData first item must be callable after decoding."]
    try:
        result = np.asarray(func(np.asarray([0.0, 1.0]), np.asarray([0.0, -1.0]), params), dtype=float)
    except Exception as exc:
        return [f"ExtraData callable failed a preview evaluation: {exc}."]
    if result.size == 0 or not np.all(np.isfinite(result)):
        return ["ExtraData callable returned empty or non-finite preview values."]
    return []


def _validate_uda(value) -> list[str]:
    try:
        decoded = decode_custom_surface_value(value)
    except Exception as exc:
        return [f"UDA preset cannot be decoded: {exc}."]
    if decoded is None or (isinstance(decoded, str) and decoded == "None"):
        return []
    if not isinstance(decoded, (list, tuple)) or len(decoded) != 2:
        return ["UDA must be 'None', [px, py], or a supported preset dict."]
    try:
        px = _finite_numeric_array(decoded[0]).ravel()
        py = _finite_numeric_array(decoded[1]).ravel()
    except Exception as exc:
        return [f"UDA polygon contains invalid numeric data: {exc}."]
    if px.size != py.size:
        return [f"UDA px/py length mismatch: {px.size} vs {py.size}."]
    if px.size < 4:
        return ["UDA polygon should contain at least 4 points including closure."]
    return []


def _validate_optical_solid_virtual_planes(metadata) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings_out: list[str] = []
    normalized = normalize_optical_solid_face_metadata(metadata)
    planes = [plane for plane in list(normalized.get("virtual_planes", []) or []) if isinstance(plane, dict)]
    seen_ids: set[str] = set()
    for plane in planes:
        record = normalize_optical_solid_virtual_plane_record(plane)
        plane_id = str(record.get("plane_id", "") or "").strip() or "VP?"
        if plane_id in seen_ids:
            errors.append(f"OpticalSolidFaces virtual plane {plane_id} is duplicated.")
        seen_ids.add(plane_id)
        normal = np.asarray(record.get("normal", (0.0, 0.0, 1.0)), dtype=float).reshape(3)
        point = np.asarray(record.get("point", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
        if not np.all(np.isfinite(point)):
            errors.append(f"OpticalSolidFaces virtual plane {plane_id} point is not finite.")
        if not np.all(np.isfinite(normal)) or float(np.linalg.norm(normal)) <= 1e-12:
            errors.append(f"OpticalSolidFaces virtual plane {plane_id} normal is not finite/non-zero.")
        if float(record.get("aperture_mm", 0.0) or 0.0) <= 0.0:
            warnings_out.append(f"OpticalSolidFaces virtual plane {plane_id} has no positive aperture; preview size may be ambiguous.")
        if _normalize_optical_solid_virtual_plane_kind(record.get("kind")) == OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER:
            source_sides = [
                side
                for side in list(record.get("source_sides", []) or [])
                if _normalize_optical_solid_face_side(side) != OPTICAL_SOLID_FACE_SIDE_DEFAULT
            ]
            if len(source_sides) < 2:
                warnings_out.append(f"OpticalSolidFaces virtual plane {plane_id} has no saved source side pair.")
    return errors, warnings_out


def _validate_advanced_surface_inputs(
    advanced: dict[str, object],
    extra_data,
    uda,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings_out: list[str] = []
    if "Coating" in advanced:
        errors.extend(_validate_coating_table(advanced["Coating"]))
    if "CoatingMet" in advanced:
        errors.extend(_validate_coating_met(advanced["CoatingMet"]))
    if DRAWING_PROPERTIES_ATTR in advanced:
        errors.extend(_validate_drawing_properties(advanced[DRAWING_PROPERTIES_ATTR]))
    if BEAM_SPLITTER_ADVANCED_ATTR in advanced:
        errors.extend(_validate_beam_splitter_settings(advanced[BEAM_SPLITTER_ADVANCED_ATTR]))
    if DIFFUSE_SCATTER_ADVANCED_ATTR in advanced:
        errors.extend(_validate_diffuse_scatter_settings(advanced[DIFFUSE_SCATTER_ADVANCED_ATTR]))
    if ELEMENT_ADVANCED_ATTR in advanced:
        _normalize_element_metadata(advanced[ELEMENT_ADVANCED_ATTR])
    if "OpticalSolidFaces" in advanced:
        metadata = normalize_optical_solid_face_metadata(advanced["OpticalSolidFaces"])
        functions = [
            _normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
            for face in list(metadata.get("faces", []) or [])
            if _normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
            != OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
        ]
        sides = [
            _normalize_optical_solid_face_side(face.get("side_2d"))
            for face in list(metadata.get("faces", []) or [])
            if _normalize_optical_solid_face_side(face.get("side_2d")) != OPTICAL_SOLID_FACE_SIDE_DEFAULT
        ]
        if functions and not sides:
            warnings_out.append("OpticalSolidFaces has optical functions but no 2D side labels.")
        if sides and not functions:
            warnings_out.append("OpticalSolidFaces has 2D side labels but no optical functions.")
        plane_errors, plane_warnings = _validate_optical_solid_virtual_planes(metadata)
        errors.extend(plane_errors)
        warnings_out.extend(plane_warnings)
    if "Error_map" in advanced:
        errors.extend(_validate_error_map(advanced["Error_map"]))
    if "SPECIAL_SURF_FUNC" in advanced:
        value = advanced["SPECIAL_SURF_FUNC"]
        if isinstance(value, str):
            warnings_out.append("SPECIAL_SURF_FUNC is a string reference; it is preserved but not previewed.")
        elif not callable(value) and not isinstance(value, (list, tuple)):
            warnings_out.append("SPECIAL_SURF_FUNC is not callable/list-like; KrakenOS may reject it.")
    errors.extend(_validate_custom_extra_data(extra_data))
    errors.extend(_validate_uda(uda))
    return errors, warnings_out
