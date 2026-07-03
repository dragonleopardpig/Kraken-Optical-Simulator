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


def _unit(vector: Any) -> np.ndarray:
    vec = np.asarray(vector, dtype=float).reshape(-1)[:3]
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm > 1e-12 else vec


def promoted_mirror_world_center(specs: list[dict], row_index: int) -> np.ndarray | None:
    """World point on the promoted mirror's fold plane: the cumulative axial station of
    the mirror row plus its own decenter. The real Mirror face passes through it, so it
    anchors the reflection plane used to re-fold the display rays."""
    if not (0 <= int(row_index) < len(specs or [])):
        return None
    z = sum(_spec_get(specs[i], "thickness") for i in range(int(row_index)))
    z += _spec_get(specs[int(row_index)], "desp_z")
    return np.array(
        [
            _spec_get(specs[int(row_index)], "desp_x"),
            _spec_get(specs[int(row_index)], "desp_y"),
            z,
        ],
        dtype=float,
    )


def mirror_reflection_flip_plane_normal(
    chief_in: Any, face_normal: Any
) -> np.ndarray | None:
    """Unit normal of the world plane across which the ROTATION-folded downstream must
    be reflected to become the physical MIRROR reflection.

    The sequential tracer folds the running frame by a proper ROTATION (rotate_x/y/z +
    AxisMove=2); a real mirror is an improper REFLECTION. The two share the chief
    outgoing direction ``d_out`` and the sagittal axis ``s = d_in x d_out`` (both fix
    them), so their difference is the reflection across the plane they span -- whose
    normal is ``d_out x s``. Reflecting the rotation-folded leg across that plane (then
    re-anchoring onto the real face) yields the physical reflection for ALL rays."""
    d_in = _unit(chief_in)
    normal = _unit(face_normal)
    d_out = _unit(_reflect(d_in, normal))
    sagittal = np.cross(d_in, d_out)
    s_norm = float(np.linalg.norm(sagittal))
    if s_norm < 1e-9:
        return None  # no fold (incoming already parallel to outgoing)
    sagittal = sagittal / s_norm
    flip = np.cross(d_out, sagittal)
    flip_norm = float(np.linalg.norm(flip))
    if flip_norm < 1e-9:
        return None
    return flip / flip_norm


def _line_plane_intersection(
    p0: np.ndarray, direction: np.ndarray, plane_point: np.ndarray, plane_normal: np.ndarray
) -> np.ndarray | None:
    denom = float(np.dot(direction, plane_normal))
    if abs(denom) < 1e-12:
        return None
    t = float(np.dot(np.asarray(plane_point, dtype=float) - p0, plane_normal)) / denom
    return p0 + t * direction


def correct_folded_mirror_ray_points(
    points: Any,
    fold_center: Any,
    face_normal: Any,
    chief_in: Any,
    *,
    cos_fold_max: float = 0.2,
) -> np.ndarray | None:
    """bugs/0192: re-fold ONE display ray polyline from the sequential ROTATION fold to
    the physical MIRROR reflection off the real face plane.

    Locate the mirror kink (the sharpest ~90 deg turn), intersect the incoming leg with
    the real face plane (through ``fold_center``, normal ``face_normal``) to get the true
    hypotenuse hit ``K``, then replace every post-kink vertex with its reflection across
    the flip plane, translated so the kink lands on ``K``. Incoming vertices are left
    untouched. Returns a new array (input shape preserved) or None when the ray has no
    clear fold (e.g. clipped before the mirror)."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] < 3:
        return None
    coords = pts[:, :3]
    flip = mirror_reflection_flip_plane_normal(chief_in, face_normal)
    if flip is None:
        return None
    segments = np.diff(coords, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    valid = lengths > 1e-9
    if int(valid.sum()) < 2:
        return None
    units = np.zeros_like(segments)
    units[valid] = segments[valid] / lengths[valid, None]
    cos_turn = np.sum(units[:-1] * units[1:], axis=1)
    kink_seg = int(np.argmin(cos_turn))
    if cos_turn[kink_seg] > cos_fold_max:
        return None  # no ~90 deg fold -> not a mirror kink
    k = kink_seg + 1
    normal = _unit(face_normal)
    center = np.asarray(fold_center, dtype=float).reshape(-1)[:3]
    kink = _line_plane_intersection(coords[k - 1], units[k - 1], center, normal)
    if kink is None:
        return None
    reflected_kink = coords[k] - 2.0 * float(np.dot(coords[k], flip)) * flip
    tau = kink - reflected_kink
    out = coords.copy()
    tail = coords[k:]
    out[k:] = tail - 2.0 * (tail @ flip)[:, None] * flip[None, :] + tau
    if pts.shape[1] > 3:
        result = pts.copy()
        result[:, :3] = out
        return result
    return out


def rigid_reflect_folded_mirror_ray_points(
    points: Any,
    fold_anchor: Any,
    flip: Any,
    *,
    cos_fold_max: float = 0.2,
) -> np.ndarray | None:
    """bugs/0203 (#5): convert a rotation-folded display ray to the physical MIRROR
    reflection with a SINGLE RIGID flip -- no per-ray translation.

    The straight-equivalent path (``_fold_straight_equivalent_display_rays``) has already
    rotated every post-station vertex onto the folded branch, so the whole outgoing leg is
    a rigid image of the converging equivalent cone (it still focuses). The rotation fold
    and the physical mirror differ only by the meridional flip across the plane spanned by
    the outgoing chief and the sagittal axis (normal ``flip = d_out x s``). Reflecting the
    post-kink tail across THAT plane through the folded fold-point ``fold_anchor`` is rigid,
    so it preserves the focus (which lies on the outgoing chief axis -> in the flip plane ->
    fixed) while un-flipping the off-axis diagonal for ALL rays at once.

    ``correct_folded_mirror_ray_points`` instead reflected across the origin plane and then
    re-anchored PER RAY (``tau``), which sheared the cone (the user's "focusing rays vary
    left to right"). This preserves the tight waist on the drawn detector; see bugs/0203.
    Returns a new array (input shape preserved) or None when the ray has no clear ~90 deg
    fold (e.g. clipped before the mirror)."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] < 3:
        return None
    flip_n = _unit(flip)
    if float(np.linalg.norm(flip_n)) < 1e-9:
        return None
    anchor = np.asarray(fold_anchor, dtype=float).reshape(-1)[:3]
    coords = pts[:, :3]
    segments = np.diff(coords, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    valid = lengths > 1e-9
    if int(valid.sum()) < 2:
        return None
    units = np.zeros_like(segments)
    units[valid] = segments[valid] / lengths[valid, None]
    cos_turn = np.sum(units[:-1] * units[1:], axis=1)
    kink_seg = int(np.argmin(cos_turn))
    if cos_turn[kink_seg] > cos_fold_max:
        return None  # no ~90 deg fold -> not a mirror kink
    k = kink_seg + 1
    tail = coords[k:]
    s = (tail - anchor) @ flip_n
    out = pts.copy()
    out[k:, :3] = tail - 2.0 * s[:, None] * flip_n[None, :]
    return out


def reflect_straight_equivalent_ray_points(
    points: Any,
    plane_point: Any,
    plane_normal: Any,
) -> np.ndarray | None:
    """bugs/0205: fold ONE straight-equivalent display ray by REFLECTING its
    downstream (past-mirror) portion about the mirror plane -- a pure isometry.

    The straight-equivalent rays image to a real focus along the unfolded axis (they
    are traced through the flat-plate equivalent, no bend yet). The physical fold is
    the reflection of that converging cone about the mirror plane. Reflection is an
    ISOMETRY, which is exactly what makes this both correct and general:

      * the incoming leg (same side of the plane as the launch point) is left
        UNTOUCHED -> its cone is preserved. This fixes bugs/0205: rotating every
        post-station vertex about a fold anchor instead mapped the incoming cone's
        meridional spread into axial displacement, collapsing it to a flat fan;
      * the outgoing leg is reflected -> still a congruent converging cone, so the
        focus is preserved (an isometry cannot move a focus off the detector);
      * the vertex where the ray crosses the plane is a FIXED POINT of the
        reflection, so the kink is exact and continuous for every ray.

    The plane is ``(plane_point, plane_normal)`` -- both derived from the scene by the
    caller (the mirror's real face normal and its world station); NOTHING here is
    axis- or scene-specific. A vertex ``p`` with signed distance ``d = (p - p0).n_hat``
    maps to ``p - 2 d n_hat``. "Downstream" is the side of the plane OPPOSITE the ray's
    own launch point (``points[0]``) -- decided per ray from the sign of its first
    vertex, so no +Z / propagation-direction assumption is baked in. A crossing vertex
    is inserted where the polyline pierces the plane so the kink lands exactly on it.
    Extra ray columns (wavelength, intensity, ...) are preserved and interpolated at
    the inserted vertex. Returns a new array (column count preserved) or None when the
    ray never crosses the plane (e.g. launched on the plane, or clipped before it)."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
        return None
    normal = _unit(plane_normal)
    if float(np.linalg.norm(normal)) < 1e-9:
        return None
    p0 = np.asarray(plane_point, dtype=float).reshape(-1)[:3]
    coords = pts[:, :3]
    signed = (coords - p0) @ normal
    if abs(float(signed[0])) < 1e-9:
        return None  # launch point sits on the plane -> incoming side is ambiguous
    downstream = (signed * float(np.sign(signed[0]))) < 0.0
    if not downstream.any() or downstream.all():
        return None  # ray never crosses the mirror plane
    rows: list[np.ndarray] = []
    for i in range(len(pts)):
        if downstream[i]:
            reflected = pts[i].copy()
            reflected[:3] = coords[i] - 2.0 * float(signed[i]) * normal
            rows.append(reflected)
        else:
            rows.append(pts[i].copy())
        if i < len(pts) - 1 and downstream[i] != downstream[i + 1]:
            denom = float(signed[i] - signed[i + 1])
            if abs(denom) > 1e-12:
                t = float(signed[i]) / denom
                rows.append(pts[i] + t * (pts[i + 1] - pts[i]))  # on plane -> fixed
    return np.asarray(rows, dtype=float)


def free_placed_mirror_world_planes(
    specs: list[dict],
    exclude_row_indices: "set[int] | None" = None,
) -> list[tuple[int, np.ndarray, np.ndarray]]:
    """bugs/0213: REAL-world reflection planes for FREE-PLACED faced mirrors.

    A mirror the user drops onto an already-folded leg and then orients (a promoted
    solid that ``promote`` tags with a recorded ``center_world``) folds the beam off its
    OWN oriented face by physics. But its ``desp`` encodes the FOLDED-world drop-point
    (``desp_x`` = folded X, ``desp_z`` = ``center_world_z - station``), NOT the unfolded
    sequential station, so ``_solve_mirror_tilt`` cannot seat it and it yields no
    sequential-fold record -- the straight-equivalent composition (which needs each
    mirror's UNFOLDED plane) skips it. Its display rays are instead folded by reflecting
    the ALREADY-folded polyline about the mirror's REAL world plane:

      * point  = its world centre (``promoted_mirror_world_center``: ``station + desp_z``
        cancels back to ``center_world``);
      * normal = the Mirror face's LOCAL normal rotated into the world by the row tilt
        (``n_world = n_local @ R(tilt).T``) -- so the fold direction is the mirror's
        ORIENTATION (``r = d - 2(d.n)n``), never a hard-coded axis.

    Applied AFTER the records reflection lands the rays on the real folded branches (the
    plane lives in the real folded world, not the straight frame). Layout-authored
    cascade prisms carry no ``center_world`` marker, so they never appear here (penta is
    untouched). Rows already covered by a sequential record (``exclude_row_indices``) are
    skipped so a working fold is not double-folded. Returns ``(row_index, world_centre,
    world_normal)`` per free-placed mirror, ordered by station ASCENDING (nearer folds
    first)."""
    from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts

    exclude = {int(i) for i in (exclude_row_indices or set())}
    planes: list[tuple[int, np.ndarray, np.ndarray]] = []
    for idx, spec in enumerate(specs or []):
        if int(idx) in exclude:
            continue
        advanced = spec.get("advanced")
        if not isinstance(advanced, dict):
            continue
        free_placed = any(
            isinstance(advanced.get(key), dict) and advanced[key].get("center_world") is not None
            for key in ("StepOverlayPromotion", "StepNativePromotion")
        )
        if not free_placed:
            continue
        local_normal = mirror_fold_face_normal(advanced)
        if local_normal is None:
            continue
        center = promoted_mirror_world_center(specs, idx)
        if center is None:
            continue
        rotation = rotation_matrix_from_kraken_tilts(
            _spec_get(spec, "tilt_x"),
            _spec_get(spec, "tilt_y"),
            _spec_get(spec, "tilt_z"),
        )
        world_normal = np.asarray(local_normal, dtype=float).reshape(3) @ np.asarray(rotation, dtype=float).T
        n_norm = float(np.linalg.norm(world_normal))
        if n_norm <= 1e-9 or not np.all(np.isfinite(world_normal)):
            continue
        planes.append(
            (int(idx), np.asarray(center, dtype=float).reshape(3), world_normal / n_norm)
        )
    planes.sort(key=lambda plane: plane[0])
    return planes


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
        chief_in = _chief_exit_direction(list(out) + [dict(_DUMMY_IMAGE)])
        if chief_in is None:
            chief_in = np.asarray([0.0, 0.0, 1.0], dtype=float)
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
                "chief_in": [float(v) for v in _unit(chief_in)],
            }
        )
    if not records:
        return [dict(s) for s in (row_specs or [])], []
    return out, records
