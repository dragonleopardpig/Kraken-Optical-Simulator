"""Branch detectors for non-sequential exit branches (beam splitters etc.).

bugs/0088 Phase B1. A first-class DISPLAY entity: one detector per TERMINAL leaf
branch of the traced ray tree -- the user's "two detectors for a beam splitter",
generalized to cascading splitters. These are derived ``SceneTarget3D`` detector
planes computed from the traced rays; they do NOT add KrakenOS trace surfaces
(display-only). They flow into the scene bundle's ``targets`` so that

  (a) they DISPLAY like a detector/Image plane (a ``SurfaceCurve3D`` rectangle),
  (b) Phase A's ``scene_projector.detector_planes_for_hard_stop`` picks them up
      and the reflected/leaf-arm rays HARD-STOP at them.

Cascading: leaves are identified from ``branch_path`` component prefixes (split on
``" -> "``; ``"primary"`` is the empty root), so N chained splitters get a detector
only on each TERMINAL arm, never an intermediate arm that feeds the next splitter.
Absorbing: an Absorber/Mechanical output face stops a branch. If it produces no
exit rays the branch is simply absent. But when the reflect arm travels INTO the
solid and is absorbed at an internal/exit face, those rays ARE present in
``ray_paths`` (last segment = approach to the absorbing face) -> bugs/0108 drops a
leaf whose rays are ALL absorbed so no phantom detector floats beyond the cube.
Only genuine SPLITS
create child ``branch_path``s; a plain fold (mirror/penta) stays ``"primary"`` and
reaches the sequential Image, so sequential/folded scenes get no branch detector.

DEFERRED (next phases):
  * B2 -- right-click "register STEP camera" per detector + per-detector camera
    assignment. The ``assigned_camera_label`` slot is reserved here (left None).
  * B3/C -- per-branch quick-estimation / quick-solve / optimization + spot-RMS
    auto-solve refinement of the focus. ``branch_path`` is carried so a per-branch
    solve can target this branch's rays via the existing
    ``_best_image_filter_for_ray_records`` / ``_branch_detector_spot_samples``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from KrakenOS.UI.scene_geometry import (
    SceneTarget3D,
    SurfaceCurve3D,
    ray_path_terminal_status_from_events,
)

_BRANCH_PATH_SEP = " -> "
_BRANCH_DETECTOR_ROW_BASE = 100000  # synthetic row indices, far above real rows


@dataclass
class BranchDetector:
    """A derived detector plane on one terminal exit branch (display-only)."""

    detector_id: str
    branch_path: str
    center_world: np.ndarray
    normal_world: np.ndarray
    tangent_world: np.ndarray
    half_w: float
    half_h: float
    focus_source: str = ""  # "converging_rays" | "default_distance"
    # B2 (reserved -- a STEP camera registered to this detector). Unused in B1.
    assigned_camera_label: str | None = None
    # bugs/0093: where this arm exits the cube / its last surface (the mean exit-ray
    # origin), for the per-branch "exit face -> detector" distance overlay.
    exit_point_world: Any = None


def _unit(value: Any) -> np.ndarray | None:
    try:
        vec = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if vec.size < 3 or not np.all(np.isfinite(vec)):
        return None
    norm = float(np.linalg.norm(vec))
    if not np.isfinite(norm) or norm <= 1e-12:
        return None
    return vec / norm


def _orthogonal_unit(normal: np.ndarray) -> np.ndarray:
    """A unit vector perpendicular to ``normal`` (stable basis seed)."""
    seed = np.asarray((0.0, 1.0, 0.0), dtype=float)
    if abs(float(np.dot(seed, normal))) > 0.9:
        seed = np.asarray((1.0, 0.0, 0.0), dtype=float)
    t = seed - float(np.dot(seed, normal)) * normal
    u = _unit(t)
    return u if u is not None else np.asarray((1.0, 0.0, 0.0), dtype=float)


def _branch_components(branch_path: str) -> tuple[str, ...]:
    text = str(branch_path or "").strip()
    if not text or text.lower() == "primary":
        return ()
    return tuple(p.strip() for p in text.split(_BRANCH_PATH_SEP) if p.strip())


def _is_proper_prefix(short: tuple, long: tuple) -> bool:
    return len(short) < len(long) and tuple(long[: len(short)]) == tuple(short)


_SCATTER_BRANCH_TOKENS = ("scatter", "diffuse")

# bugs/0183: a single surface hit this many times in one branch path is an internal
# multi-bounce ghost, not a primary arm (see _branch_path_has_internal_bounce). A
# legitimate double-pass (e.g. a Michelson recombine, an autocollimator return) hits
# a surface at most twice, so 3 is the first count that can only be an internal bounce.
_MAX_SAME_SURFACE_HITS = 3


def _branch_path_has_scatter(branch_path: str) -> bool:
    """True once a branch has passed through a diffuse scatter event.

    bugs/0182: a diffuse double-pass (the object scatter in the coaxial-LED fold)
    spawns ONE leaf branch per scattered ray (S3/scatter01..N). Each such leaf still
    earns a branch detector so it acts as a ray hard-stop (detector_planes_for_hard_stop
    bounds the otherwise-escaping scatter rays in 3-D), but the DRAW of its orange
    footprint / dark plane is gated off (in scene_builder and scene_projector) --
    otherwise dozens of crisscrossing rectangles bury the 2-D 'full 3-D' projection.
    Mirrors the optical-axis scatter guard (bugs/0181)."""
    components = _branch_components(branch_path)
    for component in components:
        text = str(component or "").lower()
        if any(token in text for token in _SCATTER_BRANCH_TOKENS):
            return True
    return False


def _branch_component_surface(component: str) -> str:
    """The surface token a branch component HITS (``S1:S1/transmit`` -> ``S1``)."""
    segment = str(component or "").split(":")[-1]
    return segment.split("/")[0].strip()


def _branch_path_has_internal_bounce(branch_path: str) -> bool:
    """True when one surface is hit ``_MAX_SAME_SURFACE_HITS`` times in a branch.

    bugs/0183: a glued beam-splitter cube is a non-sequential solid -- the tracer
    forks transmit/reflect at EVERY face interaction, so a ray can re-bounce on the
    SAME surface (the cube) over and over (``S1/transmit -> S1/reflect -> S1/reflect
    -> ...``, depth 8 on the MV-150 fold). Each leaf earns a branch detector, so a
    dense LED bundle explodes into ~128 deterministic-but-faint ghost detectors, all
    clustered at the cube and drawn as overlapping orange parallelograms (the plaid
    that survived the bugs/0182 scatter gate, since these carry no scatter token).
    Like scatter, an internal-bounce ghost has no meaningful focus, so its detector
    DRAW is gated off; the target is kept as a ray hard-stop (double-duty)."""
    components = _branch_components(branch_path)
    if not components:
        return False
    counts: dict[str, int] = {}
    for component in components:
        token = _branch_component_surface(component)
        if not token:
            continue
        counts[token] = counts.get(token, 0) + 1
        if counts[token] >= _MAX_SAME_SURFACE_HITS:
            return True
    return False


def _branch_path_draw_suppressed(branch_path: str) -> bool:
    """A branch detector should NOT draw its 2-D footprint/plane when the branch is
    non-deterministic (diffuse scatter, bugs/0182) or a faint internal multi-bounce
    ghost (bugs/0183). In BOTH cases the detector TARGET is still kept as an
    is_detector ray hard-stop, so only the DRAW is gated -- the rays stay bounded in
    3-D (no starburst) while the 2-D 'full 3-D' projection stays clean (no plaid)."""
    return _branch_path_has_scatter(branch_path) or _branch_path_has_internal_bounce(branch_path)


def _leaf_reaches_existing_detector(group: list) -> bool:
    """True when this branch already terminates at the sequential Image/detector."""
    for path in group:
        if bool(getattr(path, "reaches_image", False)):
            return True
        try:
            if ray_path_terminal_status_from_events(path) == "hit_detector":
                return True
        except Exception:
            pass
    return False


def _ray_is_absorbed(path) -> bool:
    try:
        if ray_path_terminal_status_from_events(path) == "absorbed":
            return True
    except Exception:
        pass
    reason = str(getattr(path, "termination_reason", "") or "").strip().lower()
    return "absorb" in reason


def _leaf_fully_absorbed(group: list) -> bool:
    """A leaf whose every ray dies by absorption has no exit beam, so no detector.

    bugs/0108: an Absorber/Mechanical output face stops the branch INSIDE the
    solid (the reflect arm travels to that face and is absorbed there), yet the
    ray is still PRESENT in ``ray_paths`` with a last segment -- ``_exit_rays_for_group``
    would extrapolate that approach segment to a PHANTOM focus and draw a detector
    floating beyond the cube. Drop such a leaf entirely. Conservative: any ray that
    still converges/escapes (status != absorbed) keeps the detector."""
    saw_ray = False
    for path in group:
        saw_ray = True
        if not _ray_is_absorbed(path):
            return False
    return saw_ray


def _reached_image_target(existing_targets: list | None):
    """bugs/0093: the sequential Image/detector target a transmit leaf terminates on
    (the furthest non-branch-detector Image plane). Used to pin a reached-image branch
    detector ONTO that image so they coincide. None when no such target exists."""
    best = None
    for target in (existing_targets or []):
        if not bool(getattr(target, "is_detector", False)):
            continue
        if str(getattr(target, "surface", "") or "") != "Image":
            continue
        meta = getattr(target, "metadata", {}) or {}
        if str(meta.get("target_source", "") or "") == "branch_detector":
            continue
        try:
            z = float(np.asarray(getattr(target, "center_world", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)[-1])
        except Exception:
            continue
        if best is None or z > best[0]:
            best = (z, target)
    return best[1] if best is not None else None


def _exit_rays_for_group(group: list) -> tuple[np.ndarray, np.ndarray]:
    """Return (origins, unit_directions) for the EXIT segment of each ray.

    The exit segment is the last polyline segment (last interaction -> terminal
    point), i.e. the ray after its final surface interaction along this branch.
    """
    origins: list[np.ndarray] = []
    dirs: list[np.ndarray] = []
    for path in group:
        pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
            continue
        # bugs/0099: a ray absorbed at its terminal surface can record the SAME world
        # point many times (a FOLDED detector re-intersected itself up to the ns-limit on
        # the reflect arm -- 199 identical trailing points), leaving the last raw segment
        # zero-length so that arm got NO detector. Drop consecutive duplicates and use the
        # last REAL segment (the ray's approach to its focus).
        xyz = pts[:, :3]
        xyz = xyz[np.concatenate(([True], np.linalg.norm(np.diff(xyz, axis=0), axis=1) > 1.0e-9))]
        if xyz.shape[0] < 2:
            continue
        origin = xyz[-2]
        direction = _unit(xyz[-1] - xyz[-2])
        if direction is None or not np.all(np.isfinite(origin)):
            continue
        origins.append(np.asarray(origin, dtype=float))
        dirs.append(direction)
    if not origins:
        return np.empty((0, 3)), np.empty((0, 3))
    return np.asarray(origins, dtype=float), np.asarray(dirs, dtype=float)


def _closest_approach_point(origins: np.ndarray, directions: np.ndarray) -> tuple[np.ndarray, bool]:
    """Least-squares point closest to all rays (the converging waist/focus).

    Solves ``min_p sum_i ||(I - d_i d_i^T)(p - o_i)||^2``. Returns
    ``(point, ok)``; ``ok`` is False when the ray bundle is collinear/parallel
    (no convergence) so the caller falls back to a default distance.
    """
    if origins.shape[0] < 2:
        return origins.mean(axis=0) if origins.size else np.zeros(3), False
    M = np.zeros((3, 3), dtype=float)
    b = np.zeros(3, dtype=float)
    eye = np.eye(3)
    for o, d in zip(origins, directions):
        proj = eye - np.outer(d, d)
        M += proj
        b += proj @ o
    try:
        if not np.all(np.isfinite(M)) or float(np.linalg.cond(M)) > 1.0e8:
            return origins.mean(axis=0), False
        point = np.linalg.solve(M, b)
    except Exception:
        return origins.mean(axis=0), False
    if not np.all(np.isfinite(point)):
        return origins.mean(axis=0), False
    return point, True


def _existing_detector_half_dims(existing_targets: list | None) -> tuple[float, float] | None:
    for target in list(existing_targets or []):
        if not bool(getattr(target, "is_detector", False)):
            continue
        w = float(getattr(target, "active_width_mm", 0.0) or 0.0)
        h = float(getattr(target, "active_height_mm", 0.0) or 0.0)
        if w > 1e-6 and h > 1e-6:
            return w / 2.0, h / 2.0
        diameter = float(getattr(target, "diameter", 0.0) or 0.0)
        if diameter > 1e-6:
            return diameter / 2.0, diameter / 2.0
    return None


def derive_branch_detectors(
    ray_paths: list,
    existing_targets: list | None = None,
    *,
    scene_radius: float = 50.0,
    default_distance: float | None = None,
    branch_camera_sensors: dict | None = None,
) -> list[BranchDetector]:
    """One :class:`BranchDetector` per terminal leaf branch.

    When a split occurred (>1 terminal leaf) EVERY leaf gets a detector at its own
    focus -- including the straight-through transmit leaf that reaches the
    sequential Image (bugs/0090: a beam splitter must show a detector on BOTH
    arms). A plain sequential scene (single leaf reaching the Image) keeps that
    Image and derives nothing. Intermediate branches (proper prefixes of another
    branch -- they feed a downstream splitter) never get one. See module docs for
    the cascading + absorbing semantics.
    """
    paths = [p for p in list(ray_paths or []) if p is not None]
    if not paths:
        return []
    groups: dict[str, list] = {}
    for path in paths:
        bp = str(getattr(path, "branch_path", "") or getattr(path, "branch_label", "") or "")
        groups.setdefault(bp, []).append(path)
    comps = {bp: _branch_components(bp) for bp in groups}
    comp_values = list(comps.values())
    leaves = [
        bp
        for bp, comp in comps.items()
        if not any(_is_proper_prefix(comp, other) for other in comp_values)
    ]
    # bugs/0108: a leaf whose rays are ALL absorbed (an Absorber/Mechanical output
    # face on the cube) is a dead-end, not a real arm -- drop it so no phantom
    # detector/Image plane lingers in that branch. Absorbing one arm of a splitter
    # then collapses the scene to its surviving arm(s) (re: multi_leaf below).
    leaves = [bp for bp in leaves if not _leaf_fully_absorbed(groups[bp])]
    default_half = _existing_detector_half_dims(existing_targets)
    try:
        radius = float(scene_radius)
    except Exception:
        radius = 50.0
    if not np.isfinite(radius) or radius <= 0.0:
        radius = 50.0
    fallback_distance = float(default_distance) if (default_distance and float(default_distance) > 0.0) else max(radius, 50.0)

    # When a SPLIT occurred (>1 terminal leaf), EVERY leaf -- including the
    # straight-through transmit leaf that reaches the sequential Image -- gets a
    # detector at its own focus, so a beam splitter shows a detector on BOTH arms
    # (bugs/0090; the user's "the transmitted one is missing"). A plain sequential
    # scene has a single leaf reaching the Image -> keep that Image, derive nothing.
    multi_leaf = len(leaves) > 1
    detectors: list[BranchDetector] = []
    for index, bp in enumerate(sorted(leaves)):
        group = groups[bp]
        reaches_image = _leaf_reaches_existing_detector(group)
        if not multi_leaf and reaches_image:
            continue
        origins, directions = _exit_rays_for_group(group)
        if origins.shape[0] == 0:
            continue
        mean_dir = _unit(directions.mean(axis=0))
        if mean_dir is None:
            continue
        mean_origin = origins.mean(axis=0)
        focus, converged = _closest_approach_point(origins, directions)
        forward = float(np.dot(focus - mean_origin, mean_dir)) if converged else -1.0
        if (not converged) or forward <= 1.0e-6 or not np.all(np.isfinite(focus)):
            focus = mean_origin + mean_dir * fallback_distance
            focus_source = "default_distance"
        else:
            focus_source = "converging_rays"
        # bugs/0093: a transmit leaf that REACHES the sequential Image focuses AT that
        # image (the user's designed focus). When the splitter sits BEFORE the lens the
        # branch path's exit-ray convergence is unreliable -- it lands far FORWARD of
        # the lens focus (recording flag_20260618_221055: transmit detector pulled
        # ~270 mm forward of the image, physically backwards). Pin the detector to the
        # reached Image so the detector and image COINCIDE ("the original is correct,
        # the image plane lands on the detector").
        reached = _reached_image_target(existing_targets) if reaches_image else None
        if reached is not None:
            ri = np.asarray(getattr(reached, "center_world", focus), dtype=float).reshape(-1)
            # bugs/0097: in a multi-arm split EVERY leaf that lands on a detector trips
            # reaches_image, but _reached_image_target returns the single furthest global
            # Image. Pinning a reflect leaf (beam +Y) onto a +Z image collapsed BOTH
            # branch detectors onto that image (the two perpendicular squares at the
            # transmit end of beam_splitter_two_arm_doublets). Only pin when the image
            # lies on THIS leaf's beam -- ahead of the exit and aligned with the mean
            # exit direction -- so the reflect leaf keeps its own +Y convergence focus.
            on_this_leaf = False
            if ri.shape == (3,) and np.all(np.isfinite(ri)):
                to_image = ri - mean_origin
                dist = float(np.linalg.norm(to_image))
                on_this_leaf = dist > 1.0e-6 and float(np.dot(to_image, mean_dir)) / dist > 0.7
            if on_this_leaf:
                # bugs/0099: pin to the reached Image only when the exit rays don't already
                # converge BEFORE it. The dual-lens reflect arm's rays focus ~36mm SHORT of
                # the nominal image (the REAL per-branch focus) -- pinning to the image put
                # the detector BEYOND the focus, so "the rays don't reach the detector" (a
                # tight spot stopping short of the plane). 0093's cube-before-lens case is the
                # opposite: the convergence lands far FORWARD of the image (unreliable), so
                # there we DO pin. Trust a reliable convergence that sits >1mm behind the image.
                behind = float(np.dot(np.asarray(focus, dtype=float) - ri, mean_dir)) if converged else 0.0
                to_image = float(np.dot(ri - mean_origin, mean_dir))
                # bugs/0100: trust a forward convergence ONLY when it sits CLOSE to the reached image
                # (a real per-branch focus -- the dual-lens reflect arm converges ~36mm, ~30% short). A
                # cube-before-lens transmit leaf's display bundle converges WILDLY forward (live flag
                # 20260621_181338: focus_z 361.9 vs image 612.8 = 251mm, ~85% short, source=converging_rays)
                # -- an artifact, not a focus -- so pin to the designed Image rather than parking the
                # transmit detector ~250mm forward of the real focus.
                reliable_forward = (
                    converged
                    and focus_source == "converging_rays"
                    and to_image > 1.0e-6
                    and -0.5 * to_image < behind < -1.0
                )
                if not reliable_forward:
                    focus = ri
                    focus_source = "reached_image"
        # Size to the beam FOOTPRINT entering this branch (catches the whole beam
        # and stays visible), NOT the focus spot (~0, which collapsed the plane to
        # a sub-mm sliver). A real, sensibly-sized existing detector wins;
        # otherwise a scene-scaled minimum keeps the plane visible (bugs/0090).
        footprint = 0.0
        for o in origins:
            rel = np.asarray(o, dtype=float) - mean_origin
            trans = rel - float(np.dot(rel, mean_dir)) * mean_dir
            footprint = max(footprint, float(np.linalg.norm(trans)))
        min_half = max(0.04 * radius, 5.0)
        if default_half is not None and min(default_half) >= min_half:
            half_w, half_h = default_half
        else:
            half_w = half_h = max(footprint, min_half)
        # B2 (bugs/0093, vendor-step-import-semantics): a vendor camera STEP
        # registered to this branch determines the SENSOR SIZE -- blend the detector
        # plane to the camera's active sensor (w x h) so the per-branch FOV / sensor
        # quick-estimation reads the real sensor instead of the beam footprint.
        assigned_camera_label = None
        cam = (branch_camera_sensors or {}).get(bp)
        if cam is not None:
            assigned_camera_label = cam[0] or None
            try:
                sensor_w, sensor_h = float(cam[1][0]), float(cam[1][1])
                if np.isfinite(sensor_w) and np.isfinite(sensor_h) and sensor_w > 1.0e-6 and sensor_h > 1.0e-6:
                    half_w, half_h = sensor_w / 2.0, sensor_h / 2.0
            except Exception:
                pass
        tangent = _orthogonal_unit(mean_dir)
        detectors.append(
            BranchDetector(
                detector_id=f"branch_detector:{index}:{bp[:48]}",
                branch_path=bp,
                center_world=np.asarray(focus, dtype=float),
                normal_world=np.asarray(mean_dir, dtype=float),
                tangent_world=np.asarray(tangent, dtype=float),
                half_w=float(half_w),
                half_h=float(half_h),
                focus_source=focus_source,
                assigned_camera_label=assigned_camera_label,
                exit_point_world=np.asarray(mean_origin, dtype=float),
            )
        )
    return detectors


def _short_branch_label(branch_path: str) -> str:
    comps = _branch_components(branch_path)
    if not comps:
        return "primary"
    last = comps[-1]
    # component looks like "S4:Name/label" -> keep "Name/label"
    return last.split(":", 1)[-1] if ":" in last else last


def branch_detector_scene_target(detector: BranchDetector, row_index: int | None = None) -> SceneTarget3D:
    """Wrap a :class:`BranchDetector` as an ``is_detector`` scene target."""
    return SceneTarget3D(
        target_id=detector.detector_id,
        name=f"Branch detector ({_short_branch_label(detector.branch_path)})",
        role="detector",
        row_index=int(row_index) if row_index is not None else _BRANCH_DETECTOR_ROW_BASE,
        trace_surface=None,
        surface="Image",
        material="",
        center_world=np.asarray(detector.center_world, dtype=float),
        normal_world=np.asarray(detector.normal_world, dtype=float),
        tangent_world=np.asarray(detector.tangent_world, dtype=float),
        diameter=2.0 * max(detector.half_w, detector.half_h),
        active_width_mm=2.0 * detector.half_w,
        active_height_mm=2.0 * detector.half_h,
        is_detector=True,
        metadata={
            "target_source": "branch_detector",
            "branch_path": detector.branch_path,
            "assigned_camera_label": detector.assigned_camera_label,
            "focus_source": detector.focus_source,
            "exit_point_world": (
                tuple(float(v) for v in np.asarray(detector.exit_point_world, dtype=float).reshape(-1)[:3])
                if detector.exit_point_world is not None
                else None
            ),
        },
    )


def branch_detector_plane_curve(detector: BranchDetector) -> SurfaceCurve3D:
    """A world-space rectangle outline so the branch detector draws as a plane."""
    center = np.asarray(detector.center_world, dtype=float)[:3]
    normal = _unit(detector.normal_world)
    tangent = _unit(detector.tangent_world)
    if normal is None or tangent is None:
        normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
        tangent = np.asarray((0.0, 1.0, 0.0), dtype=float)
    bitangent = _unit(np.cross(normal, tangent))
    if bitangent is None:
        bitangent = np.asarray((1.0, 0.0, 0.0), dtype=float)
    hw, hh = float(detector.half_w), float(detector.half_h)
    corners = [
        center + tangent * hw + bitangent * hh,
        center - tangent * hw + bitangent * hh,
        center - tangent * hw - bitangent * hh,
        center + tangent * hw - bitangent * hh,
    ]
    points = np.asarray(corners + [corners[0]], dtype=float)
    return SurfaceCurve3D(row_index=-1, kind="image", points_world=points, coordinate_space="world")
