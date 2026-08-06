"""Diagnostic for flag_20260806_074148 -- "swapped lens, changed FOV, solve for thickness,
camera and RA mirror misplaced."

The recording (recording_20260806_074228.json) shows exactly one solve:
``fov_solve(plane="object", mode="thickness", width=23.0, height=23.0)``.

Suspicion: the folded conjugate solve writes the IMAGE-leg delta into
``image_gap_row = gap_start``, and ``gap_start`` walks back only through promoted MIRROR
folds -- so on this scene it stops on the promoted BEAM-SPLITTER PLATE row (S6), whose
thickness is 0 and whose promotion is ``station_neutral`` (its body is absolutely placed;
its row index is not its geometry -- bugs/0546). Inflating it pushes every downstream
station along the chain, lifting the RA mirror and the sensor off the beam.

Prints the row table, what the solve decides, and the world poses before/after the REAL
``fov_solve`` call.

Run:
    xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0569_fov_solve_image_gap_row.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_AZ85_RA_Mirror_BS.py"
TARGET_FOV = (23.0, 23.0)


def _rowtab(editor, title: str) -> None:
    from KrakenOS.UI.services import row_placement

    print(f"\n{title}")
    print(f"  {'i':>2} {'surface':10} {'name':38} {'thick':>10} {'station':>9} {'pose_z':>9} {'flags'}")
    stations = editor._row_z_positions()
    for i, row in enumerate(editor.rows):
        advanced = getattr(row, "advanced", None) or {}
        promo = advanced.get("StepOverlayPromotion") or {}
        flags = []
        if promo:
            flags.append("promoted")
        if promo.get("station_neutral"):
            flags.append("STATION-NEUTRAL")
        if promo.get("beam_splitter"):
            flags.append("beam-splitter")
        faces = (advanced.get("OpticalSolidFaces") or {}).get("faces") or []
        if any(str(f.get("role", "")).strip().lower() == "mirror" for f in faces):
            flags.append("MIRROR-fold")
        pose = row_placement.world_pose(editor, i)
        print(
            f"  {i:>2} {str(row.surface)[:10]:10} {str(row.name)[:38]:38} "
            f"{float(row.thickness):10.4f} {stations[i]:9.3f} {float(pose.position[2]):9.3f} "
            f"{','.join(flags)}"
        )


def main() -> int:
    if not SCENE.exists():
        print(f"SKIP: {SCENE} not present")
        return 0
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    try:
        editor.layout_files["fov_probe"] = SCENE
        editor.load_layout_by_name("fov_probe")
        _rowtab(editor, "ROWS AS LOADED")

        # The service hangs off the INSPECTOR (it reads inspector.editor); a shim host is
        # enough for the solve, which touches only the editor.
        from types import SimpleNamespace

        from KrakenOS.UI.services.quick_estimation import QuickEstimationService

        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        print("\nQuick-estimation service:", type(qe).__name__)

        sensor_semi = None
        try:
            sensor_semi = qe._sensor_semi() if qe is not None else None
        except Exception as exc:
            print("  _sensor_semi failed:", exc)
        print("  sensor semi-diagonal:", sensor_semi)

        import numpy as np

        obj_diag = float(np.hypot(*TARGET_FOV))
        semi = obj_diag / 2.0
        print(f"  target object semi-diagonal for {TARGET_FOV[0]}x{TARGET_FOV[1]}: {semi:.4f} mm")

        if sensor_semi:
            magnitude = float(sensor_semi) / semi
            folded = editor._folded_conjugate_gaps_for_magnification(magnitude)
            print(f"\n_folded_conjugate_gaps_for_magnification(|m|={magnitude:.6g}):")
            if folded is None:
                print("  -> None (not folded / infeasible)")
            else:
                for key in (
                    "object_gap_row", "image_gap_row", "object_delta", "image_delta",
                    "object_total", "image_total", "object_distance", "image_distance",
                ):
                    print(f"  {key:18s} {folded[key]}")
                ig = int(folded["image_gap_row"])
                row = editor.rows[ig]
                promo = (getattr(row, "advanced", None) or {}).get("StepOverlayPromotion") or {}
                print(
                    f"  -> the image delta lands on row {ig} ({row.name!r}, thickness "
                    f"{float(row.thickness):.4f}, station_neutral={bool(promo.get('station_neutral'))})"
                )

        print("\n--- running the REAL fov_solve(object, thickness, 23, 23) ---")
        ok, msg = qe.fov_solve("object", "thickness", TARGET_FOV[0], TARGET_FOV[1])
        print("  ok:", ok)
        print("  msg:", msg)
        _rowtab(editor, "ROWS AFTER THE SOLVE")
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
