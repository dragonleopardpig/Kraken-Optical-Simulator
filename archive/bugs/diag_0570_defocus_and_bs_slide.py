"""Diagnostic for flag_20260806_102150 ("solve FOV partially works, rays still defocus at
sensor"), flag_20260806_102258 ("right click defocus not working") and the user's follow-up
("the BS plate is shifted down. It happened after FOV solve"), on the scene they saved as
``attachment/machine_vision_Pyrite85_BS.py``.

Answers three questions in ONE run (the machine only has room for one of these at a time):

1. WHERE IS THE BS?  The promoted beam splitter is glued to the LED body, which is placed by an
   absolute overlay offset.  Its own row is WORLD-placed (pose = station + desp_z), so any
   object-gap write slides it while the LED stays -- print both.
2. IS THE FOCUS MEASURABLE?  ``_traced_bundle_best_focus_shift`` is what both the FOV solve's
   finisher (bugs/0490) and the right-click "Snap detector to image plane (remove defocus)"
   consume.  Print it, and the analysis-surface shift beside it.
3. DOES THE SNAP DO ANYTHING?  Drive ``snap_detector_to_image_plane`` and report what moved.

Run (capped so the desktop keeps cores):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0570_defocus_and_bs_slide.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Pyrite85_BS.py"


def main() -> int:
    if not SCENE.exists():
        print(f"SKIP: {SCENE} not present")
        return 0
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import row_placement

    editor = KrakenLayoutEditor()
    try:
        editor.layout_files["probe"] = SCENE
        editor.load_layout_by_name("probe")

        def pose(i):
            return np.asarray(row_placement.world_pose(editor, i).position, dtype=float)

        print("ROWS")
        stations = editor._row_z_positions()
        for i, row in enumerate(editor.rows):
            print(
                f"  {i:>2} {str(row.name)[:34]:34} th={float(row.thickness):9.3f} "
                f"station={stations[i]:9.3f} pose={np.round(pose(i), 3).tolist()}"
            )

        print("\n1. ILLUMINATION UNIT (is the BS still on its LED?)")
        for label in ("led", "optical", "lens", "camera"):
            try:
                mesh = editor._transformed_imported_step_mesh_for_label(label)
            except Exception as exc:
                mesh = None
                print(f"   {label}: mesh error {exc}")
            if mesh is not None:
                b = np.asarray(mesh.bounds, dtype=float)
                print(
                    f"   {label:8s} bounds x[{b[0]:8.3f},{b[1]:8.3f}] z[{b[4]:8.3f},{b[5]:8.3f}] "
                    f"centre=({(b[0]+b[1])/2:8.3f},{(b[2]+b[3])/2:7.3f},{(b[4]+b[5])/2:8.3f})"
                )
        for i, row in enumerate(editor.rows):
            promo = (getattr(row, "advanced", None) or {}).get("StepOverlayPromotion") or {}
            if promo:
                print(
                    f"   promoted row {i}: pose={np.round(pose(i), 3).tolist()} "
                    f"station_neutral={bool(promo.get('station_neutral'))} "
                    f"beam_splitter={bool(promo.get('beam_splitter'))} "
                    f"axial_reserve={promo.get('axial_reserve_mm')}"
                )
        try:
            print("   optical_led_glued:", bool(editor.optical_led_glued()))
        except Exception as exc:
            print("   optical_led_glued: ?", exc)
        try:
            print("   _object_locked_redirect_row(0) ->", end=" ")
            from types import SimpleNamespace

            from KrakenOS.UI.services.quick_estimation import QuickEstimationService

            qe = QuickEstimationService(SimpleNamespace(editor=editor))
            print(qe._object_locked_redirect_row(0), "(None = the object write slides everything)")
        except Exception as exc:
            print("error", exc)

        print("\n2. IS THE FOCUS MEASURABLE?")
        for name in ("_traced_bundle_best_focus_shift", "_real_ray_best_focus_shift_for_rows"):
            try:
                value = getattr(editor, name)()
            except Exception as exc:
                value = f"RAISED {type(exc).__name__}: {exc}"
            print(f"   {name}() = {value}")

        print("\n3. DOES THE SNAP MOVE ANYTHING?")
        image_row = len(editor.rows) - 1
        before = pose(image_row)
        gap_before = float(editor.rows[image_row - 1].thickness)
        try:
            result = editor.snap_detector_to_image_plane()
        except Exception as exc:
            result = f"RAISED {type(exc).__name__}: {exc}"
        after = pose(image_row)
        print(f"   snap_detector_to_image_plane() -> {result}")
        try:
            log = [l for l in (editor.debug_lines if hasattr(editor, "debug_lines") else []) if "snap detector iter" in str(l)]
        except Exception:
            log = []
        if not log:
            try:
                log = [l for l in str(editor.debug_text.get("1.0", "end")).splitlines() if "snap detector iter" in l]
            except Exception:
                log = []
        for line in log:
            print("   |", str(line).strip())
        print(f"   status: {editor.status_var.get()!r}")
        print(
            f"   sensor {np.round(before, 3).tolist()} -> {np.round(after, 3).tolist()} "
            f"(moved {float(np.linalg.norm(after - before)):.4f} mm); "
            f"gap row {image_row - 1}: {gap_before:.4f} -> {float(editor.rows[image_row-1].thickness):.4f}"
        )
        try:
            print("   _traced_bundle_best_focus_shift() after =", editor._traced_bundle_best_focus_shift())
        except Exception as exc:
            print("   _traced_bundle_best_focus_shift() after RAISED", exc)
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
