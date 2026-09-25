"""Display-free guard: the paraxial matrix and Gaussian beam reports render their builders
(bugs/0896, docs/design_qt_migration.md phase 4).

The last report-family panel that still drew its own tables. Both builders already existed --
`reports/paraxial_matrix.py` and `reports/gaussian_beam.py`, which Qt has rendered since 0859
and 0864 -- but the Tk dialogs kept 211 lines of layout over them, and the Gaussian one held a
verb the report could not say: **Use Cavity Eigenmode**, which solves the resonator's own mode
and WRITES IT BACK into the waist and offset boxes before recomputing.

`ReportUpdate` is that verb as data -- a status line plus the control values to adopt -- so the
arithmetic stays in the model and each toolkit has one job: put these values in those widgets.
Qt now has the button it never had.

  L  the panel is two `ReportWindow`s; the calculator and the three solve prompts stay its own
  M  the REAL Tk matrix window draws the builder's grid, cell for cell, and exports it
  G  the Gaussian window's four inputs are the builder's own, and typing one rebuilds through it
  C  on a STABLE cavity the verb returns the model's own w0 and q, and the view adopts them and
     rebuilds; on this scene, which is not a resonator, nothing is written back and g is named
  Q  the Qt dialog offers the same verb and adopts an update the same way
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

def adopted_value(shown, wanted) -> bool:
    """The control holds `wanted`, as the BUILDER echoes it back.

    A verb's update is adopted and the report is then rebuilt, and the rebuild re-renders every
    control from the fresh report -- which formats to 6 significant figures. So the box ends up
    holding 0.123132 where the eigenmode said 0.12313222: the same number, said by the model.
    """
    try:
        shown_value, wanted_value = float(shown), float(wanted)
    except (TypeError, ValueError):
        return str(shown) == str(wanted)
    return abs(shown_value - wanted_value) <= 1e-6 * max(1.0, abs(wanted_value))


RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")
#: a two-mirror resonator that IS stable: d = f = 100 mm, so g = -0.5
CAVITY_D = 100.0
CAVITY_F = 100.0


def cavity_owner(editor):
    """`editor`, but its paraxial matrices are a stable two-mirror round trip.

    A stand-in, because no layout in the tree is a resonator: everything else -- the wavelength,
    the default beam, `short_error_message` -- is the real editor's (bugs/0892 did the same for
    the splitter forms).
    """
    import numpy as np

    propagate = np.array([[1.0, CAVITY_D], [0.0, 1.0]])
    mirror = np.array([[1.0, 0.0], [-1.0 / CAVITY_F, 1.0]])
    round_trip = mirror @ propagate @ mirror @ propagate

    class System:
        def ParaxMatrices(self, _wavelength):
            return round_trip

    class Owner:
        def __getattr__(self, name):
            return getattr(editor, name)

        def build_system(self, force_rebuild=False):
            return System()

    return Owner()


def qt_runtime_checks() -> list[list]:
    """The Qt half: the verb exists, and Qt adopts a `ReportUpdate` as the Tk view does."""
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.dialogs.report_dialog import ReportDialog
    from KrakenOS.UI.reports import ReportAction, ReportUpdate
    from KrakenOS.UI.reports.gaussian_beam import (build_gaussian_beam_report,
                                                   cavity_eigenmode_update)
    from KrakenOS.UI.uihost import host_of
    from KrakenOS.UI.validate_open3d_0896_paraxial_reports_on_report_view import adopted_value

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor

    dialog = window.action_manager["gaussian_beam"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    rows: list[list] = []
    labels = list(dialog.action_buttons)

    expected = cavity_eigenmode_update(cavity_owner(editor), dialog.control_values())
    rebuilt: list = []

    def rebuild(**values):
        rebuilt.append(dict(values))
        return build_gaussian_beam_report(editor, **values)

    # the same dialog, given the stand-in's verb: what Qt does with an update, not what the
    # eigenmode of THIS scene happens to be
    probe = ReportDialog(
        build_gaussian_beam_report(editor), parent=window, host=host_of(window), rebuild=rebuild)
    probe.report = probe.report.__class__(
        **{**probe.report.__dict__,
           "actions": (ReportAction("Use Cavity Eigenmode",
                                    lambda controls: expected, needs_controls=True),)})
    status = probe.run_action(probe.report.actions[0])
    adopted = probe.control_values()
    rows.append(["Q", "Use Cavity Eigenmode" in labels and bool(expected.controls)
                 and all(adopted_value(adopted.get(key), value)
                         for key, value in expected.controls.items())
                 and bool(rebuilt),
                 f"the Qt dialog offers {labels} and adopted the update's "
                 f"{expected.controls} then rebuilt ({status[:48]!r})"])
    probe.close()
    dialog.close()
    window.close()
    return rows


def _run_qt_subprocess() -> tuple[str, list[list]]:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the shell needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0896_paraxial_reports_on_report_view import "
        "qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Q", False, "the Qt subprocess timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Q", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Q", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.filedialog as tk_filedialog
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels import main_paraxial_analysis_dialogs
    from KrakenOS.UI.reports.gaussian_beam import (build_gaussian_beam_report,
                                                   cavity_eigenmode_update, default_inputs)

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    panel_source = inspect.getsource(main_paraxial_analysis_dialogs)
    ok(panel_source.count("ReportWindow(") == 2 and "ttk.Treeview(" not in panel_source
       and "Paraxial Calculator" in panel_source and "Best Image Solve" in panel_source,
       f"L: the two reports are ReportWindows and the panel draws no table of its own "
       f"({len(panel_source.splitlines())} lines), while the calculator and the three solve "
       f"prompts stay its own pages")

    saved = (tk_messagebox.showinfo, tk_messagebox.showerror, tk_filedialog.asksaveasfilename)
    boxes: list = []
    tk_messagebox.showinfo = lambda *a, **k: boxes.append(a) or "ok"
    tk_messagebox.showerror = lambda *a, **k: boxes.append(a) or "ok"
    out = Path("/tmp/claude-1000")

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        panel = editor._main_paraxial_analysis_dialogs()

        # ---- M the matrix report --------------------------------------------------------
        editor.open_paraxial_matrix_report()
        matrix = panel._matrix_window
        drawn = [[str(value) for value in matrix.table.item(iid, "values")]
                 for iid in matrix.table.get_children("")]
        expected = [[matrix.report.cell(row, column)
                     for column in range(len(matrix.report.columns))]
                    for row in range(len(matrix.report.rows))]
        csv_path = out / "guard_0896_matrix.csv"
        tk_filedialog.asksaveasfilename = lambda *a, **k: str(csv_path)
        matrix.export_csv()
        header = csv_path.read_text(encoding="utf-8").splitlines()[0] if csv_path.exists() else ""
        ok(drawn == expected and len(expected) > 10
           and header.split(",") == list(matrix.report.keys) and not boxes,
           f"M: the matrix window drew the builder's {len(expected)}x{len(expected[0])} grid and "
           f"exported it under its own {len(matrix.report.keys)} keys"
           if drawn == expected else
           f"M: drew {len(drawn)} rows for a builder grid of {len(expected)}")

        # ---- G the Gaussian inputs ------------------------------------------------------
        editor.open_gaussian_beam_report()
        gaussian = panel._gaussian_window
        defaults = default_inputs(editor)
        shown = gaussian.control_values()
        gaussian.controls["waist"].set("2.5")
        gaussian.refresh()
        typed = build_gaussian_beam_report(editor, **gaussian.control_values())
        redrawn = [[str(value) for value in gaussian.table.item(iid, "values")]
                   for iid in gaussian.table.get_children("")]
        expected_typed = [[typed.cell(row, column) for column in range(len(typed.columns))]
                          for row in range(len(typed.rows))]
        ok(list(shown) == ["wavelength", "waist", "offset", "m2"]
           and shown["wavelength"] == f"{defaults['wavelength']:.6g}"
           and redrawn == expected_typed and "w0=2.5" in gaussian.summary_var.get(),
           f"G: the four inputs are the builder's own ({shown}) and typing waist=2.5 rebuilt the "
           f"{len(expected_typed)} rows through it"
           if redrawn == expected_typed else
           f"G: after typing, drew {len(redrawn)} rows for {len(expected_typed)}")

        # ---- C the cavity verb ----------------------------------------------------------
        unstable = cavity_eigenmode_update(editor, gaussian.control_values())
        stable = cavity_eigenmode_update(cavity_owner(editor), gaussian.control_values())
        before = gaussian.control_values()
        gaussian.run_action(gaussian.report.actions[0])
        after_unstable = gaussian.control_values()

        action = gaussian.report.actions[0].__class__(
            "Use Cavity Eigenmode", lambda controls: stable, needs_controls=True)
        status = gaussian.run_action(action)
        adopted = gaussian.control_values()
        ok(not unstable.controls and "g=" in unstable.status and after_unstable == before
           and stable.controls
           and all(adopted_value(adopted[key], value)
                   for key, value in stable.controls.items())
           and adopted != before and "w0=" in gaussian.summary_var.get(),
           f"C: this scene is no resonator, so nothing was written back "
           f"({unstable.status[:52]!r}); a stable d={CAVITY_D:g}/f={CAVITY_F:g} cavity gave "
           f"{stable.controls}, and the view adopted them and rebuilt"
           if stable.controls and after_unstable == before else
           f"C: unstable wrote {unstable.controls} (controls {before} -> {after_unstable}), "
           f"stable gave {stable.controls} -> {adopted}")
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror, tk_filedialog.asksaveasfilename = saved
        editor.destroy()

    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {qt_rows[0][2]}")
    else:
        for name, passed, detail in qt_rows:
            ok(passed, f"{name}: {detail}")

    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
