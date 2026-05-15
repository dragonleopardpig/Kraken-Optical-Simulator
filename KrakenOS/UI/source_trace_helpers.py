from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.scene_geometry import SceneSource3D
from KrakenOS.UI.scene_projector import normalize_projection_plane
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


def _default_finite_cone_bundle_from_settings(
    settings: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    source_model = str(settings.get("source_model", SOURCE_MODEL_DEFAULT) or SOURCE_MODEL_DEFAULT).strip()
    object_mode = str(settings.get("object_mode", "Infinity") or "Infinity").strip()
    cone_deg = _settings_float(settings, "source_cone_angle", 0.0, minimum=0.0)
    if source_model != SOURCE_MODEL_DEFAULT or object_mode == "Infinity" or cone_deg <= 1e-12:
        return None
    ray_count = _settings_int(settings, "ray_count", 5)
    angles_deg = np.asarray([0.0] if ray_count == 1 else np.linspace(-cone_deg, cone_deg, ray_count), dtype=float)
    angles_rad = np.deg2rad(angles_deg)
    display_orientation = normalize_projection_plane(str(settings.get("display_orientation", "YZ") or "YZ").strip())
    axis_index = 0 if display_orientation == "XZ" else 1
    field_value = _settings_float(settings, "field_value", 0.0)
    x_values = np.zeros(ray_count, dtype=float)
    y_values = np.zeros(ray_count, dtype=float)
    if axis_index == 0:
        x_values.fill(field_value)
    else:
        y_values.fill(field_value)
    l_values = np.zeros(ray_count, dtype=float)
    m_values = np.zeros(ray_count, dtype=float)
    if axis_index == 0:
        l_values = np.sin(angles_rad).astype(float)
    else:
        m_values = np.sin(angles_rad).astype(float)
    n_values = np.cos(angles_rad).astype(float)
    return (
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


def source_metadata_for_bundle(bundle, wavelength: float, source: SceneSource3D) -> list[dict[str, Any]]:
    x_values, y_values, z_values, l_values, m_values, n_values = (
        np.asarray(values, dtype=float).reshape(-1) for values in bundle
    )
    source_power = np.nan if source.power is None else float(source.power)
    source_weight = np.nan if source.weight_per_ray is None else float(source.weight_per_ray)
    metadata: list[dict[str, Any]] = []
    for index in range(len(x_values)):
        metadata.append(
            {
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
        )
    return metadata


def layout_uses_nonseq(surfaces: list[dict[str, Any]]) -> bool:
    return any(
        spec.get("surface") in {"Beam Splitter", "Diffuse Object", "Object Target"}
        or str(spec.get("advanced", {}).get("Solid_3d_stl", "") or "").strip() not in {"", "None"}
        for spec in list(surfaces or [])
        if isinstance(spec, dict)
    )


def trace_bundle(trace_loop, bundle, wavelength: float, rays, *, clean: int, metadata: list[dict[str, Any]] | None = None) -> None:
    try:
        trace_loop(*bundle, wavelength, rays, clean=clean, source_metadata=metadata or [])
    except TypeError:
        trace_loop(*bundle, wavelength, rays, clean=clean)


def build_saved_layout_rays(system, surfaces: list[dict[str, Any]], settings: dict[str, Any], kos_module):
    rays = kos_module.raykeeper(system)
    wavelength = _settings_float(settings, "wavelength", 0.55, minimum=1e-12)
    use_nonseq = layout_uses_nonseq(surfaces)
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
                metadata=source_metadata_for_bundle(bundle, float(source.wavelength if source.wavelength is not None else wavelength), source),
            )
            clean = 0
        return rays

    default_finite_cone = _default_finite_cone_bundle_from_settings(settings)
    if default_finite_cone is not None:
        trace_loop = kos_module.NsTraceLoop if use_nonseq and hasattr(kos_module, "NsTraceLoop") else kos_module.TraceLoop
        trace_bundle(trace_loop, default_finite_cone, wavelength, rays, clean=1)
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
    trace_fn = system.NsTrace if use_nonseq and hasattr(system, "NsTrace") else system.Trace
    for y0 in ray_heights:
        trace_fn([0.0, float(y0), 0.0], [0.0, 0.0, 1.0], wavelength)
        rays.push()
    return rays
