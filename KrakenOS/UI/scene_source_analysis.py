from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.scene_geometry import SceneSource3D


def scene_source_setting_value(value: object):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, np.ndarray):
        return [scene_source_setting_value(item) for item in value.reshape(-1).tolist()]
    if isinstance(value, (list, tuple)):
        return [scene_source_setting_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): scene_source_setting_value(item) for key, item in value.items()}
    if isinstance(value, float):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    try:
        return float(value)
    except Exception:
        return str(value)


def normalize_scene_source_specs(value: object) -> list[dict[str, object]]:
    if value is None or value == "":
        return []
    if isinstance(value, dict):
        if isinstance(value.get("sources"), (list, tuple)):
            raw_items = value.get("sources", [])
        elif isinstance(value.get("scene_sources"), (list, tuple)):
            raw_items = value.get("scene_sources", [])
        else:
            raw_items = [value]
    elif isinstance(value, (list, tuple)):
        raw_items = list(value)
    else:
        return []
    specs: list[dict[str, object]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        spec = {str(key): scene_source_setting_value(val) for key, val in item.items()}
        spec.setdefault("source_id", f"source:{index}")
        spec.setdefault("name", f"Source {index + 1}")
        specs.append(spec)
    return specs


def dedupe_scene_source_ids(specs: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    output: list[dict[str, object]] = []
    for index, raw in enumerate(specs):
        spec = dict(raw)
        base = str(spec.get("source_id", "") or f"source:{index}").strip() or f"source:{index}"
        source_id = base
        suffix = 2
        while source_id in seen:
            source_id = f"{base}_{suffix}"
            suffix += 1
        seen.add(source_id)
        spec["source_id"] = source_id
        spec.setdefault("name", f"Source {index + 1}")
        output.append({str(key): scene_source_setting_value(value) for key, value in spec.items()})
    return output


def source_spec_bool(spec: dict[str, object], keys, default: bool) -> bool:
    """Read the first present boolean key, allowing the same alias tuples as float settings."""
    if isinstance(keys, str):
        keys = (keys,)
    value = default
    for key in keys:
        if key in spec:
            value = spec.get(key, default)
            break
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", "disabled"}
    return bool(value)


def scene_source_spec_is_face_bound_marker(spec: object) -> bool:
    """A face-anchored illumination source (Feature B, bugs/0264) is a *designation marker*, not a
    trace driver. The user marks a CAD/STL face as an emitter and it tracks that face -- but the image
    plane, detector, and optical axis are IMAGING conjugates fixed by the object, so a face-bound
    illumination source must NEVER replace the imaging trace (bugs/0266: doing so relocated the image
    plane + detector onto the beam-splitter's illumination face and exploded the optical axis).

    Detected by a resolved ``face_anchor_row`` >= 0. The key survives spec normalization AND rides in
    ``SceneSource3D.settings``, so this one predicate covers both the dict-spec and the dataclass form.
    """
    if isinstance(spec, dict):
        raw = spec.get("face_anchor_row", None)
    else:
        settings = getattr(spec, "settings", None)
        raw = settings.get("face_anchor_row", None) if isinstance(settings, dict) else None
    if raw is None:
        return False
    try:
        return int(round(float(raw))) >= 0
    except (TypeError, ValueError):
        return False


def source_spec_float(spec: dict[str, object], keys, default: float = 0.0, *, minimum: float | None = None) -> float:
    if isinstance(keys, str):
        keys = (keys,)
    value = default
    for key in keys:
        if key not in spec:
            continue
        try:
            value = float(spec.get(key))
            break
        except Exception:
            continue
    if not np.isfinite(value):
        value = default
    if minimum is not None:
        value = max(float(minimum), float(value))
    return float(value)


def source_spec_vector(spec: dict[str, object], vector_keys, component_keys, default) -> np.ndarray:
    for key in vector_keys:
        value = spec.get(key)
        if isinstance(value, (list, tuple, np.ndarray)):
            try:
                arr = np.asarray(value, dtype=float).reshape(-1)
                if arr.size >= 3 and np.all(np.isfinite(arr[:3])):
                    return arr[:3].astype(float)
            except Exception:
                pass
    return np.asarray(
        [source_spec_float(spec, key, float(default[index])) for index, key in enumerate(component_keys)],
        dtype=float,
    )


COAXIAL_ILLUMINATOR_KEY = "coaxial_illuminator"
COUPLE_TO_IMAGING_LAUNCH_KEY = "couple_to_imaging_launch"


def coaxial_illuminator_descriptor(spec: object) -> dict[str, object] | None:
    """bugs/0292: read a coaxial-illuminator descriptor off a scene-source spec (or a
    ``SceneSource3D.settings`` dict), or ``None`` for a non-coaxial / non-illuminator spec.

    Attached at "Add Illumination Source (LED)" time (source_modeling.add_illumination_led_source) when the
    LED feeds the object via a folding beam splitter.  It records the RAW illuminator aperture plus the
    fold geometry -- NOT a pre-computed 38.9 mm -- so the effective object-plane footprint (aperture along
    the fold axis foreshortened by cos(fold_angle)) can be derived generally at draw time by
    ``source_object_coupling.coaxial_illuminator_footprint_map``.  The keys survive spec normalization
    (``normalize_scene_source_specs`` keeps arbitrary keys) and ride in ``SceneSource3D.settings``.
    """
    if isinstance(spec, dict):
        settings: object = spec
    else:
        settings = getattr(spec, "settings", None)
    if not isinstance(settings, dict):
        return None
    if not source_spec_bool(settings, COAXIAL_ILLUMINATOR_KEY, False):
        return None
    aperture_fold = source_spec_float(
        settings, ("coaxial_aperture_fold_mm", "aperture_fold_mm"), 0.0, minimum=0.0
    )
    aperture_perp = source_spec_float(
        settings, ("coaxial_aperture_perp_mm", "aperture_perp_mm"), 0.0, minimum=0.0
    )
    if not (aperture_fold > 0.0 and aperture_perp > 0.0):
        return None
    fold_angle = source_spec_float(settings, ("coaxial_fold_angle_deg", "fold_angle_deg"), 45.0)
    axis_raw = str(settings.get("coaxial_fold_axis", settings.get("fold_axis", "x")) or "x").strip().lower()
    fold_axis = "y" if axis_raw in {"y", "fold_y", "vertical", "v"} else "x"
    penumbra_mm: float | None = None
    raw_penumbra = settings.get("coaxial_penumbra_mm", settings.get("penumbra_mm", None))
    if raw_penumbra is not None:
        try:
            candidate = float(raw_penumbra)
            if np.isfinite(candidate) and candidate > 0.0:
                penumbra_mm = candidate
        except (TypeError, ValueError):
            penumbra_mm = None
    return {
        "aperture_fold_mm": float(aperture_fold),
        "aperture_perp_mm": float(aperture_perp),
        "fold_angle_deg": float(fold_angle),
        "fold_axis": fold_axis,
        "penumbra_mm": penumbra_mm,
    }


def scene_source_spec_couples_to_imaging_launch(spec: object) -> bool:
    """Return whether an illumination source bounds the object-driven imaging launch.

    A coupled source is deliberately *additive*: KrakenOS continues to launch the
    imaging rays from the Object plane, while the source's coaxial descriptor limits
    those field origins to the illuminated footprint.  The physical LED is traced in
    an isolated illumination pass, so it cannot replace the imaging conjugates.

    Coupling is opt-in because many scene sources are themselves the primary traced
    rays (stray-light and source-to-detector layouts).  A valid coaxial descriptor is
    required; a bare flag can never fabricate launch geometry.
    """
    if isinstance(spec, dict):
        settings: object = spec
    else:
        settings = getattr(spec, "settings", None)
    if not isinstance(settings, dict):
        return False
    enabled = source_spec_bool(
        settings,
        (
            COUPLE_TO_IMAGING_LAUNCH_KEY,
            "couple_to_imaging",
            "imaging_launch_coupled",
        ),
        False,
    )
    return bool(enabled and coaxial_illuminator_descriptor(settings) is not None)


def scene_source_from_spec(
    spec: dict[str, object],
    index: int,
    *,
    wavelength: float,
    sample_count: int | None = None,
    default_ray_count: int = 1,
    default_radius: float = 1.0,
    default_cone_deg: float = 0.0,
    source_model_values: tuple[str, ...] = (
        "Pupil / field",
        "Gaussian beam",
        "Collimated disk source",
        "Random circle source",
        "Random square source",
        "Random rectangle source",
        "Random line source",
        "Random point cone",
        "Zemax rayfile source",
    ),
    source_model_default: str = "Pupil / field",
    angular_weight_default: str = "Uniform solid angle",
) -> SceneSource3D:
    model = str(spec.get("model", spec.get("source_model", "Collimated disk source"))).strip()
    if model not in source_model_values:
        model = "Collimated disk source"
    origin = source_spec_vector(
        spec,
        ("origin", "source_xyz", "xyz"),
        ("source_x", "source_y", "source_z"),
        (0.0, 0.0, 0.0),
    )
    direction = source_spec_vector(
        spec,
        ("direction", "source_lmn", "lmn"),
        ("source_l", "source_m", "source_n"),
        (0.0, 0.0, 1.0),
    )
    direction_norm = float(np.linalg.norm(direction))
    if direction_norm <= 1e-12:
        direction = np.asarray((0.0, 0.0, 1.0), dtype=float)
    else:
        direction = direction / direction_norm
    ray_count = int(max(1, round(source_spec_float(spec, ("ray_count", "rays"), sample_count or default_ray_count, minimum=1.0))))
    power = source_spec_float(spec, ("power", "source_power"), 1.0, minimum=0.0)
    radius = source_spec_float(spec, ("radius", "source_radius", "launch_radius"), default_radius, minimum=0.0)
    radius_x = source_spec_float(spec, ("radius_x", "half_width_x", "source_radius_x"), radius, minimum=0.0)
    radius_y = source_spec_float(spec, ("radius_y", "half_width_y", "source_radius_y"), radius, minimum=0.0)
    cone_deg = source_spec_float(spec, ("cone_deg", "source_cone_angle"), default_cone_deg, minimum=0.0)
    physical = source_spec_bool(spec, "physical", model != source_model_default)
    role_default = "illumination" if physical else "pupil_field_reference"
    role = str(spec.get("role", role_default)).strip() or role_default
    wavelength_value = source_spec_float(spec, ("wavelength", "source_wavelength"), wavelength, minimum=1e-12)
    settings = dict(spec)
    settings.update(
        {
            "source_model": model,
            "ray_count": ray_count,
            "origin": [float(value) for value in origin[:3]],
            "direction": [float(value) for value in direction[:3]],
            "power": float(power),
            "power_per_ray": float(power) / float(ray_count),
            "radius": radius,
            "radius_x": radius_x,
            "radius_y": radius_y,
            "cone_deg": cone_deg,
            "seed": int(round(source_spec_float(spec, ("seed", "source_seed"), index + 1, minimum=0.0))) % (2**32 - 1),
            "angular_weight": str(spec.get("angular_weight", spec.get("source_angular_weight", angular_weight_default))),
        }
    )
    return SceneSource3D(
        source_id=str(spec.get("source_id", spec.get("id", f"source:{index}"))),
        name=str(spec.get("name", f"Source {index + 1}")),
        role=role,
        model=model,
        enabled=source_spec_bool(spec, "enabled", True),
        physical=physical,
        origin=origin[:3].astype(float),
        direction=direction[:3].astype(float),
        ray_count=ray_count,
        wavelength=wavelength_value,
        power=float(power),
        weight_per_ray=float(power) / float(ray_count),
        settings={str(key): scene_source_setting_value(value) for key, value in settings.items()},
    )


def scene_source_feature_text(
    source: SceneSource3D,
    *,
    source_model_default: str = "Pupil / field",
    source_model_zemax_rayfile: str = "Zemax rayfile source",
    pupil_pattern_default: str = "Meridional fan",
) -> str:
    settings = dict(source.settings or {})
    features = [str(source.role), f"rays={int(source.ray_count)}"]
    if source.model == "Gaussian beam":
        if settings.get("waist_radius") is not None:
            features.append(f"w0={float(settings['waist_radius']):.6g} mm")
        if settings.get("m2") is not None:
            features.append(f"M2={float(settings['m2']):.6g}")
    elif source.model == source_model_zemax_rayfile:
        rayfile_path = str(settings.get("rayfile_path", "") or "").strip()
        if rayfile_path:
            features.append(Path(rayfile_path).name)
        record_count = settings.get("record_count")
        if record_count is not None:
            try:
                features.append(f"records={int(record_count):,}")
            except Exception:
                pass
    elif source.model == source_model_default:
        features.append(str(settings.get("pupil_pattern", pupil_pattern_default)))
    else:
        if settings.get("radius") is not None:
            features.append(f"radius={float(settings['radius']):.6g} mm")
        if settings.get("cone_deg") is not None:
            features.append(f"cone={float(settings['cone_deg']):.6g} deg")
    return ", ".join(features)


def scene_source_detail_text(
    source: SceneSource3D,
    *,
    source_model_zemax_rayfile: str = "Zemax rayfile source",
) -> str:
    settings = dict(source.settings or {})
    ox, oy, oz = np.asarray(source.origin, dtype=float).reshape(-1)[:3]
    dl, dm, dn = np.asarray(source.direction, dtype=float).reshape(-1)[:3]
    parts = [
        f"origin=({ox:.6g}, {oy:.6g}, {oz:.6g}) mm",
        f"dir=({dl:.6g}, {dm:.6g}, {dn:.6g})",
    ]
    if source.wavelength is not None:
        parts.append(f"wavelength={float(source.wavelength):.6g} um")
    if source.power is not None:
        parts.append(f"power={float(source.power):.6g}")
    if source.weight_per_ray is not None:
        parts.append(f"weight/ray={float(source.weight_per_ray):.6g}")
    if source.model == source_model_zemax_rayfile:
        rayfile_path = str(settings.get("rayfile_path", "") or "").strip()
        if rayfile_path:
            parts.append(f"rayfile={Path(rayfile_path).name}")
        spectrum_path = str(settings.get("spectrum_path", "") or "").strip()
        if spectrum_path:
            parts.append(f"spectrum={Path(spectrum_path).name}")
    if not source.physical:
        parts.append("not a physical illumination emitter; uses object/field pupil sampling")
    return " | ".join(parts)


def scene_sources_summary_text(sources: list[SceneSource3D]) -> str:
    enabled = [source for source in sources if bool(source.enabled)]
    total_rays = sum(int(source.ray_count) for source in enabled)
    names = ", ".join(str(source.name) for source in enabled[:3])
    suffix = "" if len(enabled) <= 3 else f", +{len(enabled) - 3} more"
    return (
        f"Layout scene sources: {len(enabled)} physical emitter(s), "
        f"{total_rays} rays total ({names}{suffix}). "
        "Use Scene Source Manager to add, edit, delete, or reorder physical emitters."
    )


def source_panel_summary_text(
    stats: dict[str, object],
    *,
    source_model_default: str = "Pupil / field",
    source_model_zemax_rayfile: str = "Zemax rayfile source",
    pupil_pattern_default: str = "Meridional fan",
    gaussian_input_mode_default: str = "Waist + offset",
    angular_weight_default: str = "Uniform solid angle",
) -> str:
    source_model = str(stats["source_model"])
    if source_model == source_model_default:
        pattern = str(stats["pupil_pattern"])
        if pattern == pupil_pattern_default:
            return (
                "Pupil / field source: ideal rays. Use Object Mode=Infinity, "
                "Field type=Angle, and Field value to tilt the ideal launch."
            )
        if pattern == "Chief ray":
            return "Pupil / field source: chief ray only."
        if pattern == "R-theta":
            return (
                "Pupil / field source: r-theta point "
                f"r={float(stats['pupil_rad']):.4g}, theta={float(stats['pupil_theta']):.4g} deg."
            )
        seed_note = f", seed {stats['seed']}" if pattern == "Random disk" else ""
        return f"Pupil / field source: {pattern}{seed_note}."
    if source_model == "Gaussian beam":
        ox, oy, oz = stats["origin"]
        dl, dm, dn = stats["direction"]
        mode = str(stats.get("input_mode", gaussian_input_mode_default))
        source_note = (
            f"source D {float(stats['beam_diameter']):.4g} mm, full div {float(stats['full_divergence_mrad']):.4g} mrad -> "
            if mode == "Diameter + divergence"
            else ""
        )
        return (
            f"Gaussian beam: {stats['ray_count']} rays + q-envelope, "
            f"{source_note}w0 {float(stats['waist_radius']):.4g} mm, "
            f"launch radius {float(stats['launch_radius']):.4g} mm, "
            f"offset {float(stats['waist_offset']):.4g} mm, "
            f"M2 {float(stats['m2']):.4g}, zR {float(stats['z_rayleigh']):.4g} mm, "
            f"div {float(stats['divergence_mrad']):.4g} mrad, "
            f"origin ({ox:.4g}, {oy:.4g}, {oz:.4g}) mm, "
            f"dir ({dl:.4g}, {dm:.4g}, {dn:.4g})."
        )
    if source_model == "Collimated disk source":
        ox, oy, oz = stats["origin"]
        dl, dm, dn = stats["direction"]
        cone_deg = float(stats.get("cone_deg", 0.0) or 0.0)
        angular_text = (
            f"cone {cone_deg:.4g} deg, NA {float(stats.get('na', 0.0) or 0.0):.4g}, "
            if cone_deg > 1e-12
            else "parallel rays, "
        )
        return (
            f"Collimated disk source: {stats['ray_count']} {angular_text}"
            f"radius {float(stats['radius']):.4g} mm, "
            f"power/ray {float(stats['power_per_ray']):.4g}, "
            f"origin ({ox:.4g}, {oy:.4g}, {oz:.4g}) mm, "
            f"dir ({dl:.4g}, {dm:.4g}, {dn:.4g})."
        )
    if source_model == source_model_zemax_rayfile:
        ox, oy, oz = stats["origin"]
        dl, dm, dn = stats["direction"]
        rayfile_path = str(stats.get("rayfile_path", "") or "").strip()
        rayfile_note = Path(rayfile_path).name if rayfile_path else "import a Zemax NSC Source File .zmx first"
        return (
            f"Zemax rayfile source: {stats['ray_count']} sampled rays from {rayfile_note}, "
            f"records {int(stats.get('record_count', 0) or 0)}, "
            f"origin ({ox:.4g}, {oy:.4g}, {oz:.4g}) mm, "
            f"dir ({dl:.4g}, {dm:.4g}, {dn:.4g})."
        )
    ox, oy, oz = stats["origin"]
    dl, dm, dn = stats["direction"]
    weight = str(stats.get("angular_weight", angular_weight_default))
    weight_note = (
        f", {weight}"
        if source_model in {"Random circle source", "Random square source"} and weight != angular_weight_default
        else ""
    )
    size_text = (
        f"length {float(stats['length']):.4g} mm"
        if source_model == "Random line source"
        else f"area {float(stats['area']):.4g} mm^2"
    )
    return (
        f"{source_model}: {stats['ray_count']} rays, power/ray {float(stats['power_per_ray']):.4g}, "
        f"NA {float(stats['na']):.4g}, {size_text}{weight_note}, "
        f"solid angle {float(stats['solid_angle']):.4g} sr, "
        f"origin ({ox:.4g}, {oy:.4g}, {oz:.4g}) mm, "
        f"dir ({dl:.4g}, {dm:.4g}, {dn:.4g})."
    )
