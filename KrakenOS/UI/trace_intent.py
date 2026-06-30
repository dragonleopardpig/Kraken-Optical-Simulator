"""Shared trace-mode intent resolver for Kraken UI scene workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SOURCE_MODEL_DEFAULT = "Pupil / field"
BEAM_SPLITTER_SURFACE = "Beam Splitter"
OBJECT_TARGET_SURFACE = "Object Target"
DIFFUSE_OBJECT_SURFACE = "Diffuse Object"
BEAM_SPLITTER_ADVANCED_ATTR = "BeamSplitter"
DIFFUSE_SCATTER_ADVANCED_ATTR = "DiffuseScatter"


@dataclass(frozen=True)
class TraceIntent:
    requested: str = "Auto"
    active: str = "Sequential"
    use_folded: bool = False
    use_nonseq: bool = False
    note: str = ""
    reasons: tuple[str, ...] = ()
    has_nonseq_geometry: bool = False
    has_physical_source: bool = False
    has_beam_splitter: bool = False
    has_diffuse_scatter: bool = False
    has_object_target: bool = False
    has_optical_stl_solid: bool = False
    has_probabilistic_nonseq: bool = False
    target_surface_index: int | None = None

    @property
    def has_nonseq_scene_request(self) -> bool:
        return bool(self.reasons)

    def as_dict(self) -> dict[str, object]:
        return {
            "requested": self.requested,
            "active": self.active,
            "use_folded": self.use_folded,
            "use_nonseq": self.use_nonseq,
            "note": self.note,
            "reasons": self.reasons,
            "has_nonseq_geometry": self.has_nonseq_geometry,
            "has_physical_source": self.has_physical_source,
            "has_beam_splitter": self.has_beam_splitter,
            "has_diffuse_scatter": self.has_diffuse_scatter,
            "has_object_target": self.has_object_target,
            "has_optical_stl_solid": self.has_optical_stl_solid,
            "has_probabilistic_nonseq": self.has_probabilistic_nonseq,
            "target_surface_index": self.target_surface_index,
        }


def normalize_requested_trace_mode(value: object) -> str:
    text = str(value or "Auto").strip()
    if text in {"Auto", "Sequential", "Folded Preview", "Non-Sequential Preview"}:
        return text
    return "Auto"


def scene_graph_value_present(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return text not in {"", "None", "none", "NULL", "null"}


def layout_uses_nonseq(
    rows_or_specs: list[Any],
    settings: dict[str, Any] | None = None,
    *,
    requested: object = "Auto",
    ns_trace_available: bool = True,
) -> bool:
    return bool(
        resolve_trace_intent(
            rows_or_specs,
            settings or {},
            requested=requested,
            can_folded=False,
            ns_trace_available=ns_trace_available,
        ).use_nonseq
    )


def resolve_trace_intent(
    rows_or_specs: list[Any],
    settings: dict[str, Any] | None = None,
    *,
    requested: object = "Auto",
    can_folded: bool = False,
    ns_trace_available: bool = True,
    has_physical_source: bool | None = None,
    nonseq_energy_probability: bool | None = None,
    nonseq_target_surface_index: int | None = None,
) -> TraceIntent:
    settings = settings or {}
    requested_mode = normalize_requested_trace_mode(requested)
    flags = _trace_flags(
        rows_or_specs,
        settings,
        has_physical_source=has_physical_source,
        nonseq_energy_probability=nonseq_energy_probability,
        nonseq_target_surface_index=nonseq_target_surface_index,
    )
    reasons = _trace_reasons(flags)
    active = "Sequential"
    use_folded = False
    use_nonseq = False
    note = ""

    if requested_mode == "Sequential":
        active = "Sequential"
    elif requested_mode == "Folded Preview":
        if can_folded:
            active = "Folded Preview"
            use_folded = True
        else:
            note = "Folded preview unavailable; using sequential preview."
    elif requested_mode == "Non-Sequential Preview":
        if ns_trace_available:
            active = "Non-Sequential Preview"
            use_nonseq = True
            if can_folded:
                note = "Using KrakenOS NsTraceLoop; folded compatibility display is bypassed."
            elif not flags["has_nonseq_geometry"]:
                note = "Using KrakenOS NsTraceLoop on a sequential-looking layout."
        else:
            note = "KrakenOS NsTrace is unavailable; using sequential preview."
    else:
        if reasons and ns_trace_available:
            active = "Non-Sequential Preview"
            use_nonseq = True
            reason_text = ", ".join(reasons) if reasons else "scene request"
            note = f"Auto uses KrakenOS NsTraceLoop for {reason_text}; sequential tracing is the axial special case."
        elif can_folded:
            active = "Folded Preview"
            use_folded = True
        else:
            active = "Sequential"

    return TraceIntent(
        requested=requested_mode,
        active=active,
        use_folded=use_folded,
        use_nonseq=use_nonseq,
        note=note,
        reasons=tuple(reasons),
        has_nonseq_geometry=bool(flags["has_nonseq_geometry"]),
        has_physical_source=bool(flags["has_physical_source"]),
        has_beam_splitter=bool(flags["has_beam_splitter"]),
        has_diffuse_scatter=bool(flags["has_diffuse_scatter"]),
        has_object_target=bool(flags["has_object_target"]),
        has_optical_stl_solid=bool(flags["has_optical_stl_solid"]),
        has_probabilistic_nonseq=bool(flags["has_probabilistic_nonseq"]),
        target_surface_index=flags["target_surface_index"],
    )


def _optical_solid_faces_have_beam_splitter(metadata: Any) -> bool:
    """A PROMOTED optical solid (e.g. a beam-splitter cube) carries its split on an
    ``OpticalSolidFaces`` "Beam Splitter" face / virtual plane, NOT a sequential BeamSplitter
    surface. Detect it so a promoted-BS scene still classifies as branching -- otherwise it is
    mistaken for the bug-0126 non-branching refractive solid and its launch collapses to a flat
    fan instead of revolving into a cone (bugs/0161)."""
    if not metadata:
        return False
    try:
        from KrakenOS.UI.optical_solid_metadata import (
            OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER,
            normalize_optical_solid_face_metadata,
        )

        normalized = normalize_optical_solid_face_metadata(metadata)
        for face in normalized.get("faces", []) or []:
            if str(face.get("function", "")) == "Beam Splitter":
                return True
        for plane in normalized.get("virtual_planes", []) or []:
            if str(plane.get("kind", "")) == OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER:
                return True
    except Exception:
        return False
    return False


def _optical_solid_faces_have_mirror_fold(metadata: Any) -> bool:
    """A PROMOTED optical solid that folds the path (a right-angle mirror cube) carries its
    reflection on an ``OpticalSolidFaces`` face whose ``function`` is "Mirror", NOT a sequential
    ``Mirror`` surface row. Detect it so a promoted-mirror fold still classifies as breaking
    rotational symmetry -- otherwise the folded scene is mistaken for the bug-0126 non-branching
    refractive solid and its launch collapses to a flat fan instead of revolving into a cone
    (bugs/0161, bugs/0186). A "Beam Splitter" face is intentionally NOT a fold here -- it keeps its
    real straight-through (bugs/0185 reflects the downstream chain only for a FULL mirror)."""
    if not metadata:
        return False
    try:
        from KrakenOS.UI.optical_solid_metadata import normalize_optical_solid_face_metadata

        normalized = normalize_optical_solid_face_metadata(metadata)
        for face in normalized.get("faces", []) or []:
            if str(face.get("function", "")) == "Mirror":
                return True
    except Exception:
        return False
    return False


def _trace_flags(
    rows_or_specs: list[Any],
    settings: dict[str, Any],
    *,
    has_physical_source: bool | None,
    nonseq_energy_probability: bool | None,
    nonseq_target_surface_index: int | None,
) -> dict[str, object]:
    rows = list(rows_or_specs or [])
    beam_splitter = False
    diffuse = False
    object_target = False
    optical_stl = False
    nonseq_geometry = False
    for row in rows:
        surface = _row_value(row, "surface", "")
        advanced = _row_advanced(row)
        if surface == BEAM_SPLITTER_SURFACE or BEAM_SPLITTER_ADVANCED_ATTR in advanced:
            beam_splitter = True
        elif _optical_solid_faces_have_beam_splitter(advanced.get("OpticalSolidFaces")):
            beam_splitter = True  # a PROMOTED beam-splitter cube (split on an OpticalSolidFaces face)
        if surface == DIFFUSE_OBJECT_SURFACE or DIFFUSE_SCATTER_ADVANCED_ATTR in advanced:
            diffuse = True
        if surface == OBJECT_TARGET_SURFACE:
            object_target = True
        if scene_graph_value_present(advanced.get("Solid_3d_stl")):
            optical_stl = True
        if surface == "Mirror" or any(abs(_row_float(row, key)) > 1e-9 for key in ("tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y", "desp_z")):
            nonseq_geometry = True
    target_index = nonseq_target_surface_index
    if target_index is None:
        target_index = _target_surface_index_from_settings(settings)
    source = has_physical_source
    if source is None:
        source = _settings_have_physical_source(settings)
    probability = nonseq_energy_probability
    if probability is None:
        probability = bool(settings.get("nonseq_energy_probability", False))
    return {
        "has_nonseq_geometry": nonseq_geometry,
        "has_physical_source": bool(source),
        "has_beam_splitter": beam_splitter,
        "has_diffuse_scatter": diffuse,
        "has_object_target": object_target,
        "has_optical_stl_solid": optical_stl,
        "has_probabilistic_nonseq": bool(probability),
        "target_surface_index": target_index,
    }


def _trace_reasons(flags: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    if flags["has_physical_source"]:
        reasons.append("physical source")
    if flags["has_beam_splitter"]:
        reasons.append("beam splitter")
    if flags["has_diffuse_scatter"]:
        reasons.append("diffuse scatter")
    if flags["has_object_target"]:
        reasons.append("object target")
    if flags["has_optical_stl_solid"]:
        reasons.append("STL optical solid")
    if flags["has_nonseq_geometry"]:
        reasons.append("off-axis/scene geometry")
    if flags["has_probabilistic_nonseq"]:
        reasons.append("probabilistic non-sequential coating")
    if flags["target_surface_index"] is not None:
        reasons.append("target surface")
    return reasons


def _row_value(row: Any, key: str, default: object = None) -> object:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _row_advanced(row: Any) -> dict[str, Any]:
    advanced = _row_value(row, "advanced", {})
    return advanced if isinstance(advanced, dict) else {}


def _row_float(row: Any, key: str) -> float:
    try:
        return float(_row_value(row, key, 0.0) or 0.0)
    except Exception:
        return 0.0


def _target_surface_index_from_settings(settings: dict[str, Any]) -> int | None:
    for key in ("nonseq_target_surface_index", "target_surface_index"):
        if key in settings:
            try:
                value = int(settings.get(key))
            except Exception:
                continue
            return value if value >= 0 else None
    text = str(settings.get("nonseq_target_surface", "Auto") or "Auto").strip()
    if not text or text == "Auto":
        return None
    try:
        value = int(text.split(":", 1)[0].strip())
    except Exception:
        return None
    return value if value >= 0 else None


def _settings_have_physical_source(settings: dict[str, Any]) -> bool:
    source_model = str(settings.get("source_model", SOURCE_MODEL_DEFAULT) or SOURCE_MODEL_DEFAULT).strip()
    if source_model and source_model != SOURCE_MODEL_DEFAULT:
        return True
    for spec in _settings_scene_source_specs(settings):
        if not isinstance(spec, dict):
            continue
        enabled = _settings_bool(spec.get("enabled", True))
        physical = _settings_bool(spec.get("physical", True))
        if enabled and physical:
            return True
    return False


def _settings_scene_source_specs(settings: dict[str, Any]) -> list[object]:
    value = settings.get("scene_sources", [])
    if isinstance(value, dict):
        value = value.get("sources", value.get("scene_sources", []))
    return list(value) if isinstance(value, (list, tuple)) else []


def _settings_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"0", "false", "no", "off", "disabled"}:
        return False
    return bool(text)
