"""Guard: a display-only overlay's hover outline tracks the re-aligned body.

bugs/0113 ("ghost highlight"): in measure mode the camera STEP's gold hover
outline stuck ~13 mm in FRONT of the drawn camera body. Ground truth from the
flag bundle (flag_20260623_074500_871): the hover outline was a flat 69.4 mm
square at z=589.56 while the live camera body front face sat at z=603.07 -- a
+13.51 mm gap that exactly matched the beam-splitter promote pushing the image
plane (and so the image-plane-aligned camera body) back.

Root cause: the camera/led face metadata is **pose-blind cached** (baked once per
session from a snap STL written at the body's then-current pose, to dodge an
18-35 s re-bake freeze -- bugs/0111). The rendered body, though, re-aligns to the
live image plane every refresh (``_transformed_imported_camera_step_mesh`` ->
``image_plane_z - front_to_sensor``). The snap STL's face cell indices do not map
to the live full-body display mesh, so the hover-outline builder falls through to
the cached-STL path and draws the outline at the BAKE-TIME pose -- the ghost.

Fix (apply-on-read, no re-bake): ``_step_overlay_face_metadata`` stamps the
alignment target at bake time (``alignment_target_z_at_bake``);
``_hover_overlay_for_step_face_impl`` shifts the cached-STL outline + centre by
``current_target - baked_target`` for display-only labels so the gold outline
lands on the live body.

Two parts:

* ``run_checks`` -- display-free structure + functional assertions (the metadata
  stamp, the delta accessor across cases, the geometry-shift helpers, and the
  source wiring at the cached-STL outline return).
* ``render_alignment_proof`` -- a headless image/geometry snapshot (needs a GL
  context / Xvfb) proving a stale-pose outline, once shifted by the delta, sits
  on the live body.

Penta phase 103 (baseline -> 104) runs ``run_checks`` only (no rendering).
"""

from __future__ import annotations

import inspect
import os
import types
from pathlib import Path


def _module_source(module) -> str:
    path = inspect.getsourcefile(module) or inspect.getfile(module)
    return Path(path).read_text(encoding="utf-8")


def run_checks() -> list[tuple[str, bool, str]]:
    import numpy as np

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services import scene_placement_commands
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.validate_open3d_camera_overlay_hover_alignment import _FakeEditor

    results: list[tuple[str, bool, str]] = []

    placement_src = _module_source(scene_placement_commands)

    # 1) the metadata bake stamps the alignment target for display-only labels.
    ed = _FakeEditor()
    cam_md = ed._step_overlay_face_metadata("camera")
    cam_stamp = cam_md.get("alignment_target_z_at_bake")
    cam_expected = round(ed.image_plane_z - ed.front_to_sensor, 6)
    led_md = ed._step_overlay_face_metadata("led")
    led_stamp = led_md.get("alignment_target_z_at_bake")
    stamp_ok = cam_stamp == cam_expected and led_stamp == round(ed.led_z, 6)
    results.append(
        ("metadata bake stamps alignment_target_z_at_bake for display-only labels",
         stamp_ok, f"camera={cam_stamp} (exp {cam_expected}), led={led_stamp}")
    )

    # 2) the stamp survives a pose-blind cache hit (an image-plane move must not
    #    re-bake, so the stamp keeps the BAKE-TIME value -> a non-zero delta).
    ed.image_plane_z = ed.image_plane_z + 30.0
    moved_md = ed._step_overlay_face_metadata("camera")
    pose_blind = moved_md is cam_md and moved_md.get("alignment_target_z_at_bake") == cam_stamp
    results.append(
        ("an image-plane move keeps the same cached metadata + bake-time stamp (pose-blind)",
         pose_blind, f"same_object={moved_md is cam_md}, stamp={moved_md.get('alignment_target_z_at_bake')}")
    )

    # 3) _display_only_overlay_axial_delta returns current-minus-baked, and 0 for
    #    non-display-only / unchanged / unstamped / no-image-plane cases.
    delta_fn = Kraken3DInspector._display_only_overlay_axial_delta

    def _delta(cur, baked, label="camera", md=...):
        editor = types.SimpleNamespace(
            _DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC=ScenePlacementMixin._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC,
            _step_overlay_alignment_target_z=lambda lbl: cur if str(lbl).lower() == "camera" else None,
            _step_overlay_face_metadata=lambda lbl: {"alignment_target_z_at_bake": baked},
        )
        insp = types.SimpleNamespace(editor=editor)
        if md is ...:
            md = {"alignment_target_z_at_bake": baked}
        return delta_fn(insp, label, md)

    moved_delta = _delta(603.07, 589.56)
    delta_ok = (
        abs(moved_delta - 13.51) < 1e-6
        and _delta(603.07, 603.07) == 0.0          # unchanged
        and _delta(603.07, 589.56, label="lens") == 0.0   # not display-only
        and _delta(603.07, None, md={}) == 0.0     # no bake stamp (old cache)
        and _delta(None, 589.56) == 0.0            # no image plane
    )
    results.append(
        ("_display_only_overlay_axial_delta = current - baked (0 when not applicable)",
         delta_ok, f"moved_delta={moved_delta}")
    )

    # 4) the geometry-shift helpers move a stale outline/centre onto the live body
    #    and do NOT mutate the cached source (inplace=False).
    geom_ok = True
    detail4 = ""
    try:
        import pyvista as pv

        stale = pv.Plane(center=(0, 0, 589.56), direction=(0, 0, 1), i_size=69.4, j_size=69.4)
        moved = Kraken3DInspector._translate_hover_mesh(stale, (0.0, 0.0, 13.51))
        center = Kraken3DInspector._shift_center_z((1.0, 2.0, 589.56), 13.51)
        geom_ok = (
            abs(float(moved.bounds[4]) - 603.07) < 1e-3
            and abs(float(stale.bounds[4]) - 589.56) < 1e-3   # source untouched
            and abs(float(center[2]) - 603.07) < 1e-6
            and Kraken3DInspector._translate_hover_mesh(None, (0, 0, 1)) is None
        )
        detail4 = f"moved_z={float(moved.bounds[4]):.2f}, source_z={float(stale.bounds[4]):.2f}, center_z={float(center[2]):.2f}"
    except Exception as exc:  # pragma: no cover - pyvista import/driver dependent
        geom_ok = False
        detail4 = f"pyvista geometry check errored: {exc}"
    results.append(
        ("_translate_hover_mesh / _shift_center_z shift onto the live body (source untouched)",
         geom_ok, detail4)
    )

    # 5) source wiring: the cached-STL outline return shifts by the delta.
    impl_src = inspect.getsource(Kraken3DInspector._hover_overlay_for_step_face_impl)
    wiring_ok = (
        "_display_only_overlay_axial_delta(str(label).strip().lower(), metadata)" in impl_src
        and "self._translate_hover_mesh(outline" in impl_src
        and "self._shift_center_z(center" in impl_src
    )
    results.append(
        ("_hover_overlay_for_step_face_impl shifts the cached-STL outline by the delta",
         wiring_ok, f"wired={wiring_ok}")
    )

    # 6) source: the bake stamps the alignment target only for display-only labels.
    stamp_src_ok = (
        'metadata["alignment_target_z_at_bake"] = self._step_overlay_alignment_target_z(label)' in placement_src
        and "label in self._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC" in placement_src
        and "bugs/0113" in placement_src
    )
    results.append(
        ("_step_overlay_face_metadata stamps the bake-time alignment target (display-only)",
         stamp_src_ok, f"stamped={stamp_src_ok}")
    )

    return results


def render_alignment_proof(png_path: str | None = None) -> tuple[bool, str]:
    """Prove a stale-pose outline, shifted by the delta, lands on the live body.

    Geometry proof (works headless with pyvista, no GL needed): build the live
    camera front face at z=603.07 and a stale outline at z=589.56, apply the
    +13.51 delta, and assert the outline now coincides with the body face. Also
    writes a PNG when a GL context is available.
    """
    import numpy as np
    import pyvista as pv

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    live_front_z = 603.07
    stale_z = 589.56
    delta = live_front_z - stale_z

    body_face = pv.Plane(center=(0, 0, live_front_z), direction=(0, 0, 1), i_size=70.0, j_size=70.0)
    stale_outline = pv.Plane(center=(0, 0, stale_z), direction=(0, 0, 1), i_size=69.4, j_size=69.4)

    before_gap = abs(float(stale_outline.center[2]) - live_front_z)
    fixed = Kraken3DInspector._translate_hover_mesh(stale_outline, (0.0, 0.0, delta))
    after_gap = abs(float(fixed.center[2]) - live_front_z)

    passed = before_gap > 5.0 and after_gap < 1e-3

    if png_path and os.environ.get("DISPLAY"):
        try:
            pl = pv.Plotter(off_screen=True, window_size=(360, 360))
            pl.add_mesh(body_face, color=(0.6, 0.6, 0.6), opacity=0.5)
            pl.add_mesh(fixed.extract_feature_edges(), color=(0.95, 0.78, 0.05), line_width=4)
            pl.view_xz()
            pl.screenshot(str(png_path))
            pl.close()
        except Exception:
            pass

    detail = f"gap before shift={before_gap:.2f} mm, after shift={after_gap:.4f} mm (delta={delta:.2f})"
    return passed, detail


def main() -> int:
    results = run_checks()
    ok = True
    for name, passed, det in results:
        print(f"{name} | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed

    try:
        png = os.environ.get("KRAKEN_GHOST_OUTLINE_PNG") or "/tmp/ghost_hover_outline_alignment.png"
        passed, det = render_alignment_proof(png)
        print(f"render proof: shifted outline lands on the live body | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed
    except Exception as exc:  # pragma: no cover - pyvista/driver dependent
        print(f"render proof skipped (no usable pyvista/GL): {exc}")

    print("[PASS] ghost hover outline tracks the re-aligned body" if ok
          else "[FAIL] ghost hover outline alignment regressed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
