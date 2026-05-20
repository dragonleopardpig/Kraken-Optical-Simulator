from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.scene_geometry import SceneSource3D
from KrakenOS.UI.scene_projector import normalize_projection_plane
from KrakenOS.UI.trace_intent import layout_uses_nonseq as _layout_uses_nonseq
from KrakenOS.UI.trace_intent import resolve_trace_intent
from KrakenOS.UI.scene_source_analysis import (
    normalize_scene_source_specs,
    scene_source_from_spec,
    scene_source_setting_value,
    source_spec_float,
)

try:
    from KrakenOS.UI.zemax_rayfile import sample_zemax_rayfile
except Exception:  # pragma: no cover - optional import for standalone exports.
    sample_zemax_rayfile = None


SOURCE_MODEL_DEFAULT = "Pupil / field"
SOURCE_MODEL_ZEMAX_RAYFILE = "Zemax rayfile source"
SOURCE_MODEL_VALUES = (
    SOURCE_MODEL_DEFAULT,
    "Gaussian beam",
    "Collimated disk source",
    "Random circle source",
    "Random square source",
    "Random line source",
    "Random point cone",
    SOURCE_MODEL_ZEMAX_RAYFILE,
)
SOURCE_ANGULAR_WEIGHT_DEFAULT = "Uniform solid angle"
PUPIL_PATTERN_TO_KRAKEN = {
    "Cross fan": "fan",
    "Fan X": "fanx",
    "Fan Y": "fany",
    "Hexapolar": "hexapolar",
    "Square": "square",
    "Random disk": "rand",
    "Chief ray": "chief",
    "R-theta": "rtheta",
}


def _settings_float(settings: dict[str, Any], key: str, default: float, *, minimum: float | None = None) -> float:
    try:
        value = float(settings.get(key, default))
    except Exception:
        value = float(default)
    if not np.isfinite(value):
        value = float(default)
    if minimum is not None:
        value = max(float(minimum), float(value))
    return float(value)


def _settings_int(settings: dict[str, Any], key: str, default: int, *, minimum: int = 1) -> int:
    return max(int(minimum), int(round(_settings_float(settings, key, float(default), minimum=float(minimum)))))


def _settings_bool_value(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return bool(value)
    if value is None:
        return bool(default)
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if not text:
        return bool(default)
    if text in {"0", "false", "no", "off", "disabled"}:
        return False
    if text in {"1", "true", "yes", "on", "enabled"}:
        return True
    return bool(default)


def _sample_field_values(settings: dict[str, Any], maximum: float) -> list[float]:
    count = _settings_int(settings, "field_count", 1)
    if count == 1:
        return [float(maximum)]
    span = abs(float(maximum))
    if span <= 1e-9:
        return [0.0] * count
    return [float(value) for value in np.linspace(-span, span, count)]


def _saved_object_distance(surfaces: list[dict[str, Any]]) -> float:
    if not surfaces:
        return 100.0
    try:
        return max(float(surfaces[0].get("thickness", 100.0)), 1e-6)
    except Exception:
        return 100.0


def _saved_field_maximum(settings: dict[str, Any], surfaces: list[dict[str, Any]]) -> float:
    value = _settings_float(settings, "field_value", 0.0)
    object_mode = str(settings.get("object_mode", "Finite") or "Finite").strip()
    if object_mode == "Infinity":
        return float(value)
    field_type = str(settings.get("field_type", "Angle") or "Angle").strip()
    if field_type == "Angle":
        return float(_saved_object_distance(surfaces) * np.tan(np.deg2rad(value)))
    return float(value)


def _saved_launch_metadata(
    settings: dict[str, Any],
    surfaces: list[dict[str, Any]],
    trace_intent,
    *,
    sampling_mode: str = "saved_layout",
) -> dict[str, Any]:
    requested = _settings_int(settings, "field_count", 1)
    object_mode = str(settings.get("object_mode", "Finite") or "Finite").strip()
    basis = "angle" if object_mode == "Infinity" else "object height"
    unit = "deg" if basis == "angle" else "mm"
    maximum = _saved_field_maximum(settings, surfaces)
    active = bool(np.isfinite(maximum) and abs(float(maximum)) > 1e-12)
    values = _sample_field_values(settings, maximum) if active else [0.0]
    if not values:
        values = [0.0]
    unique_values = sorted({round(float(value), 12) for value in values})
    full_pupil = _settings_bool_value(settings.get("full_pupil", False))
    return {
        "launch_field_requested": int(requested),
        "launch_field_effective": int(max(1, len(unique_values))),
        "launch_field_basis": basis,
        "launch_field_unit": unit,
        "launch_field_min": float(min(values)),
        "launch_field_max": float(max(values)),
        "launch_field_active": bool(active),
        "launch_ray_count": _settings_int(settings, "ray_count", 5),
        "launch_pupil_pattern": str(settings.get("pupil_pattern", "Full Pupil" if full_pupil else "Meridional fan") or ""),
        "launch_trace_intent": str(getattr(trace_intent, "active", "") or ""),
        "launch_sampling_mode": str(sampling_mode or "saved_layout"),
    }


def _analysis_surface_index_from_specs(surfaces: list[dict[str, Any]]) -> int:
    candidates = [
        (index, _settings_float(spec, "diameter", 1.0, minimum=0.0))
        for index, spec in enumerate(surfaces[1:-1], start=1)
        if str(spec.get("surface", "") or "") not in {"Object", "Image"}
    ]
    if not candidates:
        return min(max(len(surfaces) - 1, 0), 1)
    return min(candidates, key=lambda item: max(float(item[1]), 1e-9))[0]


def _settings_pupil_pattern(settings: dict[str, Any], *, full_pupil: bool) -> str:
    label = str(settings.get("pupil_pattern", "Meridional fan") or "Meridional fan").strip()
    mapped = PUPIL_PATTERN_TO_KRAKEN.get(label)
    if mapped:
        return mapped
    return "hexapolar" if full_pupil else "fan"


def _pupil_bundle_from_saved_settings(pupil, settings: dict[str, Any]) -> tuple[np.ndarray, ...]:
    pupil.rad = _settings_float(settings, "pupil_rad", 0.0, minimum=0.0)
    pupil.theta = _settings_float(settings, "pupil_theta", 0.0)
    if str(getattr(pupil, "Ptype", "")).strip().lower() != "rand":
        return tuple(np.asarray(values, dtype=float) for values in pupil.Pattern2Field())
    numpy_state = np.random.get_state()
    try:
        np.random.seed(_settings_int(settings, "source_seed", 1, minimum=0))
        return tuple(np.asarray(values, dtype=float) for values in pupil.Pattern2Field())
    finally:
        np.random.set_state(numpy_state)


def _filter_saved_bundle_to_display_slice(
    bundle: tuple[np.ndarray, ...],
    settings: dict[str, Any],
    pupil_radius: float,
) -> tuple[np.ndarray, ...]:
    if _settings_bool_value(settings.get("full_pupil", False)):
        return bundle
    plane = normalize_projection_plane(str(settings.get("display_orientation", "YZ") or "YZ"))
    axis = "x" if plane == "XZ" else "y"
    cross = np.asarray(bundle[1 if axis == "x" else 0], dtype=float)
    tolerance = max(1e-8, 1e-9 * max(abs(float(pupil_radius)), 1.0))
    mask = np.abs(cross) <= tolerance
    if not np.any(mask) and cross.size:
        center = float(np.median(cross))
        mask = np.abs(cross - center) <= tolerance
    if not np.any(mask):
        return bundle
    selected = tuple(np.asarray(values, dtype=float)[mask] for values in bundle)
    selected_points = np.column_stack(selected)
    if selected_points.shape[0] <= 1:
        return selected
    _unique_rows, unique_idx = np.unique(
        np.round(selected_points, decimals=12),
        axis=0,
        return_index=True,
    )
    return tuple(values[np.sort(unique_idx)] for values in selected)


def _saved_meridional_fallback_bundles(system, surfaces: list[dict[str, Any]], settings: dict[str, Any]):
    optical_diams = [float(s.Diameter) for s in getattr(system, "SDT", [])[1:-1]] or [
        float(s.Diameter) for s in getattr(system, "SDT", [])
    ]
    max_radius = max(optical_diams, default=2.0) / 2.0
    ray_count = _settings_int(settings, "ray_count", 5)
    ray_height_factor = _settings_float(settings, "ray_height_factor", 0.8, minimum=0.0)
    if ray_count <= 1 or max_radius <= 1e-12:
        pupil_samples = np.asarray([0.0], dtype=float)
    else:
        pupil_samples = np.linspace(-max_radius * ray_height_factor, max_radius * ray_height_factor, ray_count)
    plane = normalize_projection_plane(str(settings.get("display_orientation", "YZ") or "YZ"))
    axis_index = 0 if plane == "XZ" else 1
    object_mode = str(settings.get("object_mode", "Finite") or "Finite").strip()
    field_values = _sample_field_values(settings, _saved_field_maximum(settings, surfaces))
    bundles: list[tuple[np.ndarray, ...]] = []
    if object_mode == "Infinity":
        for field_angle in field_values:
            angle_rad = np.deg2rad(float(field_angle))
            direction = np.zeros(3, dtype=float)
            direction[axis_index] = np.sin(angle_rad)
            direction[2] = np.cos(angle_rad)
            norm = float(np.linalg.norm(direction))
            if norm <= 1e-12:
                continue
            direction /= norm
            x_values = np.zeros(len(pupil_samples), dtype=float)
            y_values = np.zeros(len(pupil_samples), dtype=float)
            if axis_index == 0:
                x_values = pupil_samples.copy()
            else:
                y_values = pupil_samples.copy()
            bundles.append(
                (
                    x_values,
                    y_values,
                    np.zeros(len(pupil_samples), dtype=float),
                    np.full(len(pupil_samples), float(direction[0]), dtype=float),
                    np.full(len(pupil_samples), float(direction[1]), dtype=float),
                    np.full(len(pupil_samples), float(direction[2]), dtype=float),
                )
            )
        return bundles

    object_distance = _saved_object_distance(surfaces)
    for field_value in field_values:
        origin = np.zeros(3, dtype=float)
        origin[axis_index] = float(field_value)
        x_values: list[float] = []
        y_values: list[float] = []
        z_values: list[float] = []
        l_values: list[float] = []
        m_values: list[float] = []
        n_values: list[float] = []
        for pupil_value in pupil_samples:
            target = np.asarray((0.0, 0.0, object_distance), dtype=float)
            target[axis_index] = float(pupil_value)
            direction = target - origin
            norm = float(np.linalg.norm(direction))
            if norm <= 1e-12:
                continue
            direction /= norm
            x_values.append(float(origin[0]))
            y_values.append(float(origin[1]))
            z_values.append(float(origin[2]))
            l_values.append(float(direction[0]))
            m_values.append(float(direction[1]))
            n_values.append(float(direction[2]))
        if x_values:
            bundles.append(
                (
                    np.asarray(x_values, dtype=float),
                    np.asarray(y_values, dtype=float),
                    np.asarray(z_values, dtype=float),
                    np.asarray(l_values, dtype=float),
                    np.asarray(m_values, dtype=float),
                    np.asarray(n_values, dtype=float),
                )
            )
    return bundles


def _default_finite_cone_bundle_from_settings(
    settings: dict[str, Any],
    *,
    enabled: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    if not bool(enabled):
        return None
    source_model = str(settings.get("source_model", SOURCE_MODEL_DEFAULT) or SOURCE_MODEL_DEFAULT).strip()
    object_mode = str(settings.get("object_mode", "Infinity") or "Infinity").strip()
    cone_deg = _settings_float(settings, "source_cone_angle", 0.0, minimum=0.0)
    if source_model != SOURCE_MODEL_DEFAULT or cone_deg <= 1e-12:
        return None
    ray_count = _settings_int(settings, "ray_count", 5)
    if ray_count == 1:
        l_values = np.zeros(1, dtype=float)
        m_values = np.zeros(1, dtype=float)
        n_values = np.ones(1, dtype=float)
    else:
        cone_rad = float(np.deg2rad(cone_deg))
        rim_count = max(1, ray_count - 1)
        phi = np.linspace(0.0, 2.0 * np.pi, rim_count, endpoint=False)
        l_values = np.concatenate(([0.0], np.sin(cone_rad) * np.cos(phi))).astype(float)
        m_values = np.concatenate(([0.0], np.sin(cone_rad) * np.sin(phi))).astype(float)
        n_values = np.concatenate(([1.0], np.full(rim_count, np.cos(cone_rad), dtype=float))).astype(float)
    x_values = np.zeros(ray_count, dtype=float)
    y_values = np.zeros(ray_count, dtype=float)
    if object_mode != "Infinity":
        display_orientation = normalize_projection_plane(str(settings.get("display_orientation", "YZ") or "YZ").strip())
        axis_index = 0 if display_orientation == "XZ" else 1
        field_value = _settings_float(settings, "field_value", 0.0)
        if axis_index == 0:
            x_values.fill(field_value)
        else:
            y_values.fill(field_value)
    return orient_source_points_and_dirs(
        (
            _settings_float(settings, "source_x", 0.0),
            _settings_float(settings, "source_y", 0.0),
            _settings_float(settings, "source_z", 0.0),
        ),
        (
            _settings_float(settings, "source_l", 0.0),
            _settings_float(settings, "source_m", 0.0),
            _settings_float(settings, "source_n", 1.0),
        ),
        x_values,
        y_values,
        np.zeros(ray_count, dtype=float),
        l_values,
        m_values,
        n_values,
    )


def source_frame_vectors_from_direction(direction: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    w = np.asarray(direction, dtype=float).reshape(-1)
    if w.size < 3:
        w = np.pad(w, (0, 3 - w.size), constant_values=0.0)
        w[2] = 1.0
    w = w[:3]
    norm = float(np.linalg.norm(w))
    if norm <= 1e-12:
        w = np.asarray((0.0, 0.0, 1.0), dtype=float)
    else:
        w = w / norm
    reference = np.asarray((0.0, 0.0, 1.0), dtype=float)
    if abs(float(np.dot(w, reference))) > 0.94:
        reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
    u = np.cross(reference, w)
    u_norm = float(np.linalg.norm(u))
    if u_norm <= 1e-12:
        u = np.asarray((1.0, 0.0, 0.0), dtype=float)
        u_norm = 1.0
    u = u / u_norm
    v = np.cross(w, u)
    v_norm = float(np.linalg.norm(v))
    if v_norm <= 1e-12:
        v = np.asarray((0.0, 1.0, 0.0), dtype=float)
        v_norm = 1.0
    v = v / v_norm
    return u, v, w


def orient_source_points_and_dirs(
    origin: Any,
    direction: Any,
    x_values: Any,
    y_values: Any,
    z_values: Any,
    l_values: Any,
    m_values: Any,
    n_values: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    origin_arr = np.asarray(origin, dtype=float).reshape(-1)
    if origin_arr.size < 3:
        origin_arr = np.pad(origin_arr, (0, 3 - origin_arr.size), constant_values=0.0)
    origin_arr = origin_arr[:3]
    u, v, w = source_frame_vectors_from_direction(direction)
    x_arr, y_arr, z_arr, l_arr, m_arr, n_arr = (
        np.asarray(values, dtype=float).reshape(-1)
        for values in (x_values, y_values, z_values, l_values, m_values, n_values)
    )
    points = (
        origin_arr[None, :]
        + x_arr[:, None] * u[None, :]
        + y_arr[:, None] * v[None, :]
        + z_arr[:, None] * w[None, :]
    )
    dirs = (
        l_arr[:, None] * u[None, :]
        + m_arr[:, None] * v[None, :]
        + n_arr[:, None] * w[None, :]
    )
    norms = np.linalg.norm(dirs, axis=1)
    norms = np.where(norms > 1e-12, norms, 1.0)
    dirs = dirs / norms[:, None]
    return (
        points[:, 0],
        points[:, 1],
        points[:, 2],
        dirs[:, 0],
        dirs[:, 1],
        dirs[:, 2],
    )


def random_cone_directions(ray_count: int, cone_angle_deg: float, rng: np.random.Generator):
    count = max(1, int(ray_count))
    cone_rad = max(float(np.deg2rad(cone_angle_deg)), 0.0)
    if cone_rad <= 1e-12:
        return (
            np.zeros(count, dtype=float),
            np.zeros(count, dtype=float),
            np.ones(count, dtype=float),
        )
    cos_min = float(np.cos(cone_rad))
    cos_theta = rng.uniform(cos_min, 1.0, count)
    sin_theta = np.sqrt(np.clip(1.0 - cos_theta * cos_theta, 0.0, 1.0))
    phi = rng.uniform(0.0, 2.0 * np.pi, count)
    return (
        sin_theta * np.cos(phi),
        sin_theta * np.sin(phi),
        cos_theta,
    )


def sample_source_disk_points(radius: float, ray_count: int) -> np.ndarray:
    count = max(1, int(ray_count))
    radius = max(float(radius), 0.0)
    if count == 1 or radius <= 1e-12:
        return np.asarray([[0.0, 0.0]], dtype=float)
    if count <= 9:
        edge = radius * min(np.sqrt((count - 1) / float(count)), 0.985)
        y_values = np.linspace(-edge, edge, count)
        return np.column_stack((np.zeros(count, dtype=float), y_values.astype(float)))
    points = [[0.0, 0.0]]
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    for index in range(1, count):
        r = radius * np.sqrt(index / float(count))
        theta = index * golden_angle
        points.append([r * np.cos(theta), r * np.sin(theta)])
    return np.asarray(points, dtype=float)


def settings_panel_scene_source(settings: dict[str, Any], *, wavelength: float | None = None, sample_count: int | None = None) -> SceneSource3D | None:
    model = str(settings.get("source_model", SOURCE_MODEL_DEFAULT) or SOURCE_MODEL_DEFAULT).strip()
    if model not in SOURCE_MODEL_VALUES:
        model = SOURCE_MODEL_DEFAULT
    if model == SOURCE_MODEL_DEFAULT:
        return None
    wavelength_value = float(wavelength if wavelength is not None else _settings_float(settings, "wavelength", 0.55, minimum=1e-12))
    ray_count = int(sample_count if sample_count is not None else _settings_int(settings, "ray_count", 5))
    spec: dict[str, Any] = {
        "source_id": "source:0",
        "name": "Source 1",
        "enabled": True,
        "physical": True,
        "role": "illumination",
        "model": model,
        "ray_count": ray_count,
        "power": _settings_float(settings, "source_power", 1.0, minimum=0.0),
        "wavelength": wavelength_value,
        "radius": _settings_float(settings, "source_radius", 1.0, minimum=0.0),
        "cone_deg": _settings_float(settings, "source_cone_angle", 0.0, minimum=0.0),
        "seed": _settings_int(settings, "source_seed", 1, minimum=0),
        "source_x": _settings_float(settings, "source_x", 0.0),
        "source_y": _settings_float(settings, "source_y", 0.0),
        "source_z": _settings_float(settings, "source_z", 0.0),
        "source_l": _settings_float(settings, "source_l", 0.0),
        "source_m": _settings_float(settings, "source_m", 0.0),
        "source_n": _settings_float(settings, "source_n", 1.0),
        "angular_weight": str(settings.get("source_angular_weight", SOURCE_ANGULAR_WEIGHT_DEFAULT) or SOURCE_ANGULAR_WEIGHT_DEFAULT),
    }
    if model == "Gaussian beam":
        spec.update(
            {
                "waist_radius": _settings_float(settings, "gaussian_waist_radius", 0.5, minimum=1e-12),
                "waist_offset": _settings_float(settings, "gaussian_waist_offset", 0.0),
                "m2": _settings_float(settings, "gaussian_m2", 1.0, minimum=1e-12),
                "gaussian_input_mode": str(settings.get("gaussian_input_mode", "Waist + offset") or "Waist + offset"),
                "beam_diameter": _settings_float(settings, "gaussian_beam_diameter", 1.0, minimum=0.0),
                "full_divergence_mrad": _settings_float(settings, "gaussian_full_divergence", 1.0, minimum=0.0),
            }
        )
    return scene_source_from_spec(
        {str(key): scene_source_setting_value(value) for key, value in spec.items()},
        0,
        wavelength=wavelength_value,
        sample_count=ray_count,
        default_ray_count=ray_count,
        default_radius=float(spec["radius"]),
        default_cone_deg=float(spec["cone_deg"]),
        source_model_values=SOURCE_MODEL_VALUES,
        source_model_default=SOURCE_MODEL_DEFAULT,
        angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
    )


def scene_sources_from_settings(settings: dict[str, Any], *, wavelength: float | None = None, sample_count: int | None = None) -> list[SceneSource3D]:
    wavelength_value = float(wavelength if wavelength is not None else _settings_float(settings, "wavelength", 0.55, minimum=1e-12))
    explicit_specs = normalize_scene_source_specs(settings.get("scene_sources", []))
    if explicit_specs:
        sources = [
            scene_source_from_spec(
                spec,
                index,
                wavelength=wavelength_value,
                sample_count=sample_count,
                default_ray_count=_settings_int(settings, "ray_count", 5),
                default_radius=_settings_float(settings, "source_radius", 1.0, minimum=0.0),
                default_cone_deg=_settings_float(settings, "source_cone_angle", 0.0, minimum=0.0),
                source_model_values=SOURCE_MODEL_VALUES,
                source_model_default=SOURCE_MODEL_DEFAULT,
                angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
            )
            for index, spec in enumerate(explicit_specs)
        ]
        if any(bool(source.enabled) and bool(source.physical) for source in sources):
            return sources
    panel_source = settings_panel_scene_source(settings, wavelength=wavelength_value, sample_count=sample_count)
    return [] if panel_source is None else [panel_source]


def build_scene_source_bundle(source: SceneSource3D):
    settings = dict(source.settings or {})
    model = str(source.model or settings.get("source_model", "Collimated disk source"))
    ray_count = max(1, int(source.ray_count))
    radius = source_spec_float(settings, ("radius", "source_radius", "launch_radius"), 1.0, minimum=0.0)
    origin = np.asarray(source.origin, dtype=float)
    direction = np.asarray(source.direction, dtype=float)
    if model == SOURCE_MODEL_ZEMAX_RAYFILE:
        if sample_zemax_rayfile is None:
            return None
        raw_rayfile_path = str(settings.get("rayfile_path", "") or "").strip()
        if not raw_rayfile_path:
            return None
        rayfile_path = Path(raw_rayfile_path).expanduser()
        if not rayfile_path.exists():
            return None
        x_values, y_values, z_values, l_values, m_values, n_values, _flux = sample_zemax_rayfile(rayfile_path, ray_count)
        return orient_source_points_and_dirs(origin, direction, x_values, y_values, z_values, l_values, m_values, n_values)
    if model == "Gaussian beam":
        waist_radius = source_spec_float(settings, ("waist_radius", "gaussian_waist_radius"), max(radius, 0.5), minimum=1e-9)
        waist_offset = source_spec_float(settings, ("waist_offset", "gaussian_waist_offset"), 0.0)
        m2 = source_spec_float(settings, ("m2", "gaussian_m2"), 1.0, minimum=1e-9)
        wavelength_um = float(source.wavelength if source.wavelength is not None else 0.55)
        wavelength_mm = max(wavelength_um * 1e-3, 1e-12)
        z_rayleigh = np.pi * waist_radius * waist_radius / (wavelength_mm * m2)
        q_value = complex(waist_offset, float(z_rayleigh))
        inverse_q = 1.0 / q_value if abs(q_value) > 1e-18 else complex(0.0, 0.0)
        real_inverse = float(np.real(inverse_q))
        wavefront_radius = np.inf if abs(real_inverse) <= 1e-18 else float(1.0 / real_inverse)
        launch_radius = waist_radius * np.sqrt(1.0 + (waist_offset / max(float(z_rayleigh), 1e-12)) ** 2)
        disk_points = sample_source_disk_points(launch_radius, ray_count)
        x_offsets = disk_points[:, 0].astype(float)
        y_offsets = disk_points[:, 1].astype(float)
        x_slopes = np.zeros_like(x_offsets)
        y_slopes = np.zeros_like(y_offsets)
        if np.isfinite(wavefront_radius) and abs(wavefront_radius) > 1e-12:
            x_slopes = x_offsets / wavefront_radius
            y_slopes = y_offsets / wavefront_radius
        l_values = x_slopes.astype(float)
        m_values = y_slopes.astype(float)
        n_values = np.ones(ray_count, dtype=float)
        norms = np.sqrt(l_values * l_values + m_values * m_values + n_values * n_values)
        norms = np.where(norms > 1e-12, norms, 1.0)
        return orient_source_points_and_dirs(
            origin,
            direction,
            x_offsets,
            y_offsets,
            np.zeros(ray_count, dtype=float),
            l_values / norms,
            m_values / norms,
            n_values / norms,
        )
    if model == "Collimated disk source":
        disk_points = sample_source_disk_points(radius, ray_count)
        cone_angle = source_spec_float(settings, ("cone_deg", "source_cone_angle"), 0.0, minimum=0.0)
        if cone_angle > 1e-12:
            seed = int(round(source_spec_float(settings, "seed", 1, minimum=0.0))) % (2**32 - 1)
            rng = np.random.default_rng(seed)
            l_values, m_values, n_values = random_cone_directions(ray_count, cone_angle, rng)
        else:
            l_values = np.zeros(ray_count, dtype=float)
            m_values = np.zeros(ray_count, dtype=float)
            n_values = np.ones(ray_count, dtype=float)
        return orient_source_points_and_dirs(
            origin,
            direction,
            disk_points[:, 0].astype(float),
            disk_points[:, 1].astype(float),
            np.zeros(ray_count, dtype=float),
            l_values,
            m_values,
            n_values,
        )
    seed = int(round(source_spec_float(settings, "seed", 1, minimum=0.0))) % (2**32 - 1)
    rng = np.random.default_rng(seed)
    cone_angle = source_spec_float(settings, ("cone_deg", "source_cone_angle"), 0.0, minimum=0.0)
    l_values, m_values, n_values = random_cone_directions(ray_count, cone_angle, rng)
    z_values = np.zeros(ray_count, dtype=float)
    if model == "Random circle source":
        r = radius * np.sqrt(rng.uniform(0.0, 1.0, ray_count))
        theta = rng.uniform(0.0, 2.0 * np.pi, ray_count)
        x_values = r * np.cos(theta)
        y_values = r * np.sin(theta)
    elif model == "Random square source":
        x_values = rng.uniform(-radius, radius, ray_count)
        y_values = rng.uniform(-radius, radius, ray_count)
    elif model == "Random line source":
        x_values = rng.uniform(-radius, radius, ray_count)
        y_values = np.zeros(ray_count, dtype=float)
    else:
        x_values = np.zeros(ray_count, dtype=float)
        y_values = np.zeros(ray_count, dtype=float)
    return orient_source_points_and_dirs(
        origin,
        direction,
        np.asarray(x_values, dtype=float),
        np.asarray(y_values, dtype=float),
        z_values,
        np.asarray(l_values, dtype=float),
        np.asarray(m_values, dtype=float),
        np.asarray(n_values, dtype=float),
    )


def _surface_advanced(spec: dict[str, Any]) -> dict[str, Any]:
    advanced = spec.get("advanced", {})
    return advanced if isinstance(advanced, dict) else {}


def _surface_index_from_setting(value: Any, surfaces: list[dict[str, Any]]) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"auto", "none", "off", "disabled"}:
        return None
    if text.upper().startswith("S"):
        text = text[1:]
    text = text.split(":", 1)[0].strip()
    try:
        index = int(float(text))
    except Exception:
        return None
    return index if 0 <= index < len(surfaces) else None


def _surface_is_saved_detector(spec: dict[str, Any]) -> bool:
    surface = str(spec.get("surface", "") or "").strip().lower()
    if surface == "detector":
        return True
    advanced = _surface_advanced(spec)
    element = advanced.get("Element", {})
    element = element if isinstance(element, dict) else {}
    role_key = "".join(ch for ch in str(element.get("arm_role", "") or "").strip().lower() if ch.isalnum())
    if role_key in {"detector", "image"}:
        return True
    detector_settings = advanced.get("Detector")
    return isinstance(detector_settings, dict) and bool(detector_settings)


def saved_nonseq_terminal_policy(
    surfaces: list[dict[str, Any]],
    settings: dict[str, Any],
    *,
    use_nonseq: bool,
) -> dict[str, Any]:
    if not bool(use_nonseq):
        return {}
    detectors = {
        int(index)
        for index, spec in enumerate(surfaces)
        if _surface_is_saved_detector(spec)
    }
    target_surface = _surface_index_from_setting(settings.get("nonseq_target_surface"), surfaces)
    if target_surface is not None:
        detectors.add(int(target_surface))
    return {
        "terminal_target_surface": target_surface,
        "terminal_detector_surfaces": sorted(detectors),
        "terminal_policy_source": "saved_nonseq_trace_request",
    }


def source_metadata_for_bundle(
    bundle,
    wavelength: float,
    source: SceneSource3D,
    *,
    terminal_policy: dict[str, Any] | None = None,
    launch_metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    x_values, y_values, z_values, l_values, m_values, n_values = (
        np.asarray(values, dtype=float).reshape(-1) for values in bundle
    )
    source_power = np.nan if source.power is None else float(source.power)
    source_weight = np.nan if source.weight_per_ray is None else float(source.weight_per_ray)
    terminal_policy = dict(terminal_policy or {})
    launch_metadata = dict(launch_metadata or {})
    metadata: list[dict[str, Any]] = []
    for index in range(len(x_values)):
        record = {
            "source_xyz": [float(x_values[index]), float(y_values[index]), float(z_values[index])],
            "source_lmn": [float(l_values[index]), float(m_values[index]), float(n_values[index])],
            "source_power": source_power,
            "source_weight": source_weight,
            "source_id": source.source_id,
            "source_name": source.name,
            "source_role": source.role,
            "source_model": str(source.model or ""),
            "source_wavelength": float(wavelength),
        }
        record.update(launch_metadata)
        record.update(terminal_policy)
        metadata.append(record)
    return metadata


def layout_uses_nonseq(surfaces: list[dict[str, Any]], settings: dict[str, Any] | None = None) -> bool:
    requested = "Auto" if settings is None else settings.get("trace_mode", "Auto")
    return _layout_uses_nonseq(surfaces, settings or {}, requested=requested)


def trace_bundle(trace_loop, bundle, wavelength: float, rays, *, clean: int, metadata: list[dict[str, Any]] | None = None) -> None:
    try:
        trace_loop(*bundle, wavelength, rays, clean=clean, source_metadata=metadata or [])
    except TypeError:
        trace_loop(*bundle, wavelength, rays, clean=clean)


def build_saved_pupil_field_bundles(system, surfaces: list[dict[str, Any]], settings: dict[str, Any], kos_module):
    if str(settings.get("source_model", SOURCE_MODEL_DEFAULT) or SOURCE_MODEL_DEFAULT).strip() != SOURCE_MODEL_DEFAULT:
        return []
    wavelength = _settings_float(settings, "wavelength", 0.55, minimum=1e-12)
    ray_count = _settings_int(settings, "ray_count", 5)
    full_pupil = _settings_bool_value(settings.get("full_pupil", False))
    try:
        pupil = kos_module.PupilCalc(
            system,
            _analysis_surface_index_from_specs(surfaces),
            wavelength,
            str(settings.get("aperture_type", "EPD") or "EPD"),
            _settings_float(settings, "aperture_value", 4.0, minimum=1e-12),
        )
    except Exception:
        return _saved_meridional_fallback_bundles(system, surfaces, settings)
    pupil.Samp = max(3, ray_count) if full_pupil else max(1, ray_count // 2)
    pupil.Ptype = _settings_pupil_pattern(settings, full_pupil=full_pupil)
    object_mode = str(settings.get("object_mode", "Finite") or "Finite").strip()
    pupil.FieldType = "angle" if object_mode == "Infinity" else "height"
    field_values = _sample_field_values(settings, _saved_field_maximum(settings, surfaces))
    bundles: list[tuple[np.ndarray, ...]] = []
    pupil_radius = 1.0
    try:
        pupil_radius = abs(float(getattr(pupil, "RadPupInp", 1.0)))
    except Exception:
        pupil_radius = 1.0
    plane = normalize_projection_plane(str(settings.get("display_orientation", "YZ") or "YZ"))
    axis = "x" if plane == "XZ" else "y"
    for field_value in field_values:
        value = float(field_value)
        pupil.FieldX = value if axis == "x" else 0.0
        pupil.FieldY = value if axis == "y" else 0.0
        try:
            bundle = _pupil_bundle_from_saved_settings(pupil, settings)
        except Exception:
            continue
        if len(bundle) != 6 or len(np.asarray(bundle[0])) <= 0:
            continue
        if not full_pupil:
            bundle = _filter_saved_bundle_to_display_slice(bundle, settings, pupil_radius)
        if len(np.asarray(bundle[0])) > 0:
            bundles.append(bundle)
    return bundles


def _saved_image_catch_diameter(surfaces: list[dict[str, Any]]) -> float | None:
    if not surfaces or str(surfaces[-1].get("surface", "") or "") != "Image":
        return None
    try:
        current = max(float(surfaces[-1].get("diameter", surfaces[-1].get("Diameter", 1.0))), 1.0)
    except Exception:
        current = 1.0
    axial_span = 0.0
    max_clear = current
    for spec in surfaces:
        try:
            axial_span += abs(float(spec.get("thickness", spec.get("Thickness", 0.0)) or 0.0))
        except Exception:
            pass
        try:
            max_clear = max(max_clear, abs(float(spec.get("diameter", spec.get("Diameter", 0.0)) or 0.0)))
        except Exception:
            pass
    catch = max(current, 4.0 * axial_span, 20.0 * max_clear, 1000.0)
    return float(catch) if catch > current + 1e-9 else None


def _temporarily_set_saved_system_surface_diameter(system, surface_index: int, diameter: float):
    edits: list[tuple[object, float]] = []
    seen_surfaces: set[int] = set()
    if system is None or surface_index < 0:
        return lambda: None
    for attr in ("SDT", "SDT_0"):
        surface_list = getattr(system, attr, None)
        try:
            surface = surface_list[surface_index]
        except Exception:
            continue
        surface_id = id(surface)
        if surface_id in seen_surfaces:
            continue
        seen_surfaces.add(surface_id)
        if not hasattr(surface, "Diameter"):
            continue
        try:
            previous = float(surface.Diameter)
            surface.Diameter = float(diameter)
            edits.append((surface, previous))
        except Exception:
            continue

    def restore() -> None:
        for surface, previous in edits:
            try:
                surface.Diameter = previous
            except Exception:
                pass

    return restore


def build_saved_layout_rays(system, surfaces: list[dict[str, Any]], settings: dict[str, Any], kos_module):
    rays = kos_module.raykeeper(system)
    wavelength = _settings_float(settings, "wavelength", 0.55, minimum=1e-12)
    trace_intent = resolve_trace_intent(
        surfaces,
        settings,
        requested=settings.get("trace_mode", "Auto"),
        can_folded=False,
        ns_trace_available=hasattr(kos_module, "NsTraceLoop") or hasattr(system, "NsTrace"),
    )
    use_nonseq = bool(trace_intent.use_nonseq)
    terminal_policy = saved_nonseq_terminal_policy(surfaces, settings, use_nonseq=use_nonseq)
    base_launch_metadata = _saved_launch_metadata(settings, surfaces, trace_intent)
    sources = [
        source
        for source in scene_sources_from_settings(settings, wavelength=wavelength)
        if bool(source.enabled) and bool(source.physical)
    ]
    if sources:
        trace_loop = kos_module.NsTraceLoop if use_nonseq and hasattr(kos_module, "NsTraceLoop") else kos_module.TraceLoop
        clean = 1
        for source in sources:
            bundle = build_scene_source_bundle(source)
            if bundle is None or len(np.asarray(bundle[0]).reshape(-1)) <= 0:
                continue
            trace_bundle(
                trace_loop,
                bundle,
                float(source.wavelength if source.wavelength is not None else wavelength),
                rays,
                clean=clean,
                metadata=source_metadata_for_bundle(
                    bundle,
                    float(source.wavelength if source.wavelength is not None else wavelength),
                    source,
                    terminal_policy=terminal_policy,
                    launch_metadata={
                        **base_launch_metadata,
                        "launch_ray_count": int(source.ray_count),
                        "launch_sampling_mode": "saved_scene_source",
                    },
                ),
            )
            clean = 0
        return rays

    default_finite_cone = _default_finite_cone_bundle_from_settings(settings, enabled=use_nonseq)
    default_source = SceneSource3D(
        source_id="source:pupil_field",
        name="Pupil / field",
        role="pupil_field_reference",
        model=SOURCE_MODEL_DEFAULT,
        physical=False,
        ray_count=_settings_int(settings, "ray_count", 5),
        wavelength=wavelength,
    )
    if default_finite_cone is not None:
        trace_loop = kos_module.NsTraceLoop if use_nonseq and hasattr(kos_module, "NsTraceLoop") else kos_module.TraceLoop
        trace_bundle(
            trace_loop,
            default_finite_cone,
            wavelength,
            rays,
            clean=1,
            metadata=source_metadata_for_bundle(
                default_finite_cone,
                wavelength,
                default_source,
                terminal_policy=terminal_policy,
                launch_metadata={
                    **base_launch_metadata,
                    "launch_sampling_mode": "saved_finite_cone",
                },
            ),
        )
        return rays

    pupil_field_bundles = build_saved_pupil_field_bundles(system, surfaces, settings, kos_module)
    if pupil_field_bundles:
        trace_loop = kos_module.NsTraceLoop if use_nonseq and hasattr(kos_module, "NsTraceLoop") else kos_module.TraceLoop
        restore_image_catch = lambda: None
        image_catch_diameter = None if use_nonseq else _saved_image_catch_diameter(surfaces)
        if image_catch_diameter is not None:
            restore_image_catch = _temporarily_set_saved_system_surface_diameter(
                system,
                len(surfaces) - 1,
                image_catch_diameter,
            )
        clean = 1
        try:
            for bundle in pupil_field_bundles:
                trace_bundle(
                    trace_loop,
                    bundle,
                    wavelength,
                    rays,
                    clean=clean,
                    metadata=source_metadata_for_bundle(
                        bundle,
                        wavelength,
                        default_source,
                        terminal_policy=terminal_policy,
                        launch_metadata={
                            **base_launch_metadata,
                            "launch_sampling_mode": "saved_pupil_field",
                        },
                    ),
                )
                clean = 0
        finally:
            restore_image_catch()
        return rays

    optical_diams = [float(s.Diameter) for s in system.SDT[1:-1]] or [float(s.Diameter) for s in system.SDT]
    max_radius = max(optical_diams, default=2.0) / 2.0
    ray_count = _settings_int(settings, "ray_count", 5)
    ray_height_factor = _settings_float(settings, "ray_height_factor", 0.8, minimum=0.0)
    if ray_count <= 1 or max_radius <= 1e-12:
        ray_heights = [0.0]
    else:
        edge = max_radius * ray_height_factor
        ray_heights = np.linspace(-edge, edge, ray_count)
    bundle = (
        np.zeros(len(ray_heights), dtype=float),
        np.asarray(ray_heights, dtype=float),
        np.zeros(len(ray_heights), dtype=float),
        np.zeros(len(ray_heights), dtype=float),
        np.zeros(len(ray_heights), dtype=float),
        np.ones(len(ray_heights), dtype=float),
    )
    trace_loop = kos_module.NsTraceLoop if use_nonseq and hasattr(kos_module, "NsTraceLoop") else kos_module.TraceLoop
    trace_bundle(
        trace_loop,
        bundle,
        wavelength,
        rays,
        clean=1,
        metadata=source_metadata_for_bundle(
            bundle,
            wavelength,
            default_source,
            terminal_policy=terminal_policy,
            launch_metadata={
                **base_launch_metadata,
                "launch_sampling_mode": "saved_meridional_fallback",
            },
        ),
    )
    return rays
