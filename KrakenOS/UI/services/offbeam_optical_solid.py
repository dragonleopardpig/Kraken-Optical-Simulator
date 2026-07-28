"""Off-beam promoted optical-solid neutralisation (bugs/0065).

North Star: true non-sequential is the native model; an off-beam inert solid is
never hit, so it must contribute ZERO optical effect.  A promoted optical SOLID
(an imported STEP body -- e.g. a beam-splitter cube) that the user parks well
clear of the beam must therefore behave as a **display-only scene body**: it
keeps drawing in 3-D but stays outside the optical trace path until it is on the
beam OR carries an active coating (Mirror / TIR / Beam Splitter / Absorber).

The leak this fixes: the solid's lateral decenter lives in the row's
``desp_x``/``desp_y`` and is copied verbatim onto ``surface.DespX``/``DespY`` in
``layout_editor._build_system_from_specs`` as a *propagating* coordinate break,
so an off-beam cube enters the centered prescription and corrupts the paraxial /
best-focus / image-circle solve -- focus lands short of the detector, the image
circle is offset, and the rays appear to "chase" the solid (the recording in
``attachment/recorded_bug_repros/flag_20260612_073237_607``).  Forcing the trace
sequential (the reverted ``02323d2``) only turned the off-axis solid into a
vignetting surface.  The real fix is to drop the inert off-beam solid out of the
prescription entirely.

``neutralize_offbeam_inert_solids`` returns a copy of ``row_specs`` in which each
off-beam inert promoted solid is replaced by a flat, zero-power AIR surface at
the on-axis station, keeping the SAME ``thickness`` / ``diameter`` / surface kind
so the surface count and axial chain are preserved (no index desync, detector
station unchanged) while every optical and coordinate-break perturbation is
removed.  The 3-D body still draws -- the inspector keys on the live row overlay,
not on these transient build specs (the same property that lets bugs/0021's
missing-mesh neutralisation keep its placeholder body).

Scope: STEP-overlay promoted single-row optical solids only (mirrors
``layout_analysis_display._is_open3d_promoted_optical_solid_row``).  Intentional
decentered mirrors/folds, coated splitters, and multi-row native promotions are
left untouched.
"""

from __future__ import annotations

import copy
import math

import numpy as np

from KrakenOS.UI.services.advanced_surface_attrs import (
    _advanced_surface_attrs_from_spec,
    _canonical_advanced_surface_attr,
)
from KrakenOS.UI.optical_solid_metadata import normalize_optical_solid_face_metadata

# Face functions that make a solid optically active -- such a solid is "coated"
# in North-Star terms and stays in the trace even when geometrically off-axis.
OPTICAL_SOLID_ACTIVE_FACE_FUNCTIONS = frozenset(
    {"Mirror", "TIR", "Beam Splitter", "Absorber/Mechanical"}
)

# A solid counts as off-beam only when its nearest transverse edge clears the
# beam radius by this factor AND by this absolute margin. The beam never exceeds
# the widest clear aperture (``beam_clear_radius``), so a solid whose inner edge
# clears that radius by ~25 % is genuinely outside the beam. The original 2x
# factor (bugs/0074) was too strict: a cube parked clear of the beam (inner edge
# ~38 vs radius 23) fell in the 23..46 gray zone, stayed in the sequential chain,
# and its thickness shoved the downstream detector past best focus.
_OFFBEAM_BEAM_CLEARANCE_FACTOR = 1.25
_OFFBEAM_MIN_CLEARANCE_MM = 1.0

# Advanced attrs dropped from a neutralised spec so it no longer reads as a
# promoted optical solid anywhere downstream (idempotent re-neutralisation).
_DROP_ADVANCED_ATTRS = frozenset(
    {
        "OpticalSolidFaces",
        "StepOverlayPromotion",
        "StepNativePromotion",
        "StepAnalyticPromotion",
        "LiveStepOverlayTrace",
        "OpticalSolidSourcePath",
        "OpticalSolidSourceFormat",
    }
)


def _float_or_zero(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _solid_stl_value(advanced: dict) -> str:
    return str(advanced.get("Solid_3d_stl", "") or "").strip()


def is_promoted_optical_solid_spec(spec: dict) -> bool:
    """True for a STEP-overlay promoted optical-solid spec.

    Mirrors ``_open3d_step_label_for_optical_solid_row``: a real ``Solid_3d_stl``
    plus either ``StepOverlayPromotion`` metadata or a STEP source format/suffix.
    """
    if not isinstance(spec, dict):
        return False
    advanced = _advanced_surface_attrs_from_spec(spec)
    if _solid_stl_value(advanced) in {"", "None"}:
        return False
    if isinstance(advanced.get("StepOverlayPromotion"), dict):
        return True
    source_format = str(advanced.get("OpticalSolidSourceFormat", "") or "").strip().upper()
    if source_format in {"STEP", "STP"}:
        return True
    source_path = str(advanced.get("OpticalSolidSourcePath", "") or "").strip().lower()
    return source_path.endswith((".step", ".stp"))


def solid_has_active_coating(spec: dict) -> bool:
    """True if any assigned face carries an active optical function ("coated").

    Reads through ``normalize_optical_solid_face_metadata`` so it sees the real
    persisted schema, where ``OpticalSolidFaces`` is a dict
    ``{"version", "faces": [...], ...}`` -- not the bare face list. A raw
    ``isinstance(faces, list)`` check silently treated every real coated solid as
    UNCOATED, so a Beam-Splitter cube parked off the beam was wrongly neutralised
    out of the non-sequential trace and its body snapped onto the optical axis
    (bugs/0066).
    """
    advanced = _advanced_surface_attrs_from_spec(spec)
    metadata = normalize_optical_solid_face_metadata(advanced.get("OpticalSolidFaces"))
    for face in metadata.get("faces", []) or []:
        if not isinstance(face, dict):
            continue
        function = str(face.get("function", face.get("role", "")) or "").strip()
        if function in OPTICAL_SOLID_ACTIVE_FACE_FUNCTIONS:
            return True
    return False


def solid_lateral_decenter(spec: dict) -> float:
    """Lateral decenter that leaks into ``surface.DespX``/``DespY``.

    ``desp_x``/``desp_y`` is exactly the quantity ``_build_system_from_specs``
    copies onto the built surface as a propagating coordinate break, so it is the
    causally exact off-beam signal.
    """
    return math.hypot(
        _float_or_zero(spec.get("desp_x", 0.0)),
        _float_or_zero(spec.get("desp_y", 0.0)),
    )


def solid_transverse_half_extent(spec: dict) -> float:
    """Half of the solid's larger transverse footprint span.

    Prefers the drag-invariant STEP-overlay world bounds; falls back to half the
    surface clear diameter when promotion bounds are absent.
    """
    advanced = _advanced_surface_attrs_from_spec(spec)
    promotion = advanced.get("StepOverlayPromotion")
    if isinstance(promotion, dict):
        lo = promotion.get("bounds_min_world")
        hi = promotion.get("bounds_max_world")
        if (
            isinstance(lo, (list, tuple))
            and isinstance(hi, (list, tuple))
            and len(lo) >= 2
            and len(hi) >= 2
        ):
            span_x = abs(_float_or_zero(hi[0]) - _float_or_zero(lo[0]))
            span_y = abs(_float_or_zero(hi[1]) - _float_or_zero(lo[1]))
            half = 0.5 * max(span_x, span_y)
            if half > 0.0:
                return half
    # The ``diameter`` field is a FULL clear-aperture diameter project-wide
    # (KrakenOS draws apertures at Diameter/2), so the transverse half-extent is
    # half of it -- the same units as the bounds path above (bugs/0073).
    return 0.5 * max(_float_or_zero(spec.get("diameter", 0.0)), 0.0)


def beam_clear_radius(row_specs: list[dict]) -> float:
    """Largest on-beam optical semi-diameter -- the beam envelope radius.

    Object/Image planes and promoted solids are excluded: solids do not define
    the beam, and Object/Image apertures are oversized stand-ins.

    The ``diameter`` field is a FULL clear-aperture diameter project-wide
    (KrakenOS draws every aperture at ``Diameter/2`` -- ``Prerequisites3D``,
    ``Display``, ``PupilTool`` -- and an Image row's diameter is the literal
    image-circle "Ø"). ``is_offbeam_inert_solid_spec`` compares this radius
    against RADIAL quantities (lateral decenter, transverse half-extent), so we
    return the SEMI-diameter. Returning the full diameter (bugs/0073) doubled the
    off-beam clearance threshold, so a genuinely off-beam solid was left in the
    centered prescription and its decenter leaked as a propagating coordinate
    break that bent the rays.
    """
    max_diameter = 0.0
    for spec in row_specs or []:
        if not isinstance(spec, dict):
            continue
        surface = str(spec.get("surface", "") or "").strip()
        if surface in {"Object", "Image"}:
            continue
        if is_promoted_optical_solid_spec(spec):
            continue
        max_diameter = max(max_diameter, _float_or_zero(spec.get("diameter", 0.0)))
    return 0.5 * max_diameter


def is_offbeam_solid_spec(spec: dict, beam_radius: float) -> bool:
    """True when a promoted solid sits clearly clear of the beam (geometry only).

    Ignores coating: a coated splitter parked off the beam is just as much
    out of the optical path as an uncoated one, so it must be axially inert too
    (bugs/0074). Coating only decides whether the solid is also *optically*
    neutralised (see ``is_offbeam_inert_solid_spec``).
    """
    if beam_radius <= 0.0:
        return False
    if not is_promoted_optical_solid_spec(spec):
        return False
    inner_edge = solid_lateral_decenter(spec) - solid_transverse_half_extent(spec)
    if inner_edge <= 0.0:
        return False
    threshold = max(
        beam_radius * _OFFBEAM_BEAM_CLEARANCE_FACTOR,
        beam_radius + _OFFBEAM_MIN_CLEARANCE_MM,
    )
    return inner_edge >= threshold


def is_offbeam_inert_solid_spec(spec: dict, beam_radius: float) -> bool:
    """True when a promoted UNCOATED solid sits clearly clear of the beam.

    Such a solid is optically inert (no active face), so it is fully neutralised
    -- flat zero-power AIR with no coordinate break. A coated splitter is off-beam
    too (``is_offbeam_solid_spec``) but stays in the trace; it is only made
    axially inert, never optically neutralised.
    """
    return is_offbeam_solid_spec(spec, beam_radius) and not solid_has_active_coating(spec)


def _neutralize_advanced_container(container) -> None:
    if not isinstance(container, dict):
        return
    for key in list(container.keys()):
        canonical = _canonical_advanced_surface_attr(key)
        if canonical == "Solid_3d_stl":
            container[key] = "None"
        elif canonical in _DROP_ADVANCED_ATTRS:
            del container[key]


def neutralized_offbeam_solid_spec(spec: dict) -> dict:
    """A flat zero-power AIR copy of an off-beam solid spec.

    Drops the solid-ness AND the coordinate break AND the axial footprint:
    ``desp``/``tilt`` are zeroed (no propagating lateral break) and ``thickness``
    is zeroed so the parked solid contributes nothing to the optical chain -- the
    downstream Object/Image/detector stay exactly where they were before the solid
    was dropped in. ``diameter`` and surface kind are kept so the surface count is
    intact. Preserving the thickness (bugs/0065) left the solid as a real air gap
    that shoved the detector past best focus (bugs/0074); the body still draws at
    its world station from the live row + ``offbeam_neutralized_body_transform``.
    """
    new_spec = copy.deepcopy(spec)
    for key in ("desp_x", "desp_y", "desp_z", "tilt_x", "tilt_y", "tilt_z"):
        new_spec[key] = 0.0
    new_spec["thickness"] = 0.0
    new_spec["rc"] = 0.0
    new_spec["glass"] = "AIR"
    _neutralize_advanced_container(new_spec)
    for key in ("advanced", "advanced_attrs", "surface_attrs"):
        _neutralize_advanced_container(new_spec.get(key))
    return new_spec


def axially_inert_offbeam_solid_spec(spec: dict) -> dict:
    """An off-beam solid kept optically active but with zero axial footprint.

    For a COATED splitter parked off the beam (bugs/0066 keeps it in the
    non-sequential trace, body off-axis): the rays never reach it, so its glass
    thickness must not extend the axial chain and push the detector (bugs/0074).
    Coating, glass and ``desp`` (the off-axis body station) are all preserved --
    only the chain ``thickness`` is zeroed.
    """
    new_spec = copy.deepcopy(spec)
    new_spec["thickness"] = 0.0
    return new_spec


def _spec_face_folds_beam(spec: dict) -> bool:
    """bugs/0457: True when this promoted solid has a face that FOLDS the beam.

    ``_is_promoted_mirror_fold`` demands a MIRROR face, so a BEAM SPLITTER -- which folds
    light just as surely, it merely also transmits -- was invisible to the reached-fold walk.
    Deliberately NOT fixed by widening ``_is_promoted_mirror_fold``: that predicate also gates
    fold-to-sequential, and a splitter scene must stay non-sequential (trace_mode_north_star).
    """
    if not isinstance(spec, dict):
        return False
    advanced = _advanced_surface_attrs_from_spec(spec)
    metadata = normalize_optical_solid_face_metadata(advanced.get("OpticalSolidFaces"))
    for face in metadata.get("faces", []) or []:
        if not isinstance(face, dict):
            continue
        function = str(face.get("function", face.get("role", "")) or "").strip().lower()
        if "split" in function or "mirror" in function:
            return True
    return False


def _spec_face_rotation(spec: dict):
    """bugs/0457: the rotation taking a face's LOCAL normal/centroid into WORLD.

    Face metadata is stored in the solid's own frame. The walk below used to consume it as
    if it were world, which is invisible while every fold is an untilted mirror -- and wrong
    the moment one is not. The user's BS plate carries ``tilt_z = -90``: its diagonal reads
    as a Y-Z tilt locally and folds in X-Z in world, so the un-rotated walk reflected the
    beam to -Y, missed the downstream fold mirror entirely, and let it be neutralised.
    """
    try:
        from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts

        return np.asarray(
            rotation_matrix_from_kraken_tilts(
                float(spec.get("tilt_x", 0.0) or 0.0),
                float(spec.get("tilt_y", 0.0) or 0.0),
                float(spec.get("tilt_z", 0.0) or 0.0),
            ),
            dtype=float,
        ).reshape(3, 3)
    except Exception:
        return np.eye(3, dtype=float)


def folded_beam_reached_mirror_fold_indices(row_specs: list[dict]) -> set[int]:
    """Indices of promoted MIRROR-FOLD solids the FOLDED beam actually reaches.

    bugs/0243: ``is_offbeam_solid_spec`` classifies by lateral distance from the
    straight +Z axis -- correct for a solid PARKED clear of the beam, but a
    free-placed 2nd fold mirror legitimately sits far off +Z ON THE FOLDED ARM.
    Neutralising it zeroed its row thickness, so the output-port follower walk
    seated the folded Image/detector a full mirror-thickness SHORT of the
    prescription station: the QE/paraxial solve focused at the prescription
    plane while the drawn+traced sensor sat a plate early -- the user's
    persistent "still the same error" defocus after every FOV solve.

    Walk the beam analytically (the same face-hit rule as the bugs/0224 pose
    walk): start at the origin along +Z; at each promoted mirror-fold row in
    prescription order, intersect the current leg with the mirror's face plane;
    a FORWARD hit landing within the face extent (sqrt(area)+2mm, the 0224
    radius) is a real fold -- record it and reflect the leg. Anything the walk
    never reaches stays a parked body for the caller to neutralise.
    """
    from KrakenOS.UI.services.folded_sequential_fold import (
        _is_promoted_mirror_fold,
        promoted_mirror_world_center,
    )

    specs = list(row_specs or [])
    reached: set[int] = set()
    # bugs/0457: walk BOTH legs -- a splitter folds one arm and transmits the other, and a
    # solid on EITHER arm is genuinely reached. Being "reached" only PRESERVES a spec, so a
    # false positive keeps a thickness rather than corrupting the chain.
    legs: list[tuple[np.ndarray, np.ndarray]] = [
        (np.zeros(3, dtype=float), np.asarray((0.0, 0.0, 1.0), dtype=float))
    ]
    guard = 0
    while legs and guard < 64:
        guard += 1
        origin, direction = legs.pop(0)
        for index, spec in enumerate(specs):
            if not isinstance(spec, dict):
                continue
            if not (_is_promoted_mirror_fold(spec) or _spec_face_folds_beam(spec)):
                continue
            advanced = spec.get("advanced") if isinstance(spec.get("advanced"), dict) else {}
            metadata = normalize_optical_solid_face_metadata(advanced.get("OpticalSolidFaces"))
            faces = metadata.get("faces") or []
            face = next(
                (f for f in faces if "mirror" in str(f.get("function", "") or "").lower()),
                None,
            )
            splits = False
            if face is None:
                face = next(
                    (f for f in faces if "split" in str(f.get("function", "") or "").lower()),
                    None,
                )
                splits = face is not None
            center = promoted_mirror_world_center(specs, index)
            if face is None or center is None:
                continue
            rotation = _spec_face_rotation(spec)
            normal = rotation @ np.asarray(
                face.get("normal", (0.0, 0.0, 1.0)), dtype=float
            ).reshape(3)
            norm = float(np.linalg.norm(normal))
            if norm <= 1e-12:
                continue
            normal = normal / norm
            face_point = np.asarray(center, dtype=float).reshape(3) + rotation @ np.asarray(
                face.get("centroid", (0.0, 0.0, 0.0)), dtype=float
            ).reshape(3)
            denominator = float(np.dot(direction, normal))
            if abs(denominator) <= 1e-9:
                continue
            distance = float(np.dot(face_point - origin, normal) / denominator)
            if not np.isfinite(distance) or distance <= 1e-6:
                continue  # the face lies behind the current leg -- not reachable forward
            hit = origin + direction * distance
            area = float(face.get("area_mm2", 0.0) or 0.0)
            if np.isfinite(area) and area > 1e-9:
                hit_radius = float(np.sqrt(area)) + 2.0
            else:
                hit_radius = 0.75 * max(
                    float(spec.get("thickness", 0.0) or 0.0),
                    float(spec.get("diameter", 0.0) or 0.0),
                ) + 2.0
            if float(np.linalg.norm(hit - face_point)) > hit_radius:
                continue  # the leg misses the face -- a parked mirror, not a fold
            reached.add(index)
            if splits and len(legs) < 8:
                legs.append((hit + direction * 1.0e-6, direction.copy()))
            direction = direction - 2.0 * float(np.dot(direction, normal)) * normal
            norm = float(np.linalg.norm(direction))
            if norm <= 1e-12:
                break
            direction = direction / norm
            origin = hit
    return reached


def offbeam_inert_solid_indices(row_specs: list[dict]) -> list[int]:
    """Row indices classified as off-beam inert promoted solids (display-free)."""
    specs = list(row_specs or [])
    if len(specs) < 2:
        return []
    radius = beam_clear_radius(specs)
    if radius <= 0.0:
        return []
    reached = folded_beam_reached_mirror_fold_indices(specs)
    return [
        index
        for index, spec in enumerate(specs)
        if index not in reached
        and isinstance(spec, dict)
        and is_offbeam_inert_solid_spec(spec, radius)
    ]


def neutralize_offbeam_inert_solids(row_specs: list[dict]) -> list[dict]:
    """Return ``row_specs`` with off-beam promoted solids made inert.

    An off-beam UNCOATED solid is fully neutralised (flat zero-power AIR, no
    coordinate break, zero thickness). An off-beam COATED splitter stays in the
    non-sequential trace (bugs/0066) but is made axially inert -- its thickness is
    zeroed so it no longer pushes the detector (bugs/0074), while its decenter and
    coating are preserved. Either way an off-beam solid contributes nothing to the
    Object/Image/detector chain.

    The input list is never mutated; the original list object is returned
    unchanged when nothing is off-beam (zero overhead for ordinary layouts).
    """
    specs = list(row_specs or [])
    if len(specs) < 2:
        return row_specs
    radius = beam_clear_radius(specs)
    if radius <= 0.0:
        return row_specs
    # bugs/0243: a free-placed FOLD mirror the folded beam reaches is NOT parked --
    # it only looks "off-beam" to the lateral +Z test because it sits on the
    # reflected arm. Keep its full spec (thickness included) so the output-port
    # follower walk seats the downstream Image/detector at the true prescription
    # station and the real trace focuses ON the drawn sensor.
    reached = folded_beam_reached_mirror_fold_indices(specs)
    changed = False
    result: list[dict] = []
    for index, spec in enumerate(specs):
        if index in reached or not isinstance(spec, dict) or not is_offbeam_solid_spec(spec, radius):
            result.append(spec)
            continue
        if solid_has_active_coating(spec):
            result.append(axially_inert_offbeam_solid_spec(spec))
        else:
            result.append(neutralized_offbeam_solid_spec(spec))
        changed = True
    return result if changed else row_specs


# Below this the live row counts as on-axis (nothing to restore) and a built
# surface counts as still carrying its decenter (the build did not neutralise).
_NEUTRALIZED_BODY_DECENTER_EPS_MM = 1e-6


def offbeam_neutralized_body_transform(base_transform, spec, built_desp_x, built_desp_y):
    """Redraw a neutralised off-beam solid's body back at its decentered station.

    ``neutralize_offbeam_inert_solids`` drops a parked uncoated solid's decenter
    so the solid contributes ZERO optical effect (bugs/0065) -- correct for the
    trace, but the 3-D body is then placed by the *neutralised* on-axis build
    transform (``TRANS_2A[index]``), so the display body snaps onto the optical
    axis the moment the solid is promoted / the Face Editor opens (bugs/0067).
    This restores the body's lateral station for DISPLAY ONLY; the optical solve
    is never consulted here and stays untouched.

    Returns a re-decentered copy of ``base_transform`` when -- and only when --
    the build neutralised a decentered promoted solid: the live ``spec`` is a
    promoted optical solid carrying a real decenter, yet the built surface's
    ``DespX``/``DespY`` came back ~0 (the exact neutralisation signature).
    Otherwise returns ``None`` so the caller keeps the ordinary placement -- a
    coated splitter keeps its decenter in the build (``DespX`` != 0) and is left
    alone.

    The restored translation is exact for an untilted solid: the non-neutralised
    and neutralised ``TRANS_2A[index]`` share their rotation block ``R`` and
    differ in translation by precisely ``R @ desp``, so adding
    ``base_transform[:3, :3] @ desp`` reproduces the non-neutralised world
    station.  Restoring a neutralised solid's OWN tilt orientation is out of
    scope (rare; coated splitters are never neutralised in the first place).
    """
    if base_transform is None:
        return None
    if not is_promoted_optical_solid_spec(spec):
        return None
    if solid_lateral_decenter(spec) <= _NEUTRALIZED_BODY_DECENTER_EPS_MM:
        return None
    built_decenter = math.hypot(
        _float_or_zero(built_desp_x), _float_or_zero(built_desp_y)
    )
    if built_decenter > _NEUTRALIZED_BODY_DECENTER_EPS_MM:
        return None
    transform = np.array(base_transform, dtype=float)
    if transform.shape != (4, 4):
        return None
    desp = np.array(
        (
            _float_or_zero(spec.get("desp_x", 0.0)),
            _float_or_zero(spec.get("desp_y", 0.0)),
            _float_or_zero(spec.get("desp_z", 0.0)),
        ),
        dtype=float,
    )
    transform[:3, 3] = transform[:3, 3] + transform[:3, :3] @ desp
    return transform
