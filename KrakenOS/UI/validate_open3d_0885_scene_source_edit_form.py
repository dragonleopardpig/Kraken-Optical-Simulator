"""Display-free guard: the scene-source edit row form (bugs/0885,
docs/design_qt_migration.md phase 3).

bugs/0363's "general 3D source element" popup: name, origin, emit direction, emitting size, cone
half-angle, ray count and power, applied through `update_scene_source_spec` -- the same path the
seat-on-face glue uses. A coaxial illuminator gets two more fields (bugs/0401), and that is the
MODEL deciding what the dialog contains: the builder reads the spec and adds them or does not.

  B  the builder, and a refusal for a source that is not there
  V  the model's own messages for a zero direction, a zero size and non-numeric text
  A  apply writes radius_x/radius_y (half the entered size) through update_scene_source_spec
  C  a coaxial source gets the edge profile and width; a plain one does not
  T  the REAL Tk popup opens on the builder's fields and GRABS
  Q  the Qt dialog shows the same fields and applies the same
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

    dialog = window.action_manager["source_edit"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    keys = sorted(dialog.widgets)
    dialog.widgets["width"].setText("14")
    dialog.widgets["height"].setText("6")
    errors = list(dialog.validate())
    applied = dialog.apply_to_row()
    app.processEvents()
    specs = window.editor._normalize_scene_source_specs(
        getattr(window.editor, "layout_scene_source_specs", []) or [])
    radii = [float(specs[0].get("radius_x", 0.0)), float(specs[0].get("radius_y", 0.0))]

    window.close()
    return [keys, errors, bool(applied), radii]


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
        "from KrakenOS.UI.validate_open3d_0885_scene_source_edit_form import qt_runtime_checks\n"
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
    from types import SimpleNamespace

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_scene_source_edit_form
    from KrakenOS.UI.row_forms.source_edit import model

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
        specs = editor._normalize_scene_source_specs(
            getattr(editor, "layout_scene_source_specs", []) or [])
        source_id = str(specs[0]["source_id"])

        form = build_scene_source_edit_form(editor, source_id)
        refused = ""
        try:
            build_scene_source_edit_form(editor, "source:not-a-source")
        except FormRefused as exc:
            refused = str(exc)
        empty = ""
        try:
            build_scene_source_edit_form(editor, "")
        except FormRefused as exc:
            empty = str(exc)
        keys = [field.key for field in form.fields]
        ok(keys[0] == "name" and "ray_count" in keys and "cone_deg" in keys
           and len(keys) == 12 and source_id in form.summary
           and refused.endswith("not found.") and empty == "Pick a scene source to edit.",
           f"B: {len(keys)} fields for {source_id!r}; an unknown source refuses "
           f"({refused!r}) and so does no source at all")

        messages = [form.validate(dict(form.values, source_l="0", source_m="0", source_n="0")),
                    form.validate(dict(form.values, width="0")),
                    form.validate(dict(form.values, power="lots")),
                    form.validate(dict(form.values))]
        ok(messages[0] == ["Direction must be a non-zero vector."]
           and messages[1] == ["Width and height must be positive."]
           and messages[2] == ["Enter numeric values (direction may be any non-zero vector)."]
           and messages[3] == [],
           f"V: {messages[0][0]!r}, {messages[1][0]!r}, {messages[2][0][:34]!r}")

        status = form.apply(dict(form.values, width="12", height="8", name="Guard Src"))
        after = editor._normalize_scene_source_specs(
            getattr(editor, "layout_scene_source_specs", []) or [])[0]
        ok(abs(float(after.get("radius_x", 0.0)) - 6.0) < 1e-9
           and abs(float(after.get("radius_y", 0.0)) - 4.0) < 1e-9
           and str(after.get("name")) == "Guard Src" and "12 x 8 mm" in status,
           f"A: apply halved the entered size into radius_x/radius_y "
           f"({after.get('radius_x')}, {after.get('radius_y')}) through "
           f"update_scene_source_spec")

        parts = model(editor)
        plain_keys = {field.key for field in build_scene_source_edit_form(
            editor, source_id).fields}
        coaxial_spec = dict(after)
        coaxial_spec[parts.coaxial_key] = True
        coaxial_owner = SimpleNamespace(
            _normalize_scene_source_specs=lambda _specs: [coaxial_spec],
            layout_scene_source_specs=[coaxial_spec],
            update_scene_source_spec=lambda *_a, **_k: True,
        )
        coaxial_keys = {field.key for field in build_scene_source_edit_form(
            coaxial_owner, source_id).fields}
        ok("coaxial_edge_profile" not in plain_keys
           and {"coaxial_edge_profile", "coaxial_edge_width"} <= coaxial_keys,
           f"C: the MODEL decides the dialog's contents -- a coaxial source adds "
           f"{sorted(coaxial_keys - plain_keys)}, a plain one does not")

        from tkinter import ttk

        before = {str(child) for child in editor.root.winfo_children()}
        inspector = SimpleNamespace(status_var=SimpleNamespace(set=lambda _text: None))
        from KrakenOS.UI.panels.open3d_source_edit_dialog import open_scene_source_edit_dialog

        open_scene_source_edit_dialog(editor, inspector, source_id)
        windows = [child for child in editor.root.winfo_children()
                   if str(child) not in before and child.winfo_class() == "Toplevel"]
        entries = 0
        grabbed = ""
        if windows:
            window = windows[-1]
            grabbed = str(window.grab_current() or "")

            def walk(widget):
                nonlocal entries
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Entry):
                        entries += 1
                    walk(child)

            walk(window)
            window.grab_release()
            window.destroy()
        ok(windows and entries >= 11 and grabbed == str(windows[-1]),
           f"T: the REAL Tk popup drew {entries} entries and GRABBED, so a click in the "
           f"viewport behind cannot retrace under a half-filled form")
    finally:
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    keys, errors, applied, radii = payload
    ok(len(keys) == 12 and errors == [] and applied
       and abs(float(radii[0]) - 7.0) < 1e-9 and abs(float(radii[1]) - 3.0) < 1e-9,
       f"Q: the Qt dialog showed {len(keys)} fields and applied 14 x 6 mm as radii {radii}")

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
