"""Safe custom-surface presets for KrakenOS layout editor replay."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np


def extra_xy_cosines(x, y, params):
    period = params[0]
    amplitude = params[1]
    x = np.asarray(x)
    y = np.asarray(y)
    hx = 2.0 * np.pi * np.sqrt((x * x) + (y * y * 0.0)) / period
    hy = 2.0 * np.pi * np.sqrt((x * x * 0.0) + (y * y)) / period
    return np.abs(np.cos(hx) * amplitude) + np.abs(np.cos(hy) * amplitude)


def extra_radial_sine(x, y, params):
    period = params[0]
    amplitude = params[1]
    r = np.sqrt(np.asarray(x) * np.asarray(x) + np.asarray(y) * np.asarray(y))
    return np.sin(2.0 * np.pi * r / period) * amplitude


def extra_micro_lens_array(x, y, params):
    pitch = params[0]
    radius = params[1]
    conic = params[2]
    x = np.asarray(x)
    y = np.asarray(y)
    local_x = x - pitch * np.rint(x / pitch)
    local_y = y - pitch * np.rint(y / pitch)
    s = np.sqrt((local_x * local_x) + (local_y * local_y))
    curvature = 1.0 / radius
    root = np.maximum(1.0 - (conic + 1.0) * curvature * curvature * s * s, 1e-12)
    return curvature * s * s / (1.0 + np.sqrt(root))


EXTRA_SURFACE_PRESETS: dict[str, Callable[[Any, Any, Any], Any]] = {
    "xy_cosines": extra_xy_cosines,
    "radial_sine": extra_radial_sine,
    "micro_lens_array": extra_micro_lens_array,
}


def regular_polygon_uda(radius: float, sides: int, rotation_deg: float = 0.0) -> list[list[float]]:
    sides = max(int(sides), 3)
    angles = np.deg2rad(float(rotation_deg)) + np.linspace(0.0, 2.0 * np.pi, sides + 1)
    px = float(radius) * np.cos(angles)
    py = float(radius) * np.sin(angles)
    return [px.tolist(), py.tolist()]


def decode_custom_surface_value(value):
    if not isinstance(value, dict):
        return value
    kind = str(value.get("kind", "")).strip().lower()
    if kind in {"extra_surface", "extra_data", "extradata"}:
        preset = str(value.get("preset", value.get("name", ""))).strip()
        func = EXTRA_SURFACE_PRESETS.get(preset)
        if func is None:
            raise ValueError(f"Unknown ExtraData preset: {preset!r}")
        params = value.get("params", value.get("coef", []))
        return [func, params]
    if kind in {"uda_regular_polygon", "regular_polygon_uda", "regular_polygon"}:
        return regular_polygon_uda(
            float(value.get("radius", 1.0)),
            int(value.get("sides", 6)),
            float(value.get("rotation_deg", value.get("rotation", 0.0))),
        )
    return value


def encode_custom_surface_value(value):
    if isinstance(value, dict) and str(value.get("kind", "")).strip():
        return value
    if not isinstance(value, (list, tuple)) or len(value) != 2 or not callable(value[0]):
        return None
    func, params = value
    preset = identify_extra_surface_preset(func, params)
    if preset is None:
        return None
    return {
        "kind": "extra_surface",
        "preset": preset,
        "params": _literal_value(params),
    }


def identify_extra_surface_preset(func: Callable, params) -> str | None:
    try:
        x = np.asarray([-3.0, -0.5, 0.0, 1.25, 4.0], dtype=float)
        y = np.asarray([2.0, -1.0, 0.0, 0.75, -3.5], dtype=float)
        target = np.asarray(func(x, y, params), dtype=float)
    except Exception:
        return None
    for name, candidate in EXTRA_SURFACE_PRESETS.items():
        try:
            trial = np.asarray(candidate(x, y, params), dtype=float)
        except Exception:
            continue
        if target.shape == trial.shape and np.allclose(target, trial, rtol=1e-9, atol=1e-9, equal_nan=True):
            return name
    return None


def _literal_value(value):
    if value is None or isinstance(value, (str, int, float, bool, np.floating, np.integer)):
        return value
    if isinstance(value, np.ndarray):
        return np.asarray(value).tolist()
    if isinstance(value, (list, tuple)):
        return [_literal_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _literal_value(item) for key, item in value.items()}
    return repr(value)
