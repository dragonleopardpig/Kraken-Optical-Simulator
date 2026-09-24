"""Display-free guard: the Diffuse / BRDF row form (bugs/0870,
docs/design_qt_migration.md phase 3).

The second row form, and the one that stretched the framework: a MULTI-LINE field (the pySCATMECH
backend parameters) and a choice list COMPUTED from the layout (which other surface to
importance-sample towards).

  F  the form's fields are the settings the model normalises, less the one it carries silently
  C  the guided-target choices are every OTHER row, as the Tk dialog lists them
  K  the model CLAMPS rather than rejects: reflectance 5 becomes 1.0 and validation passes --
     unlike the beam splitter, which refuses. Both toolkits inherit whichever the model does
  V  the model CLAMPS every numeric field, so validation cannot fire from a form; the one case
     it still reports is an unknown model, which a read-only choice cannot produce
  A  apply writes the settings, makes the row a Diffuse Object with MIRROR glass, and sets the
     status line
  T  the REAL Tk dialog shows the builder's values
  Q  the Qt form shows the same values in the right widgets (the textarea included), and its
     Apply leaves the row in the same state
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
NEW_REFLECTANCE = "0.42"
ROW = 3


def diffuse_row(editor) -> int:
    """A Diffuse Object row to edit -- this scene has none, so the guard makes one."""
    from KrakenOS.UI.row_forms.diffuse_scatter import model

    parts = model(editor)
    existing = [index for index, row in enumerate(editor.rows) if row.surface == parts.surface]
    if existing:
        return existing[0]
    index = min(ROW, len(editor.rows) - 1)
    editor.rows[index].surface = parts.surface
    return index


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.row_forms.diffuse_scatter import model

    from KrakenOS.UI.validate_open3d_0870_diffuse_scatter_row_form import diffuse_row

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor
    parts = model(editor)

    index = diffuse_row(editor)
    window.rows_view.selectRow(index)
    app.processEvents()
    dialog = window.action_manager["diffuse_scatter"].trigger() or window._open_dialogs[-1]
    app.processEvents()

    widget_kinds = {key: type(widget).__name__ for key, widget in dialog.widgets.items()}
    values = dict(dialog.values())
    title = dialog.windowTitle()

    dialog.widgets["reflectance"].setText(NEW_REFLECTANCE)
    applied = dialog.apply_to_row()
    app.processEvents()
    settings = dict(dict(editor.rows[index].advanced or {}).get(parts.attr, {}))

    window.close()
    return [title, values, widget_kinds, bool(applied),
            {key: str(value) for key, value in settings.items()},
            str(editor.rows[index].surface), str(editor.rows[index].glass)]


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
        "from KrakenOS.UI.validate_open3d_0870_diffuse_scatter_row_form import qt_runtime_checks\n"
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


def _tk_values(editor, row_index):
    """Open the REAL Tk dialog and read back what its widgets show."""
    import tkinter as tk

    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_diffuse_scatter_settings(row_index)
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None, None
    window = windows[-1]
    try:
        shown: list[str] = []
        texts: list[str] = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Text):
                    texts.append(child.get("1.0", "end-1c"))
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
        return shown, texts
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_diffuse_scatter_form
    from KrakenOS.UI.row_forms.diffuse_scatter import model, target_options

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

    form_values = None
    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        parts = model(editor)
        index = diffuse_row(editor)
        form = build_diffuse_scatter_form(editor, index)
        form_values = dict(form.values)

        settings_keys = set(parts.normalize(None))
        field_keys = {field.key for field in form.fields}
        ok(field_keys < settings_keys and settings_keys - field_keys == {"polarization"},
           f"F: the form's {len(field_keys)} fields are the model's settings less "
           f"{sorted(settings_keys - field_keys)}, which it carries from the defaults")

        target_field = form.field("target_surface")
        expected = target_options(editor, index)
        ok(target_field is not None and target_field.choices == expected
           and len(expected) == len(editor.rows) and expected[0] == "None"
           and all(not option.startswith(f"{index}:") for option in expected[1:]),
           f"C: the guided-target choices are every other row ({len(expected)} options, the "
           f"edited row excluded)")

        clamped = dict(form_values, reflectance="5")
        clamped_errors = form.validate(clamped)
        normalised = parts.normalize({**clamped, "polarization": parts.defaults["polarization"]})
        ok(clamped_errors == [] and float(normalised["reflectance"]) == 1.0,
           f"K: the model CLAMPS an out-of-range reflectance (5 -> "
           f"{normalised['reflectance']}) and validation then passes -- unlike the beam splitter, "
           f"which refuses; both toolkits inherit whichever the model does")

        # What CAN the validator still catch from a form? Measured, not assumed.
        clamps = []
        for key, value, expected in (("sample_count", "0", 1), ("max_branch_depth", "0", 1),
                                     ("target_radius_scale", "0", 0.01),
                                     ("roughness_deg", "400", 90.0),
                                     ("max_scatter_angle_deg", "200", 90.0),
                                     ("min_branch_power", "-1", 0.0)):
            candidate = parts.normalize({**dict(form_values, **{key: value}),
                                         "polarization": parts.defaults["polarization"]})
            if float(candidate[key]) != float(expected) or form.validate(
                    dict(form_values, **{key: value})):
                clamps.append((key, candidate[key]))
        unknown_model = parts.validate(parts.normalize({"model": "Nonsense"}))
        model_field = form.field("model")
        ok(not clamps and unknown_model and model_field is not None
           and model_field.kind == "choice",
           f"V: the model CLAMPS every numeric field into range, so validation cannot fire from a "
           f"form -- the one case it still reports is an unknown model "
           f"({unknown_model[0][:44]!r}...), which neither dialog can produce because that field "
           f"is a read-only choice"
           + (f" -- unclamped: {clamps}" if clamps else ""))

        applied_status = form.apply(dict(form_values, reflectance=NEW_REFLECTANCE))
        settings = dict(dict(editor.rows[index].advanced or {}).get(parts.attr, {}))
        ok(abs(float(settings.get("reflectance", 0)) - float(NEW_REFLECTANCE)) < 1e-12
           and str(editor.rows[index].surface) == str(parts.surface)
           and str(editor.rows[index].glass).upper() == "MIRROR"
           and "Updated Diffuse Object settings" in applied_status
           and editor.status_var.get() == applied_status,
           f"A: apply wrote reflectance {settings.get('reflectance')}, made the row "
           f"{editor.rows[index].surface!r} with {editor.rows[index].glass!r} glass, and set the "
           f"status line")

        shown, texts = _tk_values(editor, index)
        rebuilt = build_diffuse_scatter_form(editor, index).values
        missing = [key for key, value in rebuilt.items()
                   if key != "backend_parameters" and value not in (shown or [])]
        ok(shown is not None and not missing and texts
           and rebuilt["backend_parameters"].strip() == texts[0].strip() and not boxes,
           f"T: the REAL Tk dialog shows the builder's values -- {len(shown or [])} bound "
           f"variables and the backend parameters in its Text widget"
           + (f" -- missing {missing}" if missing else ""))
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

    title, values, widget_kinds, applied, settings, surface, glass = payload
    ok(values == form_values and "Diffuse / BRDF - S" in title,
       f"Q1: the Qt form opened on the selected row ({title!r}) with the builder's own values")
    ok(widget_kinds.get("backend_parameters") == "QPlainTextEdit"
       and widget_kinds.get("model") == "QComboBox"
       and widget_kinds.get("reflectance") == "QLineEdit",
       f"Q2: each field got the widget its kind asks for "
       f"({widget_kinds.get('backend_parameters')} for the multi-line one)")
    ok(applied and abs(float(settings.get("reflectance", 0)) - float(NEW_REFLECTANCE)) < 1e-12
       and glass.upper() == "MIRROR",
       f"Q3: the Qt Apply left the row in the same state -- reflectance "
       f"{settings.get('reflectance')}, surface {surface!r}, glass {glass!r}")

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
