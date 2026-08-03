"""Display-free regression guard for bugs/0184.

The folded MV-150 coaxial-LED scene is a diffuse double-pass. After the 0182 (scatter)
and 0183 (internal-bounce) per-path draw gates, ONE branch detector still drew a tilted
orange parallelogram + crosshairs in the 2-D 'YZ full 3-D' view -- but only at the reduced
preview ray count (the flag's ``sampling_diagnostics.ray_count`` was 15, not the live 60).

That survivor is the clean single-pass beam-splitter LEAK ``branch_path='S1:S1/transmit'``:
the LED light transmitting straight through the glued cube once and escaping. It carries
NEITHER a scatter token (0182) NOR an internal-bounce signature (0183), so both per-path
gates pass it. It is ray-count-dependent: at 60 rays the deep internal bounces extend it
into a non-terminal prefix (no detector); at 15 rays it is a terminal leaf (a detector that
draws). A detector that blinks in/out with the preview count is noise.

Fix: a SCENE-LEVEL gate. In a scene with ANY diffuse-scatter path, EVERY branch detector is
noise (the only real detector is the camera/Image plane), so all branch-detector 2-D draws
are gated off -- while each target is KEPT as an ``is_detector`` ray hard-stop (the rays stay
bounded in 3-D, the lesson of the 0182 starburst). A clean (scatter-free) beam splitter has
no scatter path, so the scene gate is inert and both arm detectors draw (bugs/0090).

Checks:

* Unit -- ``ray_paths_have_diffuse_scatter`` (scatter scene True / clean scene False); an
  end-to-end projection of a synthetic SceneBundle: a scatter scene draws ZERO branch-detector
  footprints yet KEEPS every branch-detector target (the hard-stops), while a clean 2-arm beam
  splitter still DRAWS both arms.
* Real scene -- the folded coaxial-LED bundle at BOTH 15 (the recording's preview count) and
  60 (the live count): (a) branch-detector hard-stop targets survive; (b) the 2-D projection
  draws ZERO detector footprints at each count (no parallelogram); (c) the bounded 3-D ray
  extent stays tight (the hard-stops still bound the rays).

Run headless: ``python -m KrakenOS.UI.validate_open3d_branch_detector_leak_clutter``
"""
from __future__ import annotations

import os

import numpy as np

from KrakenOS.UI.scene_geometry import (
    RayEvent3D,
    RayPath3D,
    SceneBundle,
    ray_path_terminal_status_from_events,
    ray_paths_have_diffuse_scatter,
)
from KrakenOS.UI.scene_projector import (
    SceneProjector2D,
    bounded_ray_points_for_scene_display,
    detector_planes_for_hard_stop,
    scene_display_center_radius,
)
from KrakenOS.UI.services.branch_detectors import (
    branch_detector_scene_target,
    derive_branch_detectors,
)

os.environ.setdefault("KRAKENOS_HEADLESS", "1")

# The recording was at the world_envelope PREVIEW count (15); 0183 was verified at the
# live count (60). The leak draws at 15 and not 60, so assert BOTH are clean.
_PREVIEW_RAYS = 15
_LIVE_RAYS = 60
_BOUNDED_XY_LIMIT = 150.0


def _ray(branch_path: str, origin, direction, *, ray_index: int, events=None) -> RayPath3D:
    o = np.asarray(origin, dtype=float)
    d = np.asarray(direction, dtype=float)
    return RayPath3D(
        ray_index=int(ray_index),
        points_world=np.asarray((o, o + 40.0 * d), dtype=float),
        branch_path=branch_path,
        branch_label=branch_path,
        events=list(events or []),
    )


def _scatter_event(point) -> RayEvent3D:
    return RayEvent3D(
        event_id="surface:99",
        event_kind="surface",
        event_type="scatter",
        surface_id=99,
        mesh_face_id="F099",
        point_world=np.asarray(point, dtype=float),
    )


def _diffuse_double_pass_paths() -> list[RayPath3D]:
    """A diffuse return ray (scatter event) + the clean S1:S1/transmit LED leak."""
    scatter = RayPath3D(
        ray_index=0,
        points_world=np.asarray([[0.0, 0.0, 0.0], [4.0, 6.0, 20.0], [12.0, 14.0, 42.0]], dtype=float),
        branch_path="S3:S3/scatter01",
        branch_label="S3:S3/scatter01",
        events=[_scatter_event([4.0, 6.0, 20.0])],
    )
    return [
        scatter,
        _ray("S1:S1/transmit", [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=1),
        _ray("S1:S1/transmit", [4.0, 1.0, 0.0], [0.05, 0.0, 1.0], ray_index=2),
    ]


def _clean_beam_splitter_paths() -> list[RayPath3D]:
    """A genuine scatter-free beam splitter: reflect (+Y) and transmit (+Z) arms."""
    return [
        _ray("S1:S1/reflect", [0.0, 0.0, 0.0], [0.0, 1.0, 0.05], ray_index=0),
        _ray("S1:S1/reflect", [0.0, 4.0, 1.0], [0.0, 1.0, 0.05], ray_index=1),
        _ray("S1:S1/transmit", [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=2),
        _ray("S1:S1/transmit", [4.0, 1.0, 0.0], [0.05, 0.0, 1.0], ray_index=3),
    ]


def _bundle_with_branch_detectors(ray_paths: list[RayPath3D]) -> tuple[SceneBundle, int]:
    dets = derive_branch_detectors(ray_paths, existing_targets=[], scene_radius=50.0)
    targets = [branch_detector_scene_target(d, row_index=100000 + i) for i, d in enumerate(dets)]
    return SceneBundle(ray_paths=list(ray_paths), targets=targets), len(targets)


def _count_footprints(bundle: SceneBundle) -> int:
    proj = SceneProjector2D("Vertical").project_bundle(bundle)
    return sum(1 for c in proj.curves if getattr(c, "kind", "") == "detector_active_footprint")


def _check_unit(notes: list[str]) -> bool:
    ok = True

    # (1) the scene-scatter primitive
    if not ray_paths_have_diffuse_scatter(_diffuse_double_pass_paths()):
        notes.append("ray_paths_have_diffuse_scatter MISSED a scatter scene")
        ok = False
    elif ray_paths_have_diffuse_scatter(_clean_beam_splitter_paths()):
        notes.append("ray_paths_have_diffuse_scatter FALSE-TRIPPED on a clean scene")
        ok = False
    else:
        notes.append("ray_paths_have_diffuse_scatter: scatter scene True, clean scene False")

    # (2) a diffuse double-pass: ZERO branch-detector footprints drawn, ALL kept as targets
    scatter_bundle, scatter_targets = _bundle_with_branch_detectors(_diffuse_double_pass_paths())
    drawn = _count_footprints(scatter_bundle)
    if scatter_targets < 2:
        notes.append(f"scatter scene: expected >=2 branch-detector targets, got {scatter_targets}")
        ok = False
    elif drawn != 0:
        notes.append(f"scatter scene draws {drawn} branch-detector footprint(s) -> leak parallelogram returns")
        ok = False
    else:
        notes.append(
            f"scatter scene: {scatter_targets} branch-detector hard-stops kept, 0 footprints drawn "
            "(incl. the clean S1:S1/transmit leak)"
        )

    # (3) a clean (scatter-free) beam splitter still DRAWS both arms (bugs/0090 preserved)
    clean_bundle, clean_targets = _bundle_with_branch_detectors(_clean_beam_splitter_paths())
    clean_drawn = _count_footprints(clean_bundle)
    if clean_targets != 2:
        notes.append(f"clean beam splitter: expected 2 arm detectors, got {clean_targets}")
        ok = False
    elif clean_drawn < 2:
        notes.append(f"clean beam splitter drew only {clean_drawn} footprint(s) -> scene gate too broad")
        ok = False
    else:
        notes.append(f"clean beam splitter: both arms draw ({clean_drawn} footprints, scene gate inert)")
    return ok


def _check_real_scene(notes: list[str], ray_count: int) -> bool:
    try:
        from KrakenOS.UI.validate_open3d_optical_axis_scatter_clutter import _build_folded_bundle
    except Exception as exc:  # pragma: no cover
        notes.append(f"could not import folded-scene harness: {exc!r}")
        return False
    try:
        bundle = _build_folded_bundle(ray_count)
    except Exception as exc:  # pragma: no cover
        notes.append(f"real folded-scene build @ {ray_count} rays raised: {exc!r}")
        return False

    ok = True

    # (a) the hard-stop detectors survive (they are NOT dropped)
    branch_targets = [
        t for t in (getattr(bundle, "targets", []) or [])
        if str((getattr(t, "metadata", {}) or {}).get("target_source", "")) == "branch_detector"
    ]
    if len(branch_targets) < 10:
        notes.append(f"@ {ray_count} rays: only {len(branch_targets)} branch-detector hard-stops -> rays may un-bound")
        ok = False

    # (b) the 2-D projection draws ZERO detector footprints (no parallelogram)
    proj = SceneProjector2D("Vertical").project_bundle(bundle)
    footprints = sum(1 for c in proj.curves if getattr(c, "kind", "") == "detector_active_footprint")
    branch_planes = sum(
        1 for c in proj.curves
        if getattr(c, "kind", "") == "image" and int(getattr(c, "row_index", 0)) == -1
    )
    if footprints != 0:
        notes.append(f"@ {ray_count} rays: 2-D draws {footprints} detector footprint(s) -> leak parallelogram returned")
        ok = False
    elif branch_planes != 0:
        notes.append(f"@ {ray_count} rays: 2-D draws {branch_planes} branch-detector plane(s) -> clutter returned")
        ok = False
    else:
        notes.append(
            f"@ {ray_count} rays: {len(branch_targets)} branch-detector hard-stops kept, "
            f"2-D draws {footprints} footprint(s) + {branch_planes} plane(s) (clean)"
        )

    # (c) the bounded 3-D ray extent stays tight (the hard-stops still bound the rays)
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
        # bugs/0506: thread the production kwargs -- the 0459 hit_detector exemption is
        # branch/scene-aware, and the guard must measure what the display actually draws.
        bpts, _capped = bounded_ray_points_for_scene_display(
            pts, center, radius, terminal_status=status, detector_planes=planes,
            branch_path=str(getattr(path, "branch_path", "") or ""),
            scene_has_diffuse_scatter=ray_paths_have_diffuse_scatter(
                list(getattr(bundle, "ray_paths", []) or [])
            ),
        )
        bpts = np.asarray(bpts, dtype=float)
        if bpts.ndim == 2 and bpts.shape[0] >= 1 and bpts.shape[1] >= 3:
            bounded.append(bpts[:, :3])
    if not bounded:
        notes.append(f"@ {ray_count} rays: no bounded ray points produced -> cannot verify 3-D extent")
        ok = False
    else:
        allpts = np.vstack(bounded)
        allpts = allpts[np.all(np.isfinite(allpts), axis=1)]
        max_xy = float(np.max(np.abs(allpts[:, :2]))) if allpts.size else 0.0
        if max_xy > _BOUNDED_XY_LIMIT:
            notes.append(f"@ {ray_count} rays: bounded 3-D ray extent max|x,y|={max_xy:.0f} > {_BOUNDED_XY_LIMIT:.0f}")
            ok = False
        else:
            notes.append(f"@ {ray_count} rays: bounded 3-D ray extent tight: max|x,y|={max_xy:.0f}")
    return ok


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    ok = _check_unit(notes) and ok
    ok = _check_real_scene(notes, _PREVIEW_RAYS) and ok
    ok = _check_real_scene(notes, _LIVE_RAYS) and ok
    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(("  ok  " if ok else "  --  ") + note)
    label = "diffuse double-pass draws no branch-detector leak clutter (2-D full-3D, preview + live counts)"
    print(("[PASS] " if ok else "[FAIL] ") + label + " (bugs/0184)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
