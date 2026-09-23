"""Display-free guard: the Gaussian Beam Report, in both toolkits (bugs/0864,
docs/design_qt_migration.md phase 3).

The first report with INPUTS. Its propagation, columns, formatting and cavity eigenmode moved to
`KrakenOS/UI/reports/gaussian_beam.py`; the Tk dialog was rewired onto it and the Qt dialog
renders the same builder, with the four inputs as `ReportValue` controls.

  D  the defaults are the model's: the scene's own Gaussian source beam when it has one
  B  a value that is not a number falls back to the default instead of raising
  E  the cavity eigenmode helper answers from the model (the Tk button's own path)
  T  the REAL Tk dialog's table equals the builder's cells
  Q  the Qt dialog's table equals them too -- one SHA-256 over every cell, both toolkits
  V  typing an input rebuilds through the builder: the table becomes the builder's own report
     for that value
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")
NEW_WAIST = "2.5"


def digest(cells) -> str:
    return hashlib.sha256(
        json.dumps(cells, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def report_cells(report) -> list[list[str]]:
    return [[report.cell(r, c) for c in range(len(report.columns))]
            for r in range(len(report.rows))]


def qt_runtime_checks() -> list[list]:
    from PySide6.QtCore import Qt

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.reports.gaussian_beam import build_gaussian_beam_report

    from KrakenOS.UI.validate_open3d_0864_gaussian_beam_report import digest, report_cells

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    dialog = window.action_manager["gaussian_beam"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    model = dialog.model

    def table() -> list[list[str]]:
        return [[str(model.data(model.index(r, c), Qt.ItemDataRole.DisplayRole))
                 for c in range(model.columnCount())]
                for r in range(model.rowCount())]

    opened = table()
    controls = [(control.key, control.value) for control in dialog.report.controls]

    # type a new waist radius and commit it
    dialog.controls["waist"].setText(NEW_WAIST)
    dialog.controls["waist"].editingFinished.emit()
    app.processEvents()
    retyped = table()
    expected = report_cells(build_gaussian_beam_report(window.editor, waist=NEW_WAIST))

    out = [["opened", controls, digest(opened), [len(opened), len(opened[0]) if opened else 0]],
           ["retyped", [(c.key, c.value) for c in dialog.report.controls], digest(retyped),
            digest(expected), dialog.report.summary]]
    dialog.close()
    window.close()
    return out


def _run_qt_subprocess() -> tuple[str, object]:
    driver = (
        "import json, os, sys\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the shell needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0864_gaussian_beam_report import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", "the Qt subprocess timed out after 900 s"
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", line[len(SKIP_MARK):]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", f"exit {proc.returncode}; " + " | ".join(tail)


def _tk_table(editor):
    """Open the REAL Tk dialog and read its Treeview back."""
    import tkinter.ttk as ttk

    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_gaussian_beam_report()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None
    window = windows[-1]
    try:
        trees: list = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Treeview):
                    trees.append(child)
                walk(child)

        walk(window)
        if not trees:
            return None
        tree = trees[0]
        return [[str(value) for value in tree.item(item, "values")]
                for item in tree.get_children("")]
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.reports.gaussian_beam import (build_gaussian_beam_report, default_inputs,
                                                   gaussian_cavity_eigenmode)

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    saved = (tk_messagebox.showinfo, tk_messagebox.showerror)
    boxes: list = []
    tk_messagebox.showinfo = lambda *a, **k: boxes.append(a) or "ok"
    tk_messagebox.showerror = lambda *a, **k: boxes.append(a) or "ok"

    editor = KrakenLayoutEditor(headless=True)
    tk_digest = None
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)

        defaults = default_inputs(editor)
        report = build_gaussian_beam_report(editor)
        values = {control.key: control.value for control in report.controls}
        ok(set(values) == {"wavelength", "waist", "offset", "m2"}
           and float(values["wavelength"]) == float(editor._current_wavelength())
           and float(values["waist"]) == defaults["waist"] and report.rows,
           f"D: the four inputs default to the model's own ({values}) over "
           f"{len(report.rows)} propagation steps")

        nonsense = build_gaussian_beam_report(editor, waist="not a number")
        ok(report_cells(nonsense) == report_cells(report),
           "B: an input that is not a number falls back to the default instead of raising")

        eigenmode = gaussian_cavity_eigenmode(editor, values["wavelength"], values["m2"])
        ok(hasattr(eigenmode, "stable") and hasattr(eigenmode, "stability_parameter"),
           f"E: the cavity eigenmode helper answered from the model "
           f"(stable={bool(eigenmode.stable)}, g={float(eigenmode.stability_parameter):.6g})")

        tk_cells = _tk_table(editor)
        tk_digest = digest(tk_cells) if tk_cells is not None else None
        ok(tk_cells is not None and digest(tk_cells) == digest(report_cells(report))
           and not boxes,
           f"T: the REAL Tk dialog shows the builder's {len(tk_cells or [])} rows exactly "
           f"({(tk_digest or '')[:16]}...)" + (f" -- message boxes {boxes}" if boxes else ""))
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror = saved
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q/V: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    opened, retyped = payload
    ok(opened[2] == tk_digest and opened[3][0] > 0,
       f"Q: the Qt dialog shows the same {opened[3][0]}x{opened[3][1]} table as Tk -- one "
       f"SHA-256 over every cell ({opened[2][:16]}...)")

    retyped_controls = dict(retyped[1])
    ok(retyped[2] == retyped[3] and retyped[2] != opened[2]
       and retyped_controls.get("waist") == NEW_WAIST
       and f"input w0={float(NEW_WAIST):.6g} mm" in retyped[4],
       f"V: typing waist={NEW_WAIST} rebuilt the table to the builder's own report for that "
       f"value, and the summary followed ({retyped[4][:64]!r}...)")

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
