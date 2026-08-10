"""Display-free regression guard for bugs/0183.

The folded MV-150 coaxial beam-splitter is a glued non-sequential CUBE: the tracer
forks transmit/reflect at every face, so a ray can re-bounce on the SAME surface
(the cube, ``S1``) up to depth 8 -- ``S1/transmit -> S1/reflect -> S1/reflect -> ...``.
``derive_branch_detectors`` makes one detector per terminal leaf, so at the live LED
ray count a dense bundle explodes into ~128 deterministic-but-faint ghost detectors,
all clustered at the cube. They carry NO scatter token, so the bugs/0182 scatter gate
never touched them -- they drew ~128 overlapping orange ``detector_active_footprint``
quads (two big tilted parallelograms + crosshairs) over the real geometry.

Like a scatter leaf, an internal-bounce ghost has no meaningful focus. The fix gates
its 2-D DRAW while KEEPING the detector target (it is still a ray hard-stop via
``detector_planes_for_hard_stop``, so the rays stay bounded in 3-D -- the lesson of
the 0182 starburst). Same double-duty story, a different (non-scatter) branch class.

Checks:

* Unit -- ``derive_branch_detectors`` + ``_branch_path_draw_suppressed``: an 8-deep
  same-surface fork keeps a detector per leaf (the hard-stops) but EVERY one is
  draw-suppressed (internal bounce); a clean 2-arm beam splitter keeps both arms,
  NEITHER suppressed (they draw); a genuine 3-surface fold (distinct surfaces) is
  NOT suppressed (distinct surfaces never trip the same-surface count).
* Real scene -- the folded coaxial-LED bundle at the LIVE LED ray count: (a) the
  branch-detector hard-stop targets are still numerous (the hard-stops survived); (b)
  the 2-D projection draws ZERO detector footprints (no parallelograms); (c) the
  bounded 3-D ray extent stays tight (the hard-stops still bound the rays).

Run headless: ``python -m KrakenOS.UI.validate_open3d_branch_detector_internal_bounce_clutter``
"""
from __future__ import annotations

import os

import numpy as np

from KrakenOS.UI.scene_geometry import RayPath3D, ray_path_terminal_status_from_events
from KrakenOS.UI.scene_projector import (
    SceneProjector2D,
    _target_branch_detector_draw_suppressed,
    bounded_ray_points_for_scene_display,
    detector_planes_for_hard_stop,
    scene_display_center_radius,
)
from KrakenOS.UI.services.branch_detectors import (
    _branch_path_draw_suppressed,
    _branch_path_has_internal_bounce,
    derive_branch_detectors,
)

os.environ.setdefault("KRAKENOS_HEADLESS", "1")

# The live LED bundle (LED_RAY_COUNT = 60) is what blooms the internal-bounce
# explosion; the 0182 guard used 15 rays where it never forms, which is why it
# missed this. Drive the guard at the live density.
_LIVE_RAYS = 60
# A scatter/bounce-bounded folded scene stays well inside this half-extent.
# Re-derived for bugs/0605: a PRIMARY ray that misses a detector now legally flies
# past it (the bugs/0553 scene-envelope tail, <= 600 mm), so the tight bound applies
# to the DRAW-SUPPRESSED ghost-branch class the clutter contract is about, and every
# path obeys the absolute no-endless-lines cap.
_BOUNDED_XY_LIMIT = 150.0
_ABSOLUTE_XY_CAP = 700.0


def _ray(branch_path: str, origin, direction, *, ray_index: int) -> RayPath3D:
    o = np.asarray(origin, dtype=float)
    d = np.asarray(direction, dtype=float)
    return RayPath3D(
        ray_index=int(ray_index),
        points_world=np.asarray((o, o + 40.0 * d), dtype=float),
        branch_path=branch_path,
        branch_label=branch_path,
    )


# --- Part 1: unit -- derive_branch_detectors + the draw-suppression predicate -----

def _internal_bounce_fork_paths() -> list[RayPath3D]:
    """A beam-splitter cube re-bouncing on its own surface S1 (depth 8), plus the
    clean straight-through leak (S1 hit once). The deep paths start with ``reflect``
    so the ``transmit`` leak is its own terminal leaf (not a shared prefix)."""
    deep = "S1:S1/reflect" + " -> S1:S1/reflect" * 7  # S1 hit 8 times
    deep2 = "S1:S1/reflect -> S1:S1/transmit" + " -> S1:S1/reflect" * 6  # S1 hit 8 times
    return [
        _ray(deep, [0.0, 0.0, 0.0], [0.2, 1.0, 0.1], ray_index=0),
        _ray(deep2, [0.0, 0.0, 0.0], [-0.3, 1.0, 0.2], ray_index=1),
        _ray("S1:S1/transmit", [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=2),
        _ray("S1:S1/transmit", [2.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=3),
    ]


def _clean_beam_splitter_paths() -> list[RayPath3D]:
    """A genuine beam splitter: reflect (+Y) and transmit (+Z) arms, S1 hit once each."""
    return [
        _ray("S1:S1/reflect", [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], ray_index=0),
        _ray("S1:S1/reflect", [0.0, 2.0, 0.0], [0.0, 1.0, 0.0], ray_index=1),
        _ray("S1:S1/transmit", [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=2),
        _ray("S1:S1/transmit", [2.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=3),
    ]


def _three_surface_fold_paths() -> list[RayPath3D]:
    """A genuine multi-element fold: distinct surfaces S1, S2, S3 -- never an
    internal bounce, so its terminal detectors must still DRAW."""
    return [
        _ray("S1:S1/reflect -> S2:S2/reflect -> S3:S3/transmit", [0.0, 0.0, 0.0], [0.1, 0.2, 1.0], ray_index=0),
        _ray("S1:S1/reflect -> S2:S2/reflect -> S3:S3/transmit", [1.0, 0.0, 0.0], [0.1, 0.2, 1.0], ray_index=1),
        _ray("S1:S1/reflect -> S2:S2/reflect -> S3:S3/reflect", [0.0, 0.0, 0.0], [0.1, -0.2, 1.0], ray_index=2),
        _ray("S1:S1/reflect -> S2:S2/reflect -> S3:S3/reflect", [1.0, 0.0, 0.0], [0.1, -0.2, 1.0], ray_index=3),
    ]


def _check_unit(notes: list[str]) -> bool:
    ok = True

    fork = derive_branch_detectors(_internal_bounce_fork_paths(), existing_targets=[], scene_radius=50.0)
    bounced = [d for d in fork if _branch_path_has_internal_bounce(d.branch_path)]
    drawn = [d for d in fork if not _branch_path_draw_suppressed(d.branch_path)]
    if len(bounced) < 2:
        notes.append(f"internal-bounce fork: expected >=2 deep ghosts, classified {len(bounced)}")
        ok = False
    else:
        notes.append(f"internal-bounce fork: {len(bounced)} deep ghost detector(s) kept as hard-stops (drawn=NO)")
    # the deep ghosts must all be draw-suppressed; only the clean leak draws
    suppressed = [d for d in fork if _branch_path_draw_suppressed(d.branch_path)]
    if not all(_branch_path_draw_suppressed(d.branch_path) for d in bounced):
        notes.append("a deep internal-bounce ghost was NOT draw-suppressed -> plaid returns")
        ok = False
    if not any(d.branch_path == "S1:S1/transmit" for d in drawn):
        notes.append("internal-bounce fork lost the clean straight-through leak detector (draw)")
        ok = False
    else:
        notes.append(f"internal-bounce fork: {len(drawn)} clean detector(s) still draw; {len(suppressed)} suppressed")

    clean = derive_branch_detectors(_clean_beam_splitter_paths(), existing_targets=[], scene_radius=50.0)
    clean_suppressed = [d for d in clean if _branch_path_draw_suppressed(d.branch_path)]
    if len(clean) != 2:
        notes.append(f"clean beam splitter expected 2 arm detectors, got {len(clean)}")
        ok = False
    elif clean_suppressed:
        notes.append(f"clean beam splitter falsely suppressed {len(clean_suppressed)} arm(s)")
        ok = False
    else:
        notes.append("clean beam splitter keeps both arm detectors, neither suppressed (draws)")

    fold = derive_branch_detectors(_three_surface_fold_paths(), existing_targets=[], scene_radius=50.0)
    fold_suppressed = [d for d in fold if _branch_path_draw_suppressed(d.branch_path)]
    if fold_suppressed:
        notes.append(f"multi-element fold falsely suppressed {len(fold_suppressed)} distinct-surface detector(s)")
        ok = False
    else:
        notes.append(f"multi-element fold (distinct surfaces): all {len(fold)} detector(s) still draw")
    return ok


# --- Part 2: real folded coaxial-LED scene at the LIVE ray count ------------------

def _check_real_scene(notes: list[str]) -> bool:
    try:
        from KrakenOS.UI.validate_open3d_optical_axis_scatter_clutter import _build_folded_bundle
    except Exception as exc:  # pragma: no cover
        notes.append(f"could not import folded-scene harness: {exc!r}")
        return False
    try:
        bundle = _build_folded_bundle(_LIVE_RAYS)
    except Exception as exc:  # pragma: no cover
        notes.append(f"real folded-scene build raised: {exc!r}")
        return False

    ok = True

    # (a) the hard-stop detectors survive (they are NOT dropped)
    branch_targets = [
        t for t in (getattr(bundle, "targets", []) or [])
        if str((getattr(t, "metadata", {}) or {}).get("target_source", "")) == "branch_detector"
    ]
    if len(branch_targets) < 10:
        notes.append(f"only {len(branch_targets)} branch-detector hard-stops -> rays may un-bound")
        ok = False
    else:
        suppressed_n = sum(1 for t in branch_targets if _target_branch_detector_draw_suppressed(t))
        notes.append(
            f"real scene @ {_LIVE_RAYS} rays: {len(branch_targets)} branch-detector hard-stops kept "
            f"({suppressed_n} draw-suppressed)"
        )

    # (b) the 2-D projection draws ZERO detector footprints (no parallelograms)
    proj = SceneProjector2D("Vertical").project_bundle(bundle)
    footprints = sum(1 for c in proj.curves if getattr(c, "kind", "") == "detector_active_footprint")
    branch_planes = sum(
        1 for c in proj.curves
        if getattr(c, "kind", "") == "image" and int(getattr(c, "row_index", 0)) == -1
    )
    if footprints > 1:
        notes.append(f"2-D draws {footprints} detector footprints (>1) -> internal-bounce plaid returned")
        ok = False
    elif branch_planes > 1:
        notes.append(f"2-D draws {branch_planes} branch-detector planes (>1) -> plaid returned")
        ok = False
    else:
        notes.append(f"2-D draws {footprints} detector footprint(s) + {branch_planes} branch plane(s) (no plaid)")

    # (c) the bounded 3-D ray extent stays tight (the hard-stops still bound the rays)
    center, radius = scene_display_center_radius(bundle)
    planes = detector_planes_for_hard_stop(bundle, radius)
    from KrakenOS.UI.services.branch_detectors import _branch_path_draw_suppressed

    bounded: list[np.ndarray] = []
    bounded_suppressed: list[np.ndarray] = []
    for path in list(getattr(bundle, "ray_paths", []) or []):
        pts = np.asarray(getattr(path, "points_world", []), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        try:
            status = ray_path_terminal_status_from_events(path)
        except Exception:
            status = ""
        # bugs/0506/0605: thread branch_path so the guard measures what the display
        # actually draws (suppressed ghost branches keep the generous-board clip).
        branch = str(getattr(path, "branch_path", "") or "")
        bpts, _capped = bounded_ray_points_for_scene_display(
            pts, center, radius, terminal_status=status, detector_planes=planes,
            branch_path=branch,
        )
        bpts = np.asarray(bpts, dtype=float)
        if bpts.ndim == 2 and bpts.shape[0] >= 1 and bpts.shape[1] >= 3:
            bounded.append(bpts[:, :3])
            try:
                if branch and _branch_path_draw_suppressed(branch):
                    bounded_suppressed.append(bpts[:, :3])
            except Exception:
                pass
    if not bounded:
        notes.append("no bounded ray points produced -> cannot verify 3-D extent")
        ok = False
    else:
        allpts = np.vstack(bounded)
        allpts = allpts[np.all(np.isfinite(allpts), axis=1)]
        max_xy = float(np.max(np.abs(allpts[:, :2]))) if allpts.size else 0.0
        sup = np.vstack(bounded_suppressed) if bounded_suppressed else np.empty((0, 3))
        sup = sup[np.all(np.isfinite(sup), axis=1)] if sup.size else sup
        max_xy_sup = float(np.max(np.abs(sup[:, :2]))) if sup.size else 0.0
        if max_xy_sup > _BOUNDED_XY_LIMIT:
            notes.append(
                f"suppressed-branch extent max|x,y|={max_xy_sup:.0f} > {_BOUNDED_XY_LIMIT:.0f}"
                " -> ghost-branch starburst un-bounded"
            )
            ok = False
        elif max_xy > _ABSOLUTE_XY_CAP:
            notes.append(
                f"bounded 3-D ray extent max|x,y|={max_xy:.0f} > {_ABSOLUTE_XY_CAP:.0f}"
                " -> a drawn tail outruns the scene-envelope cap (endless line)"
            )
            ok = False
        else:
            notes.append(
                f"bounded 3-D ray extent holds: suppressed max|x,y|={max_xy_sup:.0f} "
                f"(<= {_BOUNDED_XY_LIMIT:.0f}), all {max_xy:.0f} (<= {_ABSOLUTE_XY_CAP:.0f}; "
                "primary fly-past tails are legal per bugs/0605)"
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
    label = "beam-splitter internal-bounce ghosts stay hard-stops but draw no 2-D clutter"
    print(("[PASS] " if ok else "[FAIL] ") + label + " (bugs/0183)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
