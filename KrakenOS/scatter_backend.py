from __future__ import annotations

import ast
import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np


_PYSCATMECH_MODEL_KEY_ALIASES = {None, "None", "__model__", "model", "Model"}


def _normalize_vector(vector, fallback=(0.0, 0.0, 1.0)) -> np.ndarray:
    try:
        value = np.asarray(vector, dtype=float).reshape(-1)[:3]
    except Exception:
        value = np.asarray(fallback, dtype=float)
    if value.size < 3:
        value = np.asarray(fallback, dtype=float)
    norm = float(np.linalg.norm(value))
    if not np.isfinite(norm) or norm <= 1e-15:
        value = np.asarray(fallback, dtype=float)
        norm = float(np.linalg.norm(value)) or 1.0
    return value / norm


def _coerce_pyscatmech_model_dict(value):
    if isinstance(value, dict):
        converted: dict[object, object] = {}
        for key, child in value.items():
            normalized_key = None if key in _PYSCATMECH_MODEL_KEY_ALIASES else str(key)
            converted[normalized_key] = _coerce_pyscatmech_model_dict(child)
        return converted
    if isinstance(value, list):
        return [_coerce_pyscatmech_model_dict(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_coerce_pyscatmech_model_dict(item) for item in value)
    return value


def _serialize_pyscatmech_model_dict(value):
    if isinstance(value, dict):
        converted: dict[str, object] = {}
        for key, child in value.items():
            normalized_key = "__model__" if key is None else str(key)
            converted[normalized_key] = _serialize_pyscatmech_model_dict(child)
        return converted
    if isinstance(value, list):
        return [_serialize_pyscatmech_model_dict(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_pyscatmech_model_dict(item) for item in value]
    return value


def normalize_pyscatmech_parameters(value) -> dict[str | None, object]:
    if value is None:
        return {}
    parsed = value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        last_error: Exception | None = None
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(text)
                break
            except Exception as exc:  # pragma: no cover - exercised by validation
                last_error = exc
        else:
            raise ValueError(f"Could not parse pySCATMECH parameters: {last_error}")
    if not isinstance(parsed, dict):
        raise ValueError("pySCATMECH parameters must be a dict/JSON object.")
    converted = _coerce_pyscatmech_model_dict(parsed)
    return dict(converted)


def format_pyscatmech_parameters(value) -> str:
    try:
        normalized = normalize_pyscatmech_parameters(value)
    except Exception:
        return str(value or "").strip()
    if not normalized:
        return ""
    return json.dumps(_serialize_pyscatmech_model_dict(normalized), indent=2, sort_keys=True)


def _pyscatmech_repo_candidate() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2] / "pySCATMECH"


def _import_error_reason(exc: Exception) -> str:
    if isinstance(exc, ModuleNotFoundError) and str(getattr(exc, "name", "") or "") == "SCATPY":
        return "SCATPY extension is not installed. Build/install pySCATMECH first."
    return f"{type(exc).__name__}: {exc}"


@lru_cache(maxsize=1)
def pyscatmech_status() -> dict[str, object]:
    errors: list[str] = []
    repo_hint = ""
    try:
        from pySCATMECH.brdf import BRDF_Model  # type: ignore

        return {
            "available": True,
            "reason": "",
            "BRDF_Model": BRDF_Model,
            "path": "environment",
        }
    except Exception as exc:
        errors.append(_import_error_reason(exc))

    repo_path = _pyscatmech_repo_candidate()
    if repo_path.is_dir():
        repo_hint = str(repo_path)
        repo_text = str(repo_path)
        if repo_text not in sys.path:
            sys.path.insert(0, repo_text)
        try:
            from pySCATMECH.brdf import BRDF_Model  # type: ignore

            return {
                "available": True,
                "reason": "",
                "BRDF_Model": BRDF_Model,
                "path": repo_hint,
            }
        except Exception as exc:
            errors.append(_import_error_reason(exc))

    reason = " | ".join(item for item in errors if item)
    if repo_hint:
        reason = f"{reason} | local clone: {repo_hint}"
    return {
        "available": False,
        "reason": reason or "pySCATMECH is unavailable.",
        "BRDF_Model": None,
        "path": repo_hint,
    }


def pyscatmech_available() -> bool:
    return bool(pyscatmech_status().get("available"))


def _model_cache_key(model_name: str, parameters: dict[str | None, object]) -> tuple[str, str]:
    serialized = json.dumps(_serialize_pyscatmech_model_dict(parameters), sort_keys=True, default=str)
    return str(model_name), serialized


_MODEL_CACHE: dict[tuple[str, str], object] = {}


def _pyscatmech_model(model_name: str, parameters: dict[str | None, object], wavelength_um: float):
    status = pyscatmech_status()
    if not bool(status.get("available")):
        raise RuntimeError(str(status.get("reason", "pySCATMECH is unavailable.")))
    model_class = status.get("BRDF_Model")
    if model_class is None:
        raise RuntimeError("pySCATMECH BRDF_Model class is unavailable.")
    key = _model_cache_key(model_name, parameters)
    model = _MODEL_CACHE.get(key)
    if model is None:
        model = model_class(model_name, parameters)
        _MODEL_CACHE[key] = model
    runtime_params = dict(parameters)
    runtime_params["wavelength"] = float(wavelength_um)
    model.setParameters(runtime_params)
    return model


def _scatter_geometry_angles(incident, outgoing, normal) -> tuple[float, float, float]:
    incident_vec = _normalize_vector(incident)
    outgoing_vec = _normalize_vector(outgoing)
    normal_vec = _normalize_vector(normal)
    if float(np.dot(incident_vec, normal_vec)) > 0.0:
        normal_vec = -normal_vec

    wi = _normalize_vector(-incident_vec, fallback=normal_vec)
    wo = _normalize_vector(outgoing_vec, fallback=normal_vec)
    cos_theta_i = min(max(float(np.dot(wi, normal_vec)), -1.0), 1.0)
    cos_theta_o = min(max(float(np.dot(wo, normal_vec)), -1.0), 1.0)
    theta_i = float(np.arccos(cos_theta_i))
    theta_o = float(np.arccos(cos_theta_o))

    incident_proj = wi - (cos_theta_i * normal_vec)
    incident_proj_norm = float(np.linalg.norm(incident_proj))
    if incident_proj_norm <= 1e-12:
        reference = np.asarray((0.0, 0.0, 1.0), dtype=float)
        if abs(float(np.dot(reference, normal_vec))) > 0.94:
            reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
        tangent_x = np.cross(reference, normal_vec)
        tangent_x = tangent_x / max(float(np.linalg.norm(tangent_x)), 1e-15)
    else:
        tangent_x = incident_proj / incident_proj_norm
    tangent_y = np.cross(normal_vec, tangent_x)
    tangent_y = tangent_y / max(float(np.linalg.norm(tangent_y)), 1e-15)

    outgoing_proj = wo - (cos_theta_o * normal_vec)
    out_x = float(np.dot(outgoing_proj, tangent_x))
    out_y = float(np.dot(outgoing_proj, tangent_y))
    phi_s = float(np.arctan2(out_y, out_x))
    return theta_i, theta_o, phi_s


def pyscatmech_scalar_brdf(
    model_name: str,
    parameters,
    incident,
    outgoing,
    normal,
    wavelength_um: float,
) -> float:
    params = normalize_pyscatmech_parameters(parameters)
    model = _pyscatmech_model(str(model_name).strip() or "Microroughness_BRDF_Model", params, wavelength_um)
    theta_i, theta_o, phi_s = _scatter_geometry_angles(incident, outgoing, normal)
    value = float(model.BRDF(thetai=theta_i, thetas=theta_o, phis=phi_s))
    if not np.isfinite(value):
        return 0.0
    return max(value, 0.0)
