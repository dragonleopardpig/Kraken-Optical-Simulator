"""bugs/0511 -- a reaching leaf's detector pins to the Image unless the fit is a true waist.

Dragging the lens near the RA mirror clips the converging cone at the mirror
aperture; the leaf's closest-approach fit then lands mid-leg INSIDE the bugs/0100
trust window while 225/279 rays still LAND on the designed Image -- the detector
un-pinned and drew a phantom sensor plane between prism and camera, and the
coverage overlay (whose seating ladder keys on a pinned arm) drew NOTHING, losing
the object plane ("sensor dislocate, missing object plane",
flag_20260802_195029).

Fix under test (branch_detectors.py): inside the trust window, a forward
convergence is trusted ONLY when it is a genuine WAIST -- transverse RMS at the
fit below ``_WAIST_TIGHTNESS_RATIO`` x the RMS at the reached image. A clipped
bundle (barely tighter at its crossing) pins to the Image; a real per-branch
focus (the dual-lens reflect arm the window protects) stays trusted.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0511_reaching_leaf_detector_pin
"""
from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def _path(o, aim, bp, reaches):
    from KrakenOS.UI.scene_geometry import RayPath3D

    o = np.asarray(o, dtype=float)
    d = np.asarray(aim, dtype=float) - o
    d = d / np.linalg.norm(d)
    pts = np.vstack((o - d * 5.0, o, o + d * 300.0))
    return RayPath3D(branch_path=bp, reaches_image=bool(reaches), points_world=pts)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    from KrakenOS.UI.services import branch_detectors as bd

    src = inspect.getsource(bd.derive_branch_detectors)
    check(
        "_WAIST_TIGHTNESS_RATIO" in src and "_transverse_rms_at_plane" in src,
        "S1: the trust window applies the waist-tightness gate",
    )

    img_target = SimpleNamespace(
        is_detector=True, surface="Image",
        center_world=np.asarray((0.0, 0.0, 300.0), dtype=float),
        active_width_mm=20.0, active_height_mm=20.0,
        metadata={"target_source": "table_row"},
    )
    # a second (non-reaching) leaf so multi_leaf derivation runs
    other = [_path((x, 0.0, 200.0), (60.0, 0.0, 250.0), "S1:S1/reflect", False) for x in (-4.0, 0.0, 4.0)]

    # B1 -- CLIPPED bundle: wide near-parallel component + a converging pair crossing at
    # z=270. The fit sits in the window (behind=-30 of to_image=100) but is NOT a waist
    # (rms ratio ~0.88) -> must PIN to the image at z=300.
    clipped = [_path((x, 0.0, 200.0), (x, 0.0, 300.0), "S1:S1/transmit", True) for x in np.linspace(-8.0, 8.0, 5)]
    clipped += [_path((x, 0.0, 200.0), (0.0, 0.0, 270.0), "S1:S1/transmit", True) for x in (-11.0, 11.0)]
    o, d = bd._exit_rays_for_group(clipped)
    md = bd._unit(d.mean(axis=0))
    focus, _ = bd._closest_approach_point(o, d)
    behind = float(np.dot(focus - img_target.center_world, md))
    to_image = float(np.dot(img_target.center_world - o.mean(axis=0), md))
    ratio = bd._transverse_rms_at_plane(o, d, focus, md) / bd._transverse_rms_at_plane(
        o, d, img_target.center_world, md
    )
    check(
        -0.5 * to_image < behind < -1.0 and ratio > bd._WAIST_TIGHTNESS_RATIO,
        f"B0: clipped fixture sits in the trust window with a non-waist ratio "
        f"(behind={behind:.1f}, ratio={ratio:.2f})",
    )
    dets = bd.derive_branch_detectors(clipped + other, existing_targets=[img_target], scene_radius=50.0)
    t = next((x for x in dets if "transmit" in x.branch_path), None)
    check(
        t is not None
        and t.focus_source == "reached_image"
        and abs(float(t.center_world[2]) - 300.0) < 1.0,
        f"B1: clipped reaching leaf PINS to the Image "
        f"(got {getattr(t, 'focus_source', None)!r} at {getattr(t, 'center_world', None)})",
    )

    # B2 -- WAIST bundle: every ray through (0,0,270) (a real per-branch focus, the
    # dual-lens reflect-arm class) -> the window still TRUSTS the fit.
    waist = [_path((x, 0.0, 200.0), (0.0, 0.0, 270.0), "S1:S1/transmit", True) for x in np.linspace(-8.0, 8.0, 7)]
    dets = bd.derive_branch_detectors(waist + other, existing_targets=[img_target], scene_radius=50.0)
    t = next((x for x in dets if "transmit" in x.branch_path), None)
    check(
        t is not None
        and t.focus_source == "converging_rays"
        and abs(float(t.center_world[2]) - 270.0) < 1.0,
        f"B2: waist leaf keeps its trusted per-branch focus "
        f"(got {getattr(t, 'focus_source', None)!r} at {getattr(t, 'center_world', None)})",
    )

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    editor = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services import optical_axis_tree as tree_mod

        editor = KrakenLayoutEditor()
        editor.layout_files["lens_near_mirror_probe"] = SCENE
        editor.load_layout_by_name("lens_near_mirror_probe")
        editor.translate_step_overlay("led", (-36.9, 0.0, 0.0))
        editor.translate_scene_row_pose_vector(7, (-22.5, 0.0, 0.0))
        editor.translate_step_overlay("lens", (24.2, 0.0, 0.0))
        # bugs/0524: an along-leg lens drag now WRITES its section gaps (the drag is a
        # conjugate edit), and the interactive gesture ends with the Solve-for-FOV refocus
        # (the 0520 commit hook). The raw translate alone leaves the scene legitimately
        # defocused -- a state the user never sees since 0520 -- so complete the gesture
        # the way the product does before asserting the pin.
        editor.snap_detector_to_image_plane()
        system, rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        img8 = np.asarray(tree_mod.row_world_pose(editor.rows, 8), dtype=float).reshape(-1)[:3]
        dets = [t for t in (getattr(bundle, "targets", []) or []) if getattr(t, "is_detector", False)]
        pinned = [
            t for t in dets
            if str(((getattr(t, "metadata", None) or {}).get("focus_source", "")) or "") == "reached_image"
        ]
        near = [
            t for t in pinned
            if np.linalg.norm(np.asarray(t.center_world, dtype=float).reshape(3) - img8) < 1.0
        ]
        check(
            bool(near),
            f"A1: lens-near-mirror -- the imaging arm's detector is pinned ON the Image row "
            f"({len(pinned)} pinned of {len(dets)} detectors, image={np.round(img8, 2)})",
        )

        from KrakenOS.UI.services.detector_coverage_overlay import DetectorCoverageOverlayService
        import pyvista as pv

        class _Rec:
            def __init__(self, ed):
                self.editor = ed
                self.mesh_actors = []

            def _add_mesh_actor(self, mesh, **kw):
                try:
                    self.mesh_actors.append(tuple(float(b) for b in mesh.bounds))
                except Exception:
                    pass
                return object()

            def _add_renderer_view_prop(self, actor):
                return object()

        rec = _Rec(editor)
        DetectorCoverageOverlayService(rec, pv_module=pv).add_overlays(system, bundle)
        obj_actors = [
            b for b in rec.mesh_actors
            if abs(b[4]) < 8.0 and abs(b[5]) < 8.0 and abs((b[0] + b[1]) / 2.0 + 36.9) < 20.0
        ]
        check(
            bool(obj_actors),
            f"A2: the object-plane overlay draws AND rides the slid station "
            f"({len(obj_actors)} actor(s) near x=-36.9, z~0)",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass

    return ok, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
