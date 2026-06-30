"""bugs/0187 fix (3): trace a promoted FULL-mirror cube as a SEQUENTIAL ``Mirror``.

A promoted right-angle mirror cube reflects on an ``OpticalSolidFaces`` face whose
``function`` is "Mirror". Because it is a real CAD body the whole trace is forced
NON-sequential, and a mesh-mirror reflection flips the propagation sign; the AZ85
surrogate's IDEAL Thin Lenses (no real glass -- KrakenOS fakes the deflection) then
retroreflect after that sign flip, so 0 of 93 rays reach the sensor (the "ray
diverges" flag). See ``bugs/0187``.

Fix (3) keeps the layout but represents each promoted full-mirror cube as a
sequential ``Mirror`` surface for the TRACE only (the display still draws the cube).
The native sequential tracer folds the running coordinate frame on a ``Mirror`` row,
so the ideal Thin Lenses downstream behave, and -- crucially -- it composes an
ARBITRARY CHAIN of folds natively (two right-angle mirrors trace cleanly with no
extra machinery; the second fold is interpreted in the running, already-folded
frame).

The per-mirror tilt is solved CONVENTION-FREE: we know the cube's world face normal,
so the outgoing world direction is ``reflect(d_in, n)``; we try the principal
half-angle tilts, trace one chief ray through the partially-built sequential chain,
and keep the tilt whose real world exit direction matches. No hand-derived Euler /
AxisMove sign tables (those differ per axis and would silently mis-fold a second
mirror the user orients differently).
"""

from __future__ import annotations

import contextlib
import io
from typing import Any

import numpy as np

from KrakenOS.UI.trace_intent import _optical_solid_faces_have_mirror_fold

_AXIS_MOVE_REFLECT = 2.0


def _spec_get(spec: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(spec.get(key, default))
    except Exception:
        return float(default)


def mirror_fold_face_normal(advanced: Any) -> np.ndarray | None:
    """World normal of the promoted solid's Mirror face, or None if there is none."""
    if not isinstance(advanced, dict):
        return None
    metadata = advanced.get("OpticalSolidFaces")
    if not metadata:
        return None
    try:
        from KrakenOS.UI.optical_solid_metadata import normalize_optical_solid_face_metadata

        normalized = normalize_optical_solid_face_metadata(metadata)
    except Exception:
        return None
    for face in normalized.get("faces", []) or []:
        if str(face.get("function", "")) != "Mirror":
            continue
        normal = face.get("normal")
        if normal is None:
            continue
        try:
            vec = np.asarray(normal, dtype=float).reshape(-1)[:3]
        except Exception:
            continue
        if vec.size < 3 or not np.all(np.isfinite(vec)):
            continue
        norm = float(np.linalg.norm(vec))
        if norm <= 1e-9:
            continue
        return vec / norm
    return None


def _reflect(direction: np.ndarray, normal: np.ndarray) -> np.ndarray:
    d = np.asarray(direction, dtype=float).reshape(-1)[:3]
    n = np.asarray(normal, dtype=float).reshape(-1)[:3]
    return d - 2.0 * float(np.dot(d, n)) * n


def _is_promoted_mirror_fold(spec: dict) -> bool:
    if str(spec.get("surface", "")) in {"Object", "Image", "Mirror"}:
        return False
    advanced = spec.get("advanced")
    return _optical_solid_faces_have_mirror_fold(
        advanced.get("OpticalSolidFaces") if isinstance(advanced, dict) else None
    )


def scene_nonseq_trigger_is_only_promoted_full_mirrors(row_specs: list[dict]) -> bool:
    """True iff the scene has >=1 promoted full-mirror fold and EVERY non-sequential
    trigger is such a fold (no beam splitter / refractive mesh solid that genuinely
    needs the non-seq tracer). Only then is it safe to fold to a sequential trace."""
    from KrakenOS.UI.optical_solid_metadata import normalize_optical_solid_face_metadata

    saw_mirror_fold = False
    for spec in row_specs or []:
        advanced = spec.get("advanced")
        metadata = advanced.get("OpticalSolidFaces") if isinstance(advanced, dict) else None
        if not metadata:
            continue
        if _optical_solid_faces_have_mirror_fold(metadata):
            saw_mirror_fold = True
            continue
        # A promoted solid WITHOUT a mirror fold face (refractive lens, beam splitter,
        # any other inferred output port) keeps a real non-sequential interaction.
        try:
            normalized = normalize_optical_solid_face_metadata(metadata)
        except Exception:
            return False
        if normalized.get("faces") or normalized.get("virtual_planes"):
            return False
    return saw_mirror_fold


def _build_probe_system(specs: list[dict]):
    from KrakenOS.UI.layout_editor import _build_system_from_specs

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        system = _build_system_from_specs(
            [dict(s) for s in specs], apply_optical_solid_output_ports=False
        )
        system.energy_probability = 0
    return system


def _chief_exit_direction(specs: list[dict]) -> np.ndarray | None:
    """Trace the on-axis chief ray through ``specs`` and return its world direction
    cosines at the final surface, or None if it does not reach the end."""
    import KrakenOS as Kos

    try:
        system = _build_probe_system(specs)
        rays = Kos.raykeeper(system)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
            rays.push()
        _, _, _, L, M, N = rays.pick(-1)
    except Exception:
        return None
    vec = np.asarray([L, M, N], dtype=float).reshape(-1)[:3]
    if vec.size < 3 or not np.all(np.isfinite(vec)):
        return None
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-9:
        return None
    return vec / norm


_DUMMY_IMAGE = {
    "surface": "Image",
    "name": "fold-probe image",
    "rc": 0.0,
    "thickness": 0.0,
    "diameter": 50.0,
    "tilt_x": 0.0,
    "tilt_y": 0.0,
    "tilt_z": 0.0,
    "desp_x": 0.0,
    "desp_y": 0.0,
    "desp_z": 0.0,
    "axis_move": 0.0,
    "glass": "AIR",
}


def _sequential_mirror_spec(template: dict, tilt: dict[str, float]) -> dict:
    out = dict(template)
    out.update(
        surface="Mirror",
        glass="MIRROR",
        rc=0.0,
        axis_move=_AXIS_MOVE_REFLECT,
        advanced={},
        tilt_x=float(tilt.get("tilt_x", 0.0)),
        tilt_y=float(tilt.get("tilt_y", 0.0)),
        tilt_z=float(tilt.get("tilt_z", 0.0)),
        desp_z=0.0,
    )
    return out


def _solve_mirror_tilt(
    prefix_specs: list[dict],
    mirror_template: dict,
    face_normal: np.ndarray,
) -> dict[str, float] | None:
    """Find the sequential-Mirror tilt whose real fold matches the cube's face normal.

    ``prefix_specs`` are the already-synthesized rows up to (not including) the mirror.
    The incoming world direction is the chief-ray exit of the prefix; the target
    outgoing direction is its reflection in the face normal. We trace each principal
    half-angle candidate through the actual prefix (so the running, possibly already
    folded, frame is handled) and keep the best world-direction match."""
    d_in = _chief_exit_direction(list(prefix_specs) + [dict(_DUMMY_IMAGE)])
    if d_in is None:
        d_in = np.asarray([0.0, 0.0, 1.0], dtype=float)
    target = _reflect(d_in, face_normal)
    target_norm = float(np.linalg.norm(target))
    if target_norm <= 1e-9:
        return None
    target = target / target_norm
    fold_angle = float(np.degrees(np.arccos(np.clip(float(np.dot(d_in, target)), -1.0, 1.0))))
    half = fold_angle / 2.0
    if half <= 1e-6:
        return None
    best: dict[str, float] | None = None
    best_cos = -2.0
    for axis in ("tilt_x", "tilt_y", "tilt_z"):
        for sign in (1.0, -1.0):
            tilt = {"tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0}
            tilt[axis] = sign * half
            probe = list(prefix_specs) + [_sequential_mirror_spec(mirror_template, tilt), dict(_DUMMY_IMAGE)]
            exit_dir = _chief_exit_direction(probe)
            if exit_dir is None:
                continue
            cos = float(np.dot(exit_dir, target))
            if cos > best_cos:
                best_cos = cos
                best = tilt
    if best is None or best_cos < 0.999:
        return None
    return best


def fold_promoted_mirror_specs_to_sequential(
    row_specs: list[dict],
) -> tuple[list[dict], list[dict[str, object]]]:
    """Convert each promoted full-mirror cube row into a sequential ``Mirror`` surface.

    Returns ``(new_specs, records)``. ``records`` is empty (and ``new_specs`` is a
    plain copy) when no promoted mirror fold is present, so non-folded layouts are
    untouched. The mirror's axial displacement is reseated onto the preceding row so
    the AxisMove=2 reflection folds cleanly from the running axis. General for an
    arbitrary chain of folds."""
    specs = [dict(s) for s in (row_specs or [])]
    records: list[dict[str, object]] = []
    out: list[dict] = []
    for index, spec in enumerate(specs):
        if not _is_promoted_mirror_fold(spec):
            out.append(spec)
            continue
        face_normal = mirror_fold_face_normal(spec.get("advanced"))
        if face_normal is None:
            out.append(spec)
            continue
        tilt = _solve_mirror_tilt(out, spec, face_normal)
        if tilt is None:
            # Could not establish a clean fold; leave the row as-is (non-seq trace).
            out.append(spec)
            continue
        mirror = _sequential_mirror_spec(spec, tilt)
        # Reseat the cube's axial displacement onto the preceding row so the mirror
        # vertex stays at its world station while AxisMove=2 folds from the axis.
        desp_z = _spec_get(spec, "desp_z")
        if abs(desp_z) > 1e-9 and out:
            prior = dict(out[-1])
            prior["thickness"] = _spec_get(prior, "thickness") + desp_z
            out[-1] = prior
        out.append(mirror)
        records.append(
            {
                "row_index": int(index),
                "tilt": dict(tilt),
                "reseated_desp_z": float(desp_z),
                "face_normal": [float(v) for v in face_normal],
            }
        )
    if not records:
        return [dict(s) for s in (row_specs or [])], []
    return out, records
