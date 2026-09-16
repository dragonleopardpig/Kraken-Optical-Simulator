"""bugs/0796 -- the aperture belongs to the lens, not to the scene.

flag_20260916_125457, "I swapped the lens, seems the rays look the same": the rows swapped, the
object moved to the 4x lens's 65 mm working distance and the banner read 4.16x -- and the launch
stayed the 0.330 mm pencil bugs/0795 had just fixed.

bugs/0795 removed the pencil from the CLAMP. This one removes it from the DECLARATION. A swap
preserves pose, object, camera, field and source because the user chose them -- they describe the
scene. An aperture describes the LENS: ``FNO`` resolves against the system EFL and ``EPD`` is a
pupil diameter in millimetres, so the outgoing lens's number carries no meaning onto the incoming
glass. The SPO TCL4.0X declares ``STOP 15.0761``; the scene kept ``FNO 12.5``, which against that
build's EQUIVALENT EFL (bugs/0792) is a 0.824 mm entrance pupil.

Display-free: a synthetic scene in a temp dir for the contract, the real swap callback for the
end-to-end, no rendering.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import pprint
import tempfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPO = PROJECT_ROOT / "attachment/Information/RD-80000/Drawings/SPO TCL4.0X-65DI-5M"

_ROWS = [
    ("Object", "Object", 0.0, 65.0, 2.75),
    ("Standard", "Front Optical Vertex Datum", 0.0, 5.0, 26.0761),
    ("Thin Lens", "Blackbox Group 1", 47.112667, 47.112667, 26.0761),
    ("Aperture", "Aperture Stop", 0.0, 85.387333, 15.0761),
    ("Thin Lens", "Blackbox Group 2", -23.882528, 5.0, 26.0761),
    ("Standard", "Rear Optical Vertex Datum", 0.0, 17.526, 26.0761),
    ("Image", "Image / Sensor", 0.0, 0.0, 11.0),
]


def _layout_source() -> str:
    settings = {
        "aperture_type": "FNO",
        "aperture_value": "12.5",
        "display_orientation": "YZ",
        "field_count": 3,
        "field_type": "Real Image Height",
        "field_value": 5.5,
        "object_mode": "Finite",
        "projection_display_mode": "Full 3D",
        "wavelength": 0.55,
    }
    surfaces = [
        {"surface": s, "name": n, "rc": rc, "thickness": t, "diameter": d, "glass": "AIR"}
        for s, n, rc, t, d in _ROWS
    ]
    return (
        '"""bugs/0796 synthetic swap scene."""\n\n'
        "TITLE = 'bugs 0796 probe'\n\n"
        f"SETTINGS = {pprint.pformat(settings)}\n\n"
        f"SURFACES = {pprint.pformat(surfaces)}\n"
    )


def _axial_front_radius(app) -> float | None:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        app._preview_trace_deferred_until_requested = False
        _s, _r, bundle = app._build_preview_system_rays_bundle(trace_rays=True)
    axial = [
        np.asarray(p.points_world, float)
        for p in (getattr(bundle, "ray_paths", []) or [])
        if str(getattr(p, "termination_reason", "")) in ("image", "target_termination")
    ]
    axial = [q for q in axial if np.hypot(q[0][0], q[0][1]) < 0.01 and len(q) > 1]
    if not axial:
        return None
    return max(float(np.hypot(q[1][0], q[1][1])) for q in axial)


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: the swap wires it, and says so -------------------------------------------------
    from KrakenOS.UI.services import layout_table_workbench as ltw

    source = inspect.getsource(ltw.LayoutTableWorkbenchMixin.swap_imaging_lens_from_folder)
    ok("_apply_swapped_lens_aperture" in source,
       "A: the swap adopts the incoming lens's aperture declaration")
    ok(source.index("_apply_swapped_lens_aperture") < source.index("_swap_auto_refocus_to_best_focus"),
       "A: before the auto-refocus, so best focus is found on the cone the lens actually passes")
    ok("aperture_note" in source.split("message = ")[1][:400],
       "A: and the status message SAYS so rather than changing it silently")

    with tempfile.TemporaryDirectory(prefix="kraken0796_") as tmp:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data

        path = Path(tmp) / "probe_swap.py"
        path.write_text(_layout_source(), encoding="utf-8")
        app = KrakenLayoutEditor(headless=True)
        app._prompt_for_missing_cad_assets = lambda: None
        try:
            info = _load_python_data(path)
            app._reset_complete_layout_runtime_state(close_viewers=True)
            app.current_layout_file = path.resolve()
            app.rows = app._normalized_rows_copy(
                [app._row_from_layout_item(i) for i in info["surfaces"]])
            app._auto_assign_missing_elements(app.rows)
            app._apply_layout_settings(info.get("settings", {}))
            app._normalize_special_rows()
            app._sync_table()
            app._select_table_row(0)
            app._invalidate_preview_scene_trace()
            app.auto_save_plot_var.set(False)
            app.update_idletasks()

            # ---- B: the flagged state, measured ----------------------------------------
            before = _axial_front_radius(app)
            ok(before is not None and before < 0.5,
               f"B: declared FNO 12.5, the scene launches a {before:.3f} mm pencil -- an "
               "f-number against a conjugate-constrained build's EQUIVALENT EFL (bugs/0792)")

            # ---- C: the helper's own contract ------------------------------------------
            note = app._apply_swapped_lens_aperture(
                {"aperture_type": "STOP", "aperture_value": "15.0761"})
            ok(bool(note) and "15.0761" in note,
               f"C: adopting a new declaration returns a note ({note.strip()[:70]}...)")
            ok(app.aperture_type_var.get().upper() == "STOP"
               and abs(float(app.aperture_value_var.get()) - 15.0761) < 1e-9,
               f"C: and sets it ({app.aperture_type_var.get()} {app.aperture_value_var.get()})")
            ok(app._apply_swapped_lens_aperture(
                   {"aperture_type": "STOP", "aperture_value": "15.0761"}) == "",
               "C: re-adopting the SAME declaration is silent -- no note for a non-change")
            for junk in ({}, {"aperture_type": "BANANA", "aperture_value": "1"},
                         {"aperture_type": "EPD", "aperture_value": "0"},
                         {"aperture_type": "EPD", "aperture_value": "abc"}):
                if app._apply_swapped_lens_aperture(junk) != "":
                    ok(False, f"C: a declaration that says nothing must be ignored ({junk})")
                    break
            else:
                ok(app.aperture_type_var.get().upper() == "STOP",
                   "C: a missing or unusable declaration leaves the scene's aperture alone")

            after = _axial_front_radius(app)
            ok(after is not None and after > 8.0,
               f"C: with the lens's own STOP the same scene launches {after:.3f} mm "
               f"({after / before:.0f}x the pencil) -- the cone bugs/0795 measured")
        finally:
            with contextlib.suppress(Exception):
                app.destroy()

        # ---- D: end to end, through the real swap callback ------------------------------
        if SPO.is_dir():
            app = KrakenLayoutEditor(headless=True)
            app._prompt_for_missing_cad_assets = lambda: None
            try:
                info = _load_python_data(path)
                app._reset_complete_layout_runtime_state(close_viewers=True)
                app.current_layout_file = path.resolve()
                app.rows = app._normalized_rows_copy(
                    [app._row_from_layout_item(i) for i in info["surfaces"]])
                app._auto_assign_missing_elements(app.rows)
                app._apply_layout_settings(info.get("settings", {}))
                app._normalize_special_rows()
                app._sync_table()
                app._select_table_row(0)
                app._invalidate_preview_scene_trace()
                app.auto_save_plot_var.set(False)
                app.update_idletasks()
                ok(app._current_aperture_type_label().upper() == "FNO",
                   "D: the scene starts on the outgoing lens's f-number")
                with contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    model = app.swap_imaging_lens_from_folder(folder=str(SPO), refresh=False)
                ok(model is not None and str(model.aperture_type).upper() == "STOP",
                   "D: the imported lens declares STOP")
                ok(app._current_aperture_type_label().upper() == "STOP",
                   f"D: and the SCENE now declares it too "
                   f"({app._current_aperture_type_label()} {app.aperture_value_var.get()})")
                swapped = _axial_front_radius(app)
                ok(swapped is not None and swapped > 8.0,
                   f"D: the swapped scene launches {swapped:.3f} mm at the front datum -- "
                   "the flag traced 0.330")
                ok("Aperture set to this lens's own" in str(app.status_var.get()),
                   "D: and the swap's own message reports the change")
            finally:
                with contextlib.suppress(Exception):
                    app.destroy()
        else:
            notes.append("SKIP: D: the SPO folder is not in this checkout")

    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0796 aperture-belongs-to-the-lens validation "
          + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
