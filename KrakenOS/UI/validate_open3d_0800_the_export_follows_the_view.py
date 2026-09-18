"""bugs/0800 -- the export draws what the VIEW shows, not what the model holds.

Two reports, one contract:

* "the surrogate is hidden, but the STEP output still shows the surrogate" -- hiding four
  surrogate rows in the 3D browser left all seven analytic surfaces in the file.
* "Show Rays is on, but fresh launch KrakenOS 3D won't show it, but export STEP will show. I
  turn off, export STEP won't show." -- a fast load leaves the trace DEFERRED so the view opens
  bodies-only, while the export traced rays of its own and wrote them anyway.

The hidden-row half is the bugs/0797 shape again: ``_step_export_hidden_state`` is consulted by
the mesh, edge and native-CAD collectors, but the two ANALYTIC writers read ``sdt[j]`` directly
and only ever checked the row's 2D ``Drawing`` flag.

The rays half must NOT be fixed by tracing on open: bugs/0718 made the fast-load gate
authoritative because the in-process non-sequential trace can wedge the UI on crashed geometry,
so only a deliberate Trace Now may clear it. The export follows the view instead, and the view
says out loud that rays are pending.

Display-free: a synthetic scene in a temp dir, no rendering.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import pprint
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_ROWS = [
    ("Object", "Object at 1X", 0.0, 110.0, 58.5390),
    ("Standard", "Front Optical Vertex Datum", 0.0, 28.0630, 28.0045),
    ("Thin Lens", "Blackbox Group 1", 100000.0, 1.0, 28.0045),
    ("Aperture", "Aperture Stop", 0.0, 1.0, 10.0045),
    ("Thin Lens", "Blackbox Group 2", 70.079176, 42.698468, 28.0045),
    ("Standard", "Rear Optical Vertex Datum", 0.0, 97.3644885834, 28.0045),
    ("Image", "Image / Sensor at 1X", 0.0, 0.0, 17.5161),
]


def _layout_source() -> str:
    settings = {
        "aperture_type": "EPD", "aperture_value": "10.0", "display_orientation": "YZ",
        "field_count": 3, "field_type": "Real Image Height", "field_value": 8.75,
        "object_mode": "Finite", "projection_display_mode": "Full 3D", "wavelength": 0.55,
    }
    surfaces = [
        {"surface": s, "name": n, "rc": rc, "thickness": t, "diameter": d, "glass": "AIR"}
        for s, n, rc, t, d in _ROWS
    ]
    return ('"""bugs/0800 synthetic scene."""\n\n'
            "TITLE = 'bugs 0800 probe'\n\n"
            f"SETTINGS = {pprint.pformat(settings)}\n\n"
            f"SURFACES = {pprint.pformat(surfaces)}\n")


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    from KrakenOS.UI.services import cad_step_export as cse
    from KrakenOS.UI.services import layout_import_export as lie
    from KrakenOS.UI.services import optical_solid_workflow as osw
    from KrakenOS.UI.services import three_d_scene_tools as tdst

    # ---- A: both analytic writers take the hidden set, and the callers supply it ----------
    for writer in ("_write_step_with_analytic_surfaces", "_write_step_with_cad_shapes_and_rays"):
        src = inspect.getsource(getattr(cse, writer))
        ok("hidden_rows" in src.split(") ->")[0],
           f"A: {writer} accepts hidden_rows")
        ok("if hidden_rows and j in hidden_rows" in src,
           f"A: {writer} skips a hidden row")
    export_src = inspect.getsource(lie.LayoutImportExportMixin.export_3d_step)
    ok(export_src.count("_step_export_hidden_state()[0]") >= 1
       and "hidden_rows=" in export_src,
       "A: export_3d_step passes the browser's hidden rows to the writers")

    # ---- B: bugs/0718's gate is NOT cleared by opening the view ---------------------------
    open_src = inspect.getsource(tdst.ThreeDSceneToolsMixin.open_3d_view)
    ok("_preview_trace_deferred_until_requested = False" not in open_src,
       "B: opening the 3D view does NOT clear the fast-load gate -- bugs/0718 keeps it "
       "authoritative because the in-process trace can wedge the UI on crashed geometry")
    ray_src = inspect.getsource(osw.LayoutOpticalSolidWorkflowMixin._step_export_ray_polylines)
    ok("_preview_trace_deferred_until_requested" in ray_src,
       "B: the ray export consults the same gate, so it cannot run the trace 0718 defers")

    # ---- C: end to end on a real build ----------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="kraken0800_") as tmp:
        tmpdir = Path(tmp)
        path = tmpdir / "probe.py"
        path.write_text(_layout_source(), encoding="utf-8")

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data

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
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                system = app.build_system()

            shown, _f, _t = cse._write_step_with_analytic_surfaces(
                system, app.rows, [], tmpdir / "all.step")
            ok(shown == len(_ROWS),
               f"C: with nothing hidden every row is exported ({shown})")
            hidden = frozenset({1, 2, 4, 5})
            fewer, _f, _t = cse._write_step_with_analytic_surfaces(
                system, app.rows, [], tmpdir / "hidden.step", hidden_rows=hidden)
            ok(fewer == len(_ROWS) - len(hidden),
               f"C: hiding the four surrogate rows exports {fewer}, not {shown} -- the flag's "
               "'the surrogate is hidden, but the STEP output still shows the surrogate'")

            # ---- D: rays follow the view -------------------------------------------------
            app._preview_trace_deferred_until_requested = True
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                deferred_rays = app._step_export_ray_polylines(system)
            ok(deferred_rays == [],
               f"D: while the trace is DEFERRED the export writes no rays "
               f"({len(deferred_rays)}) -- the view is bodies-only")
            app._preview_trace_deferred_until_requested = False
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                traced_rays = app._step_export_ray_polylines(system)
            ok(len(traced_rays) > 0,
               f"D: once traced, the export carries them again ({len(traced_rays)})")

            # ---- E: and the view SAYS so -- bugs/0801 made it untick the box too ----------
            class _Var:
                def __init__(self, value):
                    self._value = bool(value)

                def get(self):
                    return self._value

                def set(self, value):
                    self._value = bool(value)

            class _Insp:
                """bugs/0818 moved the rule to the painter and left `_pending_rays_note`
                delegating to `Kraken3DInspector._sync_show_rays_toggle_to_scene`, so a fake
                inspector carrying only the toggle stopped modelling the thing under test.
                Carry the REAL method, bound to the fake ([[a guard must keep up with what it
                guards]])."""

                def __init__(self, rays_on, editor=None):
                    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

                    self.show_rays_var = _Var(rays_on)
                    self.editor = editor
                    self._sync_show_rays_toggle_to_scene = (
                        Kraken3DInspector._sync_show_rays_toggle_to_scene.__get__(self, type(self))
                    )

            app._preview_trace_deferred_until_requested = True
            deferred_insp = _Insp(True, app)
            note_on = app._pending_rays_note(deferred_insp)
            ok("Trace Now" in note_on and "Show Rays is off" in note_on,
               f"E: a deferred open explains the state ({note_on.strip()[:60]}...)")
            ok(not deferred_insp.show_rays_var.get(),
               "E (bugs/0801): and the toggle is UNTICKED so it matches the bodies-only scene")
            ok(app._pending_rays_note(_Insp(False)) == "",
               "E: with Show Rays already off there is nothing to explain")
            app._preview_trace_deferred_until_requested = False
            untouched = _Insp(True)
            ok(app._pending_rays_note(untouched) == "" and untouched.show_rays_var.get(),
               "E: and a traced scene says nothing and leaves the toggle alone")
        finally:
            with contextlib.suppress(Exception):
                app.destroy()
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0800 export-follows-the-view validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
