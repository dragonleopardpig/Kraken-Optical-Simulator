"""Display-free regression guard for bugs/0182.

The folded MV-150 coaxial area-LED scene is a diffuse double-pass: the object
scatter forks one leaf branch per scattered ray (``S3/scatter01..N``). Each leaf
earns its own synthesized branch detector.

bugs/0182 has two faces, and the corrective fix has to satisfy BOTH at once:

* 2-D plaid -- if every scatter detector DRAWS its orange footprint + dark plane,
  the 2-D 'full 3-D' projection is buried under dozens of crisscrossing
  rectangles. So the DRAW of a scatter-branch detector is gated off (in
  scene_builder for the plane curve, in scene_projector for the footprint).
* 3-D starburst -- those same detectors are also ray HARD-STOPS
  (``detector_planes_for_hard_stop`` -> ``bounded_ray_points_for_scene_display``).
  Dropping them entirely (the first 0182 attempt) let the non-deterministic
  scatter rays fly to the scene radius -> a starburst that blew the visible
  bounds out to x[-235,592] y[-342,286]. So the detectors are KEPT (just not
  drawn); the rays stay bounded.

Checks:

* Unit -- ``derive_branch_detectors`` + ``_branch_path_has_scatter``: a scatter
  fork still yields a detector per scatter leaf (the hard-stops), each correctly
  classified as scatter (so it won't draw); the clean straight-through leak is a
  detector that is NOT scatter-classified (so it still draws). A clean 2-arm beam
  splitter yields both arm detectors, neither scatter-classified.
* Real scene -- the folded coaxial-LED bundle: (a) the bounded 3-D ray extent is
  TIGHT (hard-stops still bound the scatter rays); (b) the 2-D projection draws
  only a couple of detector curves (no plaid); (c) the branch-detector targets
  are still numerous (the hard-stops survived).

Run headless: ``python -m KrakenOS.UI.validate_open3d_branch_detector_scatter_clutter``
"""
from __future__ import annotations

import os

import numpy as np

from KrakenOS.UI.scene_geometry import RayPath3D, ray_path_terminal_status_from_events
from KrakenOS.UI.scene_projector import (
    SceneProjector2D,
    _target_is_scatter_branch_detector,
    bounded_ray_points_for_scene_display,
    detector_planes_for_hard_stop,
    scene_display_center_radius,
)
from KrakenOS.UI.services.branch_detectors import (
    _branch_path_has_scatter,
    derive_branch_detectors,
)

os.environ.setdefault("KRAKENOS_HEADLESS", "1")

# A scatter-bounded folded scene stays well inside this half-extent in display
# X/Y; the starburst regression blew it past 200 (and Y past 460).
_BOUNDED_XY_LIMIT = 150.0


def _ray(branch_path: str, origin, direction, *, ray_index: int) -> RayPath3D:
    o = np.asarray(origin, dtype=float)
    d = np.asarray(direction, dtype=float)
    return RayPath3D(
        ray_index=int(ray_index),
        points_world=np.asarray((o, o + 40.0 * d), dtype=float),
        branch_path=branch_path,
        branch_label=branch_path,
    )


# --- Part 1: unit -- derive_branch_detectors + the scatter predicate ----------

def _scatter_fork_paths() -> list[RayPath3D]:
    """A diffuse fork: the reflect arm hits the object then scatters three ways,
    plus a clean straight-through transmit leak."""
    paths: list[RayPath3D] = []
    # intermediate reflect arm (a proper prefix of the scatter leaves -> not a leaf)
    paths.append(_ray("S1:S1/reflect", [0.0, 0.0, 0.0], [0.0, -1.0, 0.0], ray_index=0))
    # three scatter leaves, each a distinct random direction
    paths.append(_ray("S1:S1/reflect -> S3:S3/scatter01", [0.0, -30.0, 0.0], [0.3, 1.0, 0.2], ray_index=1))
    paths.append(_ray("S1:S1/reflect -> S3:S3/scatter02", [0.0, -30.0, 0.0], [-0.4, 1.0, -0.1], ray_index=2))
    paths.append(_ray("S1:S1/reflect -> S3:S3/scatter03", [0.0, -30.0, 0.0], [0.1, 1.0, 0.5], ray_index=3))
    # clean straight-through leak (deterministic, no scatter)
    paths.append(_ray("S1:S1/transmit", [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=4))
    paths.append(_ray("S1:S1/transmit", [2.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=5))
    return paths


def _clean_beam_splitter_paths() -> list[RayPath3D]:
    """A genuine beam splitter: reflect (+Y) and transmit (+Z) arms, no scatter."""
    paths: list[RayPath3D] = []
    paths.append(_ray("S1:S1/reflect", [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], ray_index=0))
    paths.append(_ray("S1:S1/reflect", [0.0, 2.0, 0.0], [0.0, 1.0, 0.0], ray_index=1))
    paths.append(_ray("S1:S1/transmit", [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=2))
    paths.append(_ray("S1:S1/transmit", [2.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=3))
    return paths


def _check_unit(notes: list[str]) -> bool:
    ok = True

    fork = derive_branch_detectors(_scatter_fork_paths(), existing_targets=[], scene_radius=50.0)
    scatter_dets = [d for d in fork if _branch_path_has_scatter(d.branch_path)]
    clean_dets = [d for d in fork if not _branch_path_has_scatter(d.branch_path)]
    # The scatter leaves must KEEP their detectors (they are the ray hard-stops),
    # and each must be classified as scatter so the draw is gated off.
    if len(scatter_dets) < 1:
        notes.append("scatter fork lost its scatter detectors -> rays would un-bound in 3-D")
        ok = False
    else:
        notes.append(f"scatter fork: {len(scatter_dets)} scatter hard-stop detector(s) kept (drawn=NO)")
    if len(clean_dets) < 1:
        notes.append("scatter fork lost the clean straight-through leak detector")
        ok = False
    else:
        notes.append(f"scatter fork: {len(clean_dets)} clean detector(s) kept (drawn=YES)")

    clean = derive_branch_detectors(_clean_beam_splitter_paths(), existing_targets=[], scene_radius=50.0)
    clean_scatter = [d for d in clean if _branch_path_has_scatter(d.branch_path)]
    if len(clean) != 2:
        notes.append(f"clean beam splitter expected 2 arm detectors, got {len(clean)}")
        ok = False
    elif clean_scatter:
        notes.append(f"clean beam splitter falsely scatter-classified {len(clean_scatter)} arm(s)")
        ok = False
    else:
        notes.append("clean beam splitter keeps both arm detectors, neither scatter-classified (draws)")
    return ok


# --- Part 2: real folded coaxial-LED scene ------------------------------------

def _check_real_scene(notes: list[str]) -> bool:
    try:
        from KrakenOS.UI.validate_open3d_optical_axis_scatter_clutter import _build_folded_bundle
    except Exception as exc:  # pragma: no cover
        notes.append(f"could not import folded-scene harness: {exc!r}")
        return False
    try:
        bundle = _build_folded_bundle(15)
    except Exception as exc:  # pragma: no cover
        notes.append(f"real folded-scene build raised: {exc!r}")
        return False

    ok = True

    # (c) the hard-stop detectors survive (they are NOT dropped)
    branch_targets = [
        t for t in (getattr(bundle, "targets", []) or [])
        if str((getattr(t, "metadata", {}) or {}).get("target_source", "")) == "branch_detector"
    ]
    if len(branch_targets) < 10:
        notes.append(f"only {len(branch_targets)} branch-detector hard-stops -> scatter rays may un-bound")
        ok = False
    else:
        scatter_n = sum(1 for t in branch_targets if _target_is_scatter_branch_detector(t))
        notes.append(
            f"real scene: {len(branch_targets)} branch-detector hard-stops kept "
            f"({scatter_n} scatter, draw-gated)"
        )

    # (a) the bounded 3-D ray extent is tight (the hard-stops still bound scatter)
    center, radius = scene_display_center_radius(bundle)
    planes = detector_planes_for_hard_stop(bundle, radius)
    bounded: list[np.ndarray] = []
    for path in list(getattr(bundle, "ray_paths", []) or []):
        pts = np.asarray(getattr(path, "points_world", []), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        try:
            status = ray_path_terminal_status_from_events(path)
        except Exception:
            status = ""
        bpts, _capped = bounded_ray_points_for_scene_display(
            pts, center, radius, terminal_status=status, detector_planes=planes
        )
        bpts = np.asarray(bpts, dtype=float)
        if bpts.ndim == 2 and bpts.shape[0] >= 1 and bpts.shape[1] >= 3:
            bounded.append(bpts[:, :3])
    if not bounded:
        notes.append("no bounded ray points produced -> cannot verify 3-D extent")
        ok = False
    else:
        allpts = np.vstack(bounded)
        allpts = allpts[np.all(np.isfinite(allpts), axis=1)]
        max_xy = float(np.max(np.abs(allpts[:, :2]))) if allpts.size else 0.0
        if max_xy > _BOUNDED_XY_LIMIT:
            notes.append(
                f"bounded 3-D ray extent max|x,y|={max_xy:.0f} > {_BOUNDED_XY_LIMIT:.0f}"
                " -> scatter starburst un-bounded"
            )
            ok = False
        else:
            notes.append(f"bounded 3-D ray extent tight: max|x,y|={max_xy:.0f} (hard-stops hold)")

    # (b) the 2-D projection draws only a couple of detector curves (no plaid)
    proj = SceneProjector2D("Vertical").project_bundle(bundle)
    footprints = sum(1 for c in proj.curves if getattr(c, "kind", "") == "detector_active_footprint")
    branch_planes = sum(
        1 for c in proj.curves
        if getattr(c, "kind", "") == "image" and int(getattr(c, "row_index", 0)) == -1
    )
    if footprints > 2:
        notes.append(f"2-D draws {footprints} detector footprints (>2) -> plaid clutter returned")
        ok = False
    elif branch_planes > 2:
        notes.append(f"2-D draws {branch_planes} branch-detector planes (>2) -> plaid clutter returned")
        ok = False
    else:
        notes.append(
            f"2-D draws {footprints} detector footprint(s) + {branch_planes} branch plane(s) (no plaid)"
        )
    return ok


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    ok = _check_unit(notes) and ok
    ok = _check_real_scene(notes) and ok
    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(("  ok  " if ok else "  --  ") + note)
    label = "diffuse double-pass: scatter detectors stay hard-stops but draw no 2-D clutter"
    print(("[PASS] " if ok else "[FAIL] ") + label + " (bugs/0182)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
