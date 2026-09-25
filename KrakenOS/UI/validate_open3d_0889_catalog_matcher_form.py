"""Display-free guard: the Camera + Lens Matcher form and `RowForm.read_only` (bugs/0889,
docs/design_qt_migration.md phase 3).

bugs/0634: enter the requirement and the matcher lists every registered camera x catalog lens
combination, passing ones first, with the reasons the others fail.

It REPORTS -- there is nothing to write back -- so `RowForm.read_only` drops Validate and Apply
and renames Cancel to Close. What it keeps is a VERB: the first Match scrapes the lens datasheets
and takes 10-20 s, which is not something to do on every keystroke, so it is a `FormAction` and
not a rebuild-on-change report.

  B  the builder: five inputs prefilled from the scene, one verb, an empty list
  R  Match refuses until the FOV and the resolution are there
  M  Match fills the list and counts what passed
  S  selecting a combination explains it -- why it passes, or every reason it does not
  T  the REAL Tk dialog shows Match and Close, and NO Validate/Apply
  Q  so does the Qt dialog
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    dialog = window.action_manager["catalog_matcher"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    has_apply = dialog.apply_button is not None or dialog.validate_button is not None
    labels = [dialog.buttons.buttons()[index].text()
              for index in range(len(dialog.buttons.buttons()))]
    empty = dialog.records_view.rowCount()
    dialog.widgets["fov_w"].setText("20")
    dialog.widgets["fov_h"].setText("20")
    dialog.widgets["resolution_um"].setText("10")
    dialog.run_action(next(action for action in dialog.form.actions if action.key == "match"))
    app.processEvents()
    matched = dialog.records_view.rowCount()
    dialog.records_view.selectRow(0)
    app.processEvents()
    detail = dialog.summary.text()
    dialog.close()
    app.processEvents()

    window.close()
    return [has_apply, labels, empty, matched, detail[:40]]


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
        "from KrakenOS.UI.validate_open3d_0889_catalog_matcher_form import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks(), default=str))\n"
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


def run_checks() -> tuple[bool, list[str]]:
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_catalog_matcher_form
    from KrakenOS.UI.row_forms.catalog_matcher import COLUMNS

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)

        form = build_catalog_matcher_form(editor)
        keys = [field.key for field in form.fields]
        ok(form.read_only and len(keys) == 5 and keys[0] == "fov_w"
           and [action.label for action in form.actions] == ["Match"]
           and tuple(form.records.columns) == COLUMNS
           and form.records.rows(form) == ()
           and float(form.values["fov_w"]) > 0.0,
           f"B: five inputs, one verb and an empty {len(COLUMNS)}-column list; the FOV came "
           f"prefilled from the scene ({form.values['fov_w']})")

        match = form.actions[0]
        refusals = []
        for values in ({"fov_w": "20", "fov_h": "", "resolution_um": "10"},
                       {"fov_w": "20", "fov_h": "20", "resolution_um": ""},
                       {"fov_w": "-4", "fov_h": "20", "resolution_um": "10"}):
            form.values.update(values)
            try:
                match.run(form, None)
                refusals.append(("no refusal", values))
            except FormRefused as exc:
                refusals.append(str(exc))
        ok(all(isinstance(item, str) and item.startswith("Enter a positive FOV")
               for item in refusals),
           f"R: a missing height, a missing resolution and a negative width each refuse with "
           f"the model's own message ({refusals[0][:44]!r})")

        form.values.update({"fov_w": "20", "fov_h": "20", "resolution_um": "10"})
        message = match.run(form, None)
        rows = form.records.rows(form)
        results = form.state["results"]
        passing = sum(1 for result in results if result.passes)
        ok(rows and len(rows) == len(results) and len(rows[0]) == len(COLUMNS)
           and f"{passing} of {len(results)} combinations match" in message
           and any(row[-1] == "match" for row in rows),
           f"M: Match listed {len(rows)} combinations, {passing} of them passing "
           f"({message[:50]!r})")

        detail = form.records.select(form, 0)
        first = results[0]
        ok(detail.startswith("MATCH " if first.passes else "NO ")
           and str(first.camera) in detail and str(first.lens) in detail,
           f"S: selecting a combination explains it ({detail[:64]!r})")

        before = {str(child) for child in editor.root.winfo_children()}
        editor.open_camera_lens_matcher()
        windows = [child for child in editor.root.winfo_children()
                   if str(child) not in before and child.winfo_class() == "Toplevel"]
        buttons, trees = [], 0
        if windows:
            def walk(widget):
                nonlocal trees
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button):
                        buttons.append(str(child.cget("text")))
                    elif isinstance(child, ttk.Treeview):
                        trees += 1
                    walk(child)

            walk(windows[-1])
            windows[-1].destroy()
        ok(windows and buttons == ["Match", "Close"] and trees == 1,
           f"T: the REAL Tk dialog shows {buttons} over its result list -- read_only dropped "
           f"Validate and Apply and renamed Cancel")
    finally:
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    has_apply, labels, empty, matched, detail = payload
    ok(not has_apply and "Match" in labels and any("Close" in label for label in labels)
       and int(empty) == 0 and int(matched) > 0 and str(detail),
       f"Q: the Qt dialog offered {labels} with no Validate/Apply, and Match filled "
       f"{matched} rows from an empty list")

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
