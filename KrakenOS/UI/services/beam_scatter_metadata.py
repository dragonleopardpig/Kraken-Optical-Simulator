"""Beam-splitter and diffuse-scatter surface metadata helpers."""

from __future__ import annotations

from pprint import pformat
import re

import numpy as np

from KrakenOS.scatter_backend import (
    format_pyscatmech_parameters,
    normalize_pyscatmech_parameters,
    pyscatmech_status,
)

BEAM_SPLITTER_ADVANCED_ATTR = "BeamSplitter"
DIFFUSE_SCATTER_ADVANCED_ATTR = "DiffuseScatter"

BEAM_SPLITTER_SPLIT_MODES = (
    "Deterministic paths",
    "Deterministic Fresnel P/S",
    "Deterministic coating table",
    "Monte Carlo coating split",
)
BEAM_SPLITTER_DEFAULT_SETTINGS = {
    "split_mode": BEAM_SPLITTER_SPLIT_MODES[0],
    "reflectance": 0.5,
    "absorption": 0.0,
    "polarization_p_fraction": 0.5,
    "polarization_s_phase_deg": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "transmit_s_phase_deg": 0.0,
    "reflect_s_phase_deg": 0.0,
    "min_branch_power": 1e-3,
    "max_branch_depth": 8,
}
DIFFUSE_SCATTER_DEFAULT_SETTINGS = {
    "model": "Lambertian",
    "backend": "Built-in",
    "backend_model": "Microroughness_BRDF_Model",
    "backend_parameters": {},
    "reflectance": 0.8,
    "sample_count": 9,
    "max_scatter_angle_deg": 90.0,
    "min_branch_power": 1e-4,
    "max_branch_depth": 2,
    "lobe_exponent": 20.0,
    "roughness_deg": 20.0,
    "target_surface": None,
    "target_radius_scale": 1.0,
    "polarization": "Preserve projected Jones",
}


def _normalize_diffuse_scatter_settings(value) -> dict[str, object]:
    settings = dict(DIFFUSE_SCATTER_DEFAULT_SETTINGS)
    if isinstance(value, dict):
        incoming = dict(value)
        if "reflectance" not in incoming:
            for alias in ("albedo", "diffuse_reflectance", "rho"):
                if alias in incoming:
                    incoming["reflectance"] = incoming.get(alias)
                    break
        if "sample_count" not in incoming:
            for alias in ("samples", "ray_count", "branch_count", "scatter_rays"):
                if alias in incoming:
                    incoming["sample_count"] = incoming.get(alias)
                    break
        if "max_scatter_angle_deg" not in incoming:
            for alias in ("cone_angle_deg", "hemisphere_angle_deg", "max_angle_deg"):
                if alias in incoming:
                    incoming["max_scatter_angle_deg"] = incoming.get(alias)
                    break
        if "max_branch_depth" not in incoming:
            for alias in ("max_scatter_depth", "max_depth"):
                if alias in incoming:
                    incoming["max_branch_depth"] = incoming.get(alias)
                    break
        if "target_surface" not in incoming:
            for alias in ("guided_target_surface", "target_surface_index", "target"):
                if alias in incoming:
                    incoming["target_surface"] = incoming.get(alias)
                    break
        if "target_radius_scale" not in incoming:
            for alias in ("guided_target_radius_scale", "target_radius_factor", "target_scale"):
                if alias in incoming:
                    incoming["target_radius_scale"] = incoming.get(alias)
                    break
        if "lobe_exponent" not in incoming:
            for alias in ("cosine_exponent", "phong_exponent", "gloss_exponent", "specular_exponent"):
                if alias in incoming:
                    incoming["lobe_exponent"] = incoming.get(alias)
                    break
        if "roughness_deg" not in incoming:
            for alias in ("sigma_deg", "sigma", "roughness", "surface_roughness_deg"):
                if alias in incoming:
                    incoming["roughness_deg"] = incoming.get(alias)
                    break
        if "backend_model" not in incoming:
            for alias in ("brdf_model", "pyscatmech_model", "backend_brdf_model"):
                if alias in incoming:
                    incoming["backend_model"] = incoming.get(alias)
                    break
        if "backend_parameters" not in incoming:
            for alias in ("brdf_parameters", "pyscatmech_parameters", "backend_params"):
                if alias in incoming:
                    incoming["backend_parameters"] = incoming.get(alias)
                    break
        settings.update(incoming)
    model = str(settings.get("model", "Lambertian") or "Lambertian").strip() or "Lambertian"
    if model.lower() in {"lambert", "lambertian diffuse", "diffuse"}:
        model = "Lambertian"
    elif model.lower() in {"cosine lobe", "cosine-lobe", "glossy", "phong", "specular lobe", "specular-lobe"}:
        model = "Cosine Lobe"
    elif model.lower() in {"oren-nayar", "oren nayar", "rough diffuse", "rough-diffuse"}:
        model = "Oren-Nayar"
    elif model.lower() in {"pyscatmech brdf", "pyscatmech", "scatmech", "brdf", "measured brdf"}:
        model = "pySCATMECH BRDF"
    backend = str(settings.get("backend", "Built-in") or "Built-in").strip() or "Built-in"
    if "pyscatmech" in backend.lower():
        backend = "pySCATMECH"
    else:
        backend = "Built-in"
    if model == "pySCATMECH BRDF":
        backend = "pySCATMECH"
    settings["model"] = model
    settings["backend"] = backend
    settings["backend_model"] = str(
        settings.get("backend_model", DIFFUSE_SCATTER_DEFAULT_SETTINGS["backend_model"])
        or DIFFUSE_SCATTER_DEFAULT_SETTINGS["backend_model"]
    ).strip() or str(DIFFUSE_SCATTER_DEFAULT_SETTINGS["backend_model"])
    try:
        settings["backend_parameters"] = normalize_pyscatmech_parameters(
            settings.get("backend_parameters", DIFFUSE_SCATTER_DEFAULT_SETTINGS["backend_parameters"])
        )
    except Exception:
        settings["backend_parameters"] = dict(DIFFUSE_SCATTER_DEFAULT_SETTINGS["backend_parameters"])
    for key in ("reflectance", "max_scatter_angle_deg", "min_branch_power"):
        try:
            settings[key] = float(settings.get(key, DIFFUSE_SCATTER_DEFAULT_SETTINGS[key]))
        except Exception:
            settings[key] = float(DIFFUSE_SCATTER_DEFAULT_SETTINGS[key])
    try:
        settings["sample_count"] = int(float(settings.get("sample_count", DIFFUSE_SCATTER_DEFAULT_SETTINGS["sample_count"])))
    except Exception:
        settings["sample_count"] = int(DIFFUSE_SCATTER_DEFAULT_SETTINGS["sample_count"])
    try:
        settings["max_branch_depth"] = int(float(settings.get("max_branch_depth", DIFFUSE_SCATTER_DEFAULT_SETTINGS["max_branch_depth"])))
    except Exception:
        settings["max_branch_depth"] = int(DIFFUSE_SCATTER_DEFAULT_SETTINGS["max_branch_depth"])
    target_value = settings.get("target_surface", None)
    target_surface = None
    if target_value is not None:
        try:
            target_text = str(target_value).strip()
            if target_text and target_text.lower() not in {"none", "auto", "off", "disabled"}:
                if target_text.upper().startswith("S"):
                    target_text = target_text[1:]
                target_text = target_text.split(":", 1)[0].strip()
                target_surface = int(float(target_text))
        except Exception:
            target_surface = None
    settings["target_surface"] = target_surface
    try:
        settings["target_radius_scale"] = float(settings.get("target_radius_scale", DIFFUSE_SCATTER_DEFAULT_SETTINGS["target_radius_scale"]))
    except Exception:
        settings["target_radius_scale"] = float(DIFFUSE_SCATTER_DEFAULT_SETTINGS["target_radius_scale"])
    try:
        settings["lobe_exponent"] = float(settings.get("lobe_exponent", DIFFUSE_SCATTER_DEFAULT_SETTINGS["lobe_exponent"]))
    except Exception:
        settings["lobe_exponent"] = float(DIFFUSE_SCATTER_DEFAULT_SETTINGS["lobe_exponent"])
    try:
        settings["roughness_deg"] = float(settings.get("roughness_deg", DIFFUSE_SCATTER_DEFAULT_SETTINGS["roughness_deg"]))
    except Exception:
        settings["roughness_deg"] = float(DIFFUSE_SCATTER_DEFAULT_SETTINGS["roughness_deg"])
    settings["reflectance"] = min(max(float(settings["reflectance"]), 0.0), 1.0)
    settings["max_scatter_angle_deg"] = min(max(float(settings["max_scatter_angle_deg"]), 0.0), 90.0)
    settings["min_branch_power"] = max(float(settings["min_branch_power"]), 0.0)
    settings["sample_count"] = max(1, min(int(settings["sample_count"]), 257))
    settings["max_branch_depth"] = max(1, min(int(settings["max_branch_depth"]), 32))
    if not np.isfinite(float(settings["target_radius_scale"])):
        settings["target_radius_scale"] = float(DIFFUSE_SCATTER_DEFAULT_SETTINGS["target_radius_scale"])
    settings["target_radius_scale"] = min(max(float(settings["target_radius_scale"]), 0.01), 4.0)
    if not np.isfinite(float(settings["lobe_exponent"])):
        settings["lobe_exponent"] = float(DIFFUSE_SCATTER_DEFAULT_SETTINGS["lobe_exponent"])
    settings["lobe_exponent"] = min(max(float(settings["lobe_exponent"]), 0.0), 10000.0)
    if not np.isfinite(float(settings["roughness_deg"])):
        settings["roughness_deg"] = float(DIFFUSE_SCATTER_DEFAULT_SETTINGS["roughness_deg"])
    settings["roughness_deg"] = min(max(float(settings["roughness_deg"]), 0.0), 90.0)
    settings["polarization"] = str(
        settings.get("polarization", DIFFUSE_SCATTER_DEFAULT_SETTINGS["polarization"])
        or DIFFUSE_SCATTER_DEFAULT_SETTINGS["polarization"]
    )
    return settings


def _validate_diffuse_scatter_settings(value) -> list[str]:
    settings = _normalize_diffuse_scatter_settings(value)
    messages: list[str] = []
    if settings["model"] not in {"Lambertian", "Cosine Lobe", "Oren-Nayar", "pySCATMECH BRDF"}:
        messages.append("DiffuseScatter supports model='Lambertian', 'Oren-Nayar', 'Cosine Lobe', or 'pySCATMECH BRDF'.")
    if not 0.0 <= float(settings["reflectance"]) <= 1.0:
        messages.append("DiffuseScatter reflectance must be in [0, 1].")
    if int(settings["sample_count"]) < 1:
        messages.append("DiffuseScatter sample_count must be at least 1.")
    if not 0.0 <= float(settings["max_scatter_angle_deg"]) <= 90.0:
        messages.append("DiffuseScatter max_scatter_angle_deg must be in [0, 90].")
    if float(settings["min_branch_power"]) < 0.0:
        messages.append("DiffuseScatter min_branch_power must not be negative.")
    if int(settings["max_branch_depth"]) < 1:
        messages.append("DiffuseScatter max_branch_depth must be at least 1.")
    if settings.get("target_surface") is not None and int(settings["target_surface"]) < 0:
        messages.append("DiffuseScatter target_surface must be None or a non-negative surface index.")
    if float(settings.get("target_radius_scale", 1.0)) <= 0.0:
        messages.append("DiffuseScatter target_radius_scale must be positive.")
    if float(settings.get("lobe_exponent", 0.0)) < 0.0:
        messages.append("DiffuseScatter lobe_exponent must not be negative.")
    if not 0.0 <= float(settings.get("roughness_deg", 0.0)) <= 90.0:
        messages.append("DiffuseScatter roughness_deg must be in [0, 90].")
    if str(settings.get("backend", "Built-in")) == "pySCATMECH" and not str(settings.get("backend_model", "")).strip():
        messages.append("DiffuseScatter backend_model is required when backend='pySCATMECH'.")
    return messages


def _diffuse_scatter_summary(value) -> str:
    settings = _normalize_diffuse_scatter_settings(value)
    target_text = "unguided" if settings.get("target_surface") is None else f"target=S{int(settings['target_surface'])}"
    model_detail = f"n={float(settings['lobe_exponent']):.6g}"
    if settings["model"] == "Oren-Nayar":
        model_detail = f"sigma={float(settings['roughness_deg']):.6g} deg"
    if settings["backend"] == "pySCATMECH":
        model_detail = f"model={settings['backend_model']}"
    return (
        f"{settings['model']} {settings['backend']}, R={float(settings['reflectance']):.6g}, "
        f"samples={int(settings['sample_count'])}, cone={float(settings['max_scatter_angle_deg']):.6g} deg, "
        f"minP={float(settings['min_branch_power']):.3g}, depth={int(settings['max_branch_depth'])}, "
        f"{model_detail}, {target_text}"
    )


def _normalize_beam_splitter_settings(value) -> dict[str, object]:
    settings = dict(BEAM_SPLITTER_DEFAULT_SETTINGS)
    if isinstance(value, dict):
        incoming = dict(value)
        if "split_mode" not in incoming and "mode" in incoming:
            mode_text = str(incoming.get("mode", "")).strip().lower()
            if mode_text in {"monte carlo", "probabilistic", "probability", "stochastic", "coating"}:
                incoming["split_mode"] = "Monte Carlo coating split"
            elif "coating" in mode_text and any(token in mode_text for token in ("deterministic", "table", "fixed")):
                incoming["split_mode"] = "Deterministic coating table"
            elif any(token in mode_text for token in ("fresnel", "polarization", "polarisation", "p/s")):
                incoming["split_mode"] = "Deterministic Fresnel P/S"
            else:
                incoming["split_mode"] = "Deterministic paths"
        if "absorption" not in incoming and "loss" in incoming:
            incoming["absorption"] = incoming.get("loss")
        if "max_branch_depth" not in incoming and "max_split_depth" in incoming:
            incoming["max_branch_depth"] = incoming.get("max_split_depth")
        if "polarization_p_fraction" not in incoming:
            for alias in ("p_polarization_fraction", "p_fraction", "pfrac", "p_power_fraction"):
                if alias in incoming:
                    incoming["polarization_p_fraction"] = incoming.get(alias)
                    break
        if "polarization_s_phase_deg" not in incoming:
            for alias in ("s_phase_deg", "jones_s_phase_deg", "polarization_phase_deg", "relative_s_phase_deg"):
                if alias in incoming:
                    incoming["polarization_s_phase_deg"] = incoming.get(alias)
                    break
        if "transmit_s_phase_deg" not in incoming:
            for alias in ("transmit_retardance_deg", "transmit_s_retardance_deg", "t_s_phase_deg"):
                if alias in incoming:
                    incoming["transmit_s_phase_deg"] = incoming.get(alias)
                    break
        if "reflect_s_phase_deg" not in incoming:
            for alias in ("reflect_retardance_deg", "reflect_s_retardance_deg", "r_s_phase_deg"):
                if alias in incoming:
                    incoming["reflect_s_phase_deg"] = incoming.get(alias)
                    break
        if "reflectance" not in incoming and "transmittance" in incoming:
            try:
                transmittance = float(incoming.get("transmittance", 0.5))
                absorption = float(incoming.get("absorption", incoming.get("loss", 0.0)))
                incoming["reflectance"] = 1.0 - transmittance - absorption
            except Exception:
                pass
        settings.update(incoming)
    mode = str(settings.get("split_mode", BEAM_SPLITTER_DEFAULT_SETTINGS["split_mode"])).strip()
    if mode == "Deterministic branches (future)":
        mode = "Deterministic paths"
    mode_key = re.sub(r"[^a-z0-9]+", "", mode.lower())
    mode_aliases = {
        "deterministiccoating": "Deterministic coating table",
        "deterministiccoatingtable": "Deterministic coating table",
        "coatingtable": "Deterministic coating table",
        "coatingtablesplit": "Deterministic coating table",
        "fresnel": "Deterministic Fresnel P/S",
        "deterministicfresnel": "Deterministic Fresnel P/S",
        "deterministicfresnelps": "Deterministic Fresnel P/S",
        "fresnelps": "Deterministic Fresnel P/S",
        "ps": "Deterministic Fresnel P/S",
        "deterministicps": "Deterministic Fresnel P/S",
        "polarization": "Deterministic Fresnel P/S",
        "polarisation": "Deterministic Fresnel P/S",
        "deterministicpolarization": "Deterministic Fresnel P/S",
        "deterministicpolarisation": "Deterministic Fresnel P/S",
        "deterministicpolarizationfresnel": "Deterministic Fresnel P/S",
        "deterministicpolarisationfresnel": "Deterministic Fresnel P/S",
        "deterministicbranches": "Deterministic paths",
        "deterministicpaths": "Deterministic paths",
        "ideal": "Deterministic paths",
        "plate": "Deterministic paths",
        "montecarlo": "Monte Carlo coating split",
        "montecarlocoatingsplit": "Monte Carlo coating split",
        "probabilistic": "Monte Carlo coating split",
        "stochastic": "Monte Carlo coating split",
    }
    mode = mode_aliases.get(mode_key, mode)
    if mode not in BEAM_SPLITTER_SPLIT_MODES:
        mode = BEAM_SPLITTER_DEFAULT_SETTINGS["split_mode"]
    settings["split_mode"] = mode
    for key in (
        "reflectance",
        "absorption",
        "polarization_p_fraction",
        "polarization_s_phase_deg",
        "transmit_phase_deg",
        "reflect_phase_deg",
        "transmit_s_phase_deg",
        "reflect_s_phase_deg",
        "min_branch_power",
    ):
        try:
            settings[key] = float(settings.get(key, BEAM_SPLITTER_DEFAULT_SETTINGS[key]))
        except Exception:
            settings[key] = float(BEAM_SPLITTER_DEFAULT_SETTINGS[key])
    try:
        settings["max_branch_depth"] = int(float(settings.get("max_branch_depth", BEAM_SPLITTER_DEFAULT_SETTINGS["max_branch_depth"])))
    except Exception:
        settings["max_branch_depth"] = int(BEAM_SPLITTER_DEFAULT_SETTINGS["max_branch_depth"])
    return settings


def _beam_splitter_uses_coating_table(settings) -> bool:
    mode = str(_normalize_beam_splitter_settings(settings)["split_mode"]).strip().lower()
    return "coating table" in mode


def _beam_splitter_uses_fresnel_polarization(settings) -> bool:
    mode = str(_normalize_beam_splitter_settings(settings)["split_mode"]).strip().lower()
    return "fresnel" in mode or "polarization" in mode or "polarisation" in mode


def _coating_table_has_data(value) -> bool:
    # Imported lazily: advanced_surface_validation imports this module at its top
    # level, so a module-level back-import would be circular.
    from KrakenOS.UI.services.advanced_surface_validation import _validate_coating_table

    if _validate_coating_table(value):
        return False
    try:
        r_table, a_table, wavelengths, angles = value
        r_arr = np.asarray(r_table, dtype=float)
        a_arr = np.asarray(a_table, dtype=float)
        w_arr = np.asarray(wavelengths, dtype=float).ravel()
        theta_arr = np.asarray(angles, dtype=float).ravel()
    except Exception:
        return False
    return r_arr.size > 0 and a_arr.size > 0 and w_arr.size > 0 and theta_arr.size > 0


def _beam_splitter_coating_for_settings(settings, existing_coating=None) -> list[object]:
    normalized = _normalize_beam_splitter_settings(settings)
    if _beam_splitter_uses_coating_table(normalized) and _coating_table_has_data(existing_coating):
        return existing_coating
    return _beam_splitter_coating_from_settings(normalized)


def _validate_beam_splitter_settings(value) -> list[str]:
    settings = _normalize_beam_splitter_settings(value)
    messages: list[str] = []
    reflectance = float(settings["reflectance"])
    absorption = float(settings["absorption"])
    polarization_p_fraction = float(settings["polarization_p_fraction"])
    polarization_s_phase = float(settings["polarization_s_phase_deg"])
    transmit_s_phase = float(settings["transmit_s_phase_deg"])
    reflect_s_phase = float(settings["reflect_s_phase_deg"])
    min_branch_power = float(settings["min_branch_power"])
    max_branch_depth = int(settings["max_branch_depth"])
    if not 0.0 <= reflectance <= 1.0:
        messages.append("BeamSplitter reflectance must be in [0, 1].")
    if not 0.0 <= absorption <= 1.0:
        messages.append("BeamSplitter absorption must be in [0, 1].")
    if reflectance + absorption > 1.0 + 1e-12:
        messages.append("BeamSplitter reflectance + absorption must not exceed 1.")
    if not np.isfinite(polarization_p_fraction) or not 0.0 <= polarization_p_fraction <= 1.0:
        messages.append("BeamSplitter polarization_p_fraction must be in [0, 1].")
    if not np.isfinite(polarization_s_phase):
        messages.append("BeamSplitter polarization_s_phase_deg must be finite.")
    if not np.isfinite(transmit_s_phase):
        messages.append("BeamSplitter transmit_s_phase_deg must be finite.")
    if not np.isfinite(reflect_s_phase):
        messages.append("BeamSplitter reflect_s_phase_deg must be finite.")
    if min_branch_power < 0.0 or not np.isfinite(min_branch_power):
        messages.append("BeamSplitter min path power must be a non-negative finite value.")
    if max_branch_depth < 1:
        messages.append("BeamSplitter max path depth must be at least 1.")
    return messages


def _beam_splitter_coating_from_settings(settings) -> list[object]:
    normalized = _normalize_beam_splitter_settings(settings)
    reflectance = min(max(float(normalized["reflectance"]), 0.0), 1.0)
    absorption = min(max(float(normalized["absorption"]), 0.0), 1.0 - reflectance)
    wavelengths = [0.45, 0.55, 0.65]
    angles = [0.0, 45.0, 70.0]
    r_table = [[reflectance for _w in wavelengths] for _theta in angles]
    a_table = [[absorption for _w in wavelengths] for _theta in angles]
    return [r_table, a_table, wavelengths, angles]


def _beam_splitter_summary(value) -> str:
    settings = _normalize_beam_splitter_settings(value)
    reflectance = float(settings["reflectance"])
    absorption = float(settings["absorption"])
    transmittance = max(1.0 - reflectance - absorption, 0.0)
    prefix = "fallback " if _beam_splitter_uses_coating_table(settings) else ""
    p_fraction = float(settings["polarization_p_fraction"])
    s_phase = float(settings["polarization_s_phase_deg"])
    transmit_s_phase = float(settings["transmit_s_phase_deg"])
    reflect_s_phase = float(settings["reflect_s_phase_deg"])
    show_polarization = (
        _beam_splitter_uses_fresnel_polarization(settings)
        or abs(p_fraction - float(BEAM_SPLITTER_DEFAULT_SETTINGS["polarization_p_fraction"])) > 1e-12
        or abs(s_phase) > 1e-12
        or abs(transmit_s_phase) > 1e-12
        or abs(reflect_s_phase) > 1e-12
    )
    p_summary = (
        f", Pfrac={p_fraction:.3g}, Sphase={s_phase:.3g} deg, "
        f"Tret={transmit_s_phase:.3g} deg, Rret={reflect_s_phase:.3g} deg"
        if show_polarization
        else ""
    )
    return (
        f"{prefix}R/T/A={reflectance:.6g}/{transmittance:.6g}/{absorption:.6g}, "
        f"mode={settings['split_mode']}{p_summary}, minP={float(settings['min_branch_power']):.3g}, "
        f"depth={int(settings['max_branch_depth'])}"
    )
