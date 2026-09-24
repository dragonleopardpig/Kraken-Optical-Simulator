"""Display-free guard: the Advanced Surface row form (bugs/0873,
docs/design_qt_migration.md phase 3).

Every KrakenOS surface attribute the main table does not show, in TABS: the shape parameters with
the conic-k optimisation switch, one tab per attribute group, and the custom sag/UDA pair. The
framework needed three more properties for it -- `group` (a tab), `kind="bool"` (a checkbox) and
`enabled` (a field the model will not take edits to).

  G  the form is laid out in tabs, and every field belongs to one
  L  a value the literal reader cannot read back is shown but LOCKED, so a round trip can never
     mangle it; shape parameters are locked on Object/Image rows
  K  the conic-k switch is enabled only where the variable registry supports it, and its bounds
     are refused when they are not two increasing numbers
  E  an override this editor cannot read as a literal is KEPT AS A STRING (measured: the parser
     never raises, because an attribute may legitimately be a string), while a shape value that
     is not a number is refused
  A  apply writes the shape values, the overrides, ExtraData and UDA, and removes an override
     whose box was emptied
  T  the REAL Tk dialog opens with the same tabs and values
  Q  the Qt form lays them out in a QTabWidget, locks the same fields, and applies the same
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
ROW = 9


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor

    window.rows_view.selectRow(ROW)
    app.processEvents()
    dialog = window.action_manager["advanced_surface"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    form = dialog.form

    tabs = [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())] \
        if dialog.tabs is not None else []
    disabled = sorted(key for key, widget in dialog.widgets.items() if not widget.isEnabled())
    kinds = {key: type(widget).__name__ for key, widget in dialog.widgets.items()}

    before_k = float(editor.rows[ROW].k)
    dialog.widgets["k"].setText("-0.75")
    errors = list(dialog.validate())
    applied = dialog.apply_to_row()
    app.processEvents()

    expected_locked = sorted(field.key for field in form.fields if not field.enabled)
    window.close()
    return [tabs, disabled, kinds.get("optimize_k"), kinds.get("k"), errors,
            bool(applied), before_k, float(editor.rows[ROW].k), len(form.fields),
            expected_locked]


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
        "from KrakenOS.UI.validate_open3d_0873_advanced_surface_row_form import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks(), default=str))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", ("the Qt subprocess timed out after 900 s -- a modal dialog with no one "
                         "to close it is the usual cause")
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", line[len(SKIP_MARK):]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", f"exit {proc.returncode}; " + " | ".join(tail)


def _tk_tabs(editor, row_index):
    """Open the REAL Tk dialog and read its notebook tabs and bound values back."""
    import tkinter.ttk as ttk

    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_advanced_surface_editor(row_index)
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None, None
    window = windows[-1]
    try:
        notebooks: list = []
        shown: list[str] = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Notebook):
                    notebooks.append(child)
                try:
                    name = str(child.cget("textvariable"))
                except Exception:
                    name = ""
                if name:
                    try:
                        shown.append(str(window.getvar(name)))
                    except Exception:
                        pass
                walk(child)

        walk(window)
        tabs = [notebooks[0].tab(index, "text")
                for index in range(len(notebooks[0].tabs()))] if notebooks else []
        return tabs, shown
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_advanced_surface_form
    from KrakenOS.UI.row_forms.advanced_surface import BOUNDS_KEY, OPTIMIZE_KEY, SHAPE_TAB

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

    form_groups: tuple = ()
    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        form = build_advanced_surface_form(editor, ROW)
        form_groups = form.groups

        ungrouped = [field.key for field in form.fields if not field.group]
        ok(len(form.groups) >= 4 and form.groups[0] == SHAPE_TAB and not ungrouped
           and sum(len(form.fields_in(group)) for group in form.groups) == len(form.fields),
           f"G: {len(form.fields)} fields across {len(form.groups)} tabs "
           f"({', '.join(form.groups[:4])}...), none of them loose")

        image_row = next((index for index, row in enumerate(editor.rows)
                          if row.surface == "Image"), None)
        locked_shape = []
        if image_row is not None:
            image_form = build_advanced_surface_form(editor, image_row)
            locked_shape = [field.key for field in image_form.fields_in(SHAPE_TAB)
                            if not field.enabled]
        ok(image_row is not None and "k" in locked_shape,
           f"L: the shape parameters are locked on the Image row ({locked_shape[:3]})")

        k_field = form.field(OPTIMIZE_KEY)
        bounds_field = form.field(BOUNDS_KEY)
        supported = bool(form.state.get("k_supported"))
        ok(k_field is not None and bounds_field is not None
           and k_field.enabled == supported and bounds_field.enabled == supported,
           f"K1: the conic-k switch and its bounds follow the variable registry "
           f"(supported={supported} on S{ROW})")

        conic = next((index for index, row in enumerate(editor.rows)
                      if build_advanced_surface_form(editor, index).state.get("k_supported")),
                     None)
        bounds_errors = []
        if conic is not None:
            conic_form = build_advanced_surface_form(editor, conic)
            for text, expected in (("-2", "two numbers"), ("0, -2", "increasing")):
                errors = conic_form.validate(dict(conic_form.values,
                                                  **{OPTIMIZE_KEY: "true", BOUNDS_KEY: text}))
                if not errors or expected not in errors[0]:
                    bounds_errors.append((text, errors[:1]))
        ok(conic is None or not bounds_errors,
           f"K2: bounds that are not two increasing numbers are refused"
           + (f" -- wrong: {bounds_errors}" if bounds_errors else
              f" (checked on S{conic})" if conic is not None else " (no conic row in this scene)"))

        # Measured, not assumed: _parse_literal_editor_text NEVER raises -- text it cannot read
        # as a literal is kept as a STRING, because a KrakenOS attribute may legitimately be one.
        # So a broken-looking override is stored, not refused; what refuses is a shape value that
        # is not a number.
        attr = next((field.key for field in form.fields
                     if field.group != SHAPE_TAB and field.enabled), None)
        kept = form.validate(dict(form.values, **{attr: "[1, 2,"}))
        number = form.validate(dict(form.values, k="abc"))
        ok(kept == [] and number and "number" in number[0],
           f"E: an override this editor cannot read as a literal is KEPT AS A STRING rather than "
           f"refused ({attr}), while a shape value that is not a number is refused "
           f"({number[0][:40]!r}...)")

        before_k = float(editor.rows[ROW].k)
        status = form.apply(dict(form.values, k="-0.75"))
        ok(float(editor.rows[ROW].k) == -0.75 and before_k != -0.75
           and "Updated advanced attributes" in status
           and editor.status_var.get() == status,
           f"A: apply wrote the shape value (k {before_k} -> {editor.rows[ROW].k}) and set the "
           f"status line")

        tabs, shown = _tk_tabs(editor, ROW)
        ok(tabs is not None and list(tabs) == list(form_groups) and shown and not boxes,
           f"T: the REAL Tk dialog opened with the same {len(tabs or [])} tabs and "
           f"{len(shown or [])} bound values"
           + (f" -- tabs {tabs} vs {list(form_groups)}" if tabs != list(form_groups) else ""))
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror = saved
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    (tabs, disabled, optimize_kind, k_kind, errors, applied, before_k, after_k, fields,
     expected_locked) = payload
    ok(list(tabs) == list(form_groups) and fields > len(tabs),
       f"Q1: the Qt form laid the same {len(tabs)} tabs in a QTabWidget over {fields} fields "
       f"({', '.join(tabs[:4])}...)")
    ok(optimize_kind == "QCheckBox" and k_kind == "QLineEdit",
       f"Q2: the switch is a {optimize_kind} and a shape value a {k_kind}")
    ok(applied and errors == [] and float(after_k) == -0.75 and float(before_k) != -0.75,
       f"Q3: the Qt Apply wrote k {before_k} -> {after_k}")
    ok(sorted(disabled) == sorted(expected_locked),
       f"Q4: the Qt form locked exactly the fields the model marks locked "
       f"({sorted(expected_locked)[:4]})")

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
