"""Diagnostic for the 4-flag AZ85 RA-mirror recording (20260713_200738).

Loads the user's REAL scene (attachment/machine_vision_AZ85_RA_Mirror.py) and:
  1. reports the as-loaded focus + magnification + FOV readout   (flag 1: "Defocus on launched")
  2. replays the exact popup solve the recording captured        (flag 3: 54x54 -> 58.8x58.8)
       fov_solve(object, thickness, 54, 54) + object split near=50 + image split far=30

Run: .devenv/state/venv/bin/python bugs/diag_az85_ra_fov_solve.py
"""
from __future__ import annotations

import contextlib
import io
import types
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.services.quick_estimation import QuickEstimationService

ROOT = Path(__file__).resolve().parent.parent
SCENE = ROOT / "attachment" / "machine_vision_AZ85_RA_Mirror.py"


def _quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*a, **k)


def load_scene():
    info = _quiet(_load_python_data, SCENE)
    rows = [KrakenLayoutEditor._row_from_layout_item(it) for it in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    ed = _quiet(_snapshot_editor, rows, info.get("settings", {}) or {})
    ed.tk = object()
    ed.current_layout_file = SCENE
    for a in (
        "imported_lens_step_path",
        "imported_optical_step_path",
        "imported_led_step_path",
        "imported_camera_step_path",
    ):
        if not hasattr(ed, a):
            setattr(ed, a, None)
    _quiet(ed._normalize_special_rows)
    return ed


def qe_of(editor):
    return QuickEstimationService(
        types.SimpleNamespace(
            editor=editor,
            quick_estimation_var=types.SimpleNamespace(get=lambda: True),
        )
    )


def dump(editor, qe, tag):
    print(f"\n{'='*100}\n### {tag}\n{'='*100}")
    print(f"{'row':>3} {'surface':<10} {'name':<42} {'thick':>11} {'diam':>9} {'glass':<5} desp")
    for i, r in enumerate(editor.rows):
        desp = (
            round(float(getattr(r, "desp_x", 0.0) or 0.0), 3),
            round(float(getattr(r, "desp_y", 0.0) or 0.0), 3),
            round(float(getattr(r, "desp_z", 0.0) or 0.0), 3),
        )
        print(
            f"{i:>3} {str(r.surface):<10} {str(r.name)[:42]:<42} "
            f"{float(r.thickness):>11.4f} {float(r.diameter):>9.4f} {str(r.glass):<5} {desp}"
        )

    ot = _quiet(editor._paraxial_total_object_gap)
    it = _quiet(editor._paraxial_total_image_gap)
    print(f"\n  _paraxial_total_object_gap -> total={ot[0]:.4f}  first_lens_row={ot[1]}")
    print(f"  _paraxial_total_image_gap  -> total={it[0]:.4f}  last_src_row={it[1]}")

    mag = _quiet(editor._current_finite_paraxial_magnification)
    print(f"  _current_finite_paraxial_magnification = {mag}")

    st = _quiet(qe.current_state)
    print(f"  QE state: fov_full={st.get('fov_full')} fov_semi={st.get('fov_semi')} "
          f"efl={st.get('efl')} wd={st.get('working_distance')}")
    print(f"  sensor_active_dimensions = {_quiet(qe.sensor_active_dimensions)}")
    print(f"  object_fov_dimensions    = {_quiet(qe.object_fov_dimensions)}   <-- the FOV readout")

    # --- focus error: where does the paraxial model say the image lands vs where the sensor is?
    try:
        total_img, _last, ref_rows = _quiet(editor._paraxial_total_image_gap, editor.rows)
        a, b, c, d, effl, ppa, ppp = _quiet(editor._exact_paraxial_solution_for_rows, ref_rows)
        obj_d, _fs = _quiet(editor._paraxial_total_object_gap, editor.rows)
        predicted = _quiet(
            editor._compute_image_gap_from_paraxial_solution,
            a, b, c, d, obj_d, _quiet(editor._current_object_mode),
        )
        print(f"  WHOLE-SYSTEM first order: efl={effl:.4f} ppa={ppa:.4f} ppp={ppp:.4f}")
        print(f"  predicted image gap = {predicted:.4f}   actual image gap = {total_img:.4f}   "
              f"DEFOCUS = {predicted - total_img:+.4f} mm")
    except Exception as exc:  # noqa: BLE001
        print(f"  whole-system focus probe failed: {exc!r}")

    # --- the LENS-ONLY first order the folded solver uses
    folded = _quiet(editor._folded_conjugate_gaps_for_magnification, 1.0)
    if folded:
        print(f"  folded helper @|m|=1.0: {{k: round(v,4)}} -> "
              f"{ {k: (round(v, 4) if isinstance(v, float) else v) for k, v in folded.items()} }")
    osplit = _quiet(editor._folded_object_conjugate_split)
    isplit = _quiet(editor._folded_image_conjugate_split)
    print(f"  object split: { {k: (round(v,4) if isinstance(v,float) else v) for k,v in (osplit or {}).items()} }")
    print(f"  image  split: { {k: (round(v,4) if isinstance(v,float) else v) for k,v in (isplit or {}).items()} }")
    return mag


def main() -> int:
    editor = load_scene()
    qe = qe_of(editor)

    dump(editor, qe, "AS LOADED (flag 1: 'Defocus on launched')")

    # ---- replay the recorded popup solve exactly ------------------------------------------- #
    # recording event 66:
    #   fov_solve {plane: object, mode: thickness, width: 54, height: 54,
    #              segment: [near, 50], image_segment: [far, 30]}
    sensor_wh = _quiet(qe.sensor_active_dimensions)
    aspect = tuple(sensor_wh) if sensor_wh else None
    print(f"\n\n>>> fov_solve('object','thickness',54,54, aspect={aspect})")
    ok, msg = _quiet(qe.fov_solve, "object", "thickness", 54.0, 54.0, aspect)
    print(f"    -> ok={ok} msg={msg}")
    dump(editor, qe, "AFTER fov_solve(54x54)")

    print("\n\n>>> _apply_folded_object_split('near', 50.0)")
    ok2, msg2 = _quiet(editor._apply_folded_object_split, "near", 50.0)
    print(f"    -> ok={ok2} msg={msg2}")
    dump(editor, qe, "AFTER object split near=50")

    print("\n\n>>> _apply_folded_image_split('far', 30.0)")
    ok3, msg3 = _quiet(editor._apply_folded_image_split, "far", 30.0)
    print(f"    -> ok={ok3} msg={msg3}")
    mag = dump(editor, qe, "AFTER image split far=30  (flag 3: user sees FOV 58.8x58.8 + defocus)")

    fov = _quiet(qe.object_fov_dimensions)
    print(f"\n\nRESULT: requested FOV 54.0 x 54.0 mm -> readout "
          f"{None if fov is None else f'{fov[0]:.4g} x {fov[1]:.4g}'} mm  (|m|={abs(mag) if mag else None})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
