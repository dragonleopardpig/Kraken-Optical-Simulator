"""Serializable row-spec contracts shared by preview, analysis, and workers."""

from __future__ import annotations

import hashlib

import numpy as np

from KrakenOS.UI.services.advanced_surface_attrs import _advanced_surface_attrs_from_spec
from KrakenOS.UI.services.catalog_metadata import _metal_catalog_signature, _metal_catalogs_from_row_specs
from KrakenOS.UI.trace_intent import BEAM_SPLITTER_SURFACE


def _surface_signature_token(value):
    if value is None or isinstance(value, (str, int, float, bool, np.floating, np.integer)):
        return value
    if isinstance(value, np.ndarray):
        array = np.asarray(value)
        return (
            "ndarray",
            array.shape,
            str(array.dtype),
            hashlib.sha1(array.tobytes()).hexdigest(),
        )
    if isinstance(value, dict):
        return tuple(sorted((str(key), _surface_signature_token(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_surface_signature_token(item) for item in value)
    if callable(value):
        return (
            "callable",
            getattr(value, "__module__", type(value).__module__),
            getattr(value, "__qualname__", getattr(value, "__name__", type(value).__qualname__)),
            id(value),
        )
    return (
        type(value).__module__,
        type(value).__qualname__,
        id(value),
    )


def _row_specs_signature(row_specs: list[dict]):
    metal_signature = _metal_catalog_signature(_metal_catalogs_from_row_specs(row_specs))
    signature = []
    for spec in row_specs:
        signature.append(
            (
                str(spec.get("surface", "")),
                str(spec.get("name", "")),
                float(spec.get("rc", 0.0)),
                float(spec.get("k", spec.get("K", 0.0))),
                float(spec.get("axicon", 0.0)),
                float(spec.get("diff_ord", spec.get("Diff_Ord", 0.0))),
                float(spec.get("grating_d", spec.get("Grating_D", 0.0))),
                float(spec.get("grating_angle", spec.get("Grating_Angle", 0.0))),
                float(spec.get("thickness", 0.0)),
                float(spec.get("diameter", 0.0)),
                float(spec.get("in_diameter", spec.get("InDiameter", 0.0))),
                float(spec.get("drawing", spec.get("Drawing", 1.0))),
                _surface_signature_token(spec.get("extra_data", spec.get("ExtraData", 0.0))),
                _surface_signature_token(spec.get("uda", spec.get("UDA", "None"))),
                _surface_signature_token(_advanced_surface_attrs_from_spec(spec)),
                str(spec.get("glass", "AIR")),
                float(spec.get("tilt_x", 0.0)),
                float(spec.get("tilt_y", 0.0)),
                float(spec.get("tilt_z", 0.0)),
                float(spec.get("desp_x", 0.0)),
                float(spec.get("desp_y", 0.0)),
                float(spec.get("desp_z", 0.0)),
                float(spec.get("axis_move", 0.0)),
                _surface_signature_token(spec.get("illumination_block_face_ids")),
            )
        )
    return metal_signature, tuple(signature)


def _requires_scalar_trace(row_specs: list[dict]) -> bool:
    # Kraken's current batch path is fast, but it does not reproduce all scalar
    # Trace() physics for thin-lens, folded, diffractive, and tilted/decentered elements.
    for spec in row_specs:
        if str(spec.get("surface", "")) in {"Thin Lens", "Mirror", "Grating", BEAM_SPLITTER_SURFACE}:
            return True
        if abs(float(spec.get("axicon", 0.0))) > 1e-12:
            return True
        if any(
            abs(float(spec.get(field, 0.0))) > 1e-12
            for field in ("tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y", "desp_z", "axis_move")
        ):
            return True
    return False
