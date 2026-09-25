"""Display-free guard: the Path Component placement row form and `RowForm.labels` (bugs/0888,
docs/design_qt_migration.md phase 3).

Insert a component into a beam-splitter arm, or onto a traced BRANCH_PATH. The component choice
does not just pick a type -- it CHANGES WHAT THE NEXT FIELD MEANS: a focal length for a thin
lens, a radius of curvature for a refracting surface, a mirror radius for a mirror, and nothing
at all for a detector or an aperture, whose glass is fixed too.

`FormField.label` is frozen when the form is built, so `RowForm.labels` is the live half --
the fourth live property after `values`, `choices` and `locked` -- and both views ask
`form.label_for(key)`.

  B  the builder, and the refusal when the row is not a splitter
  L  each component relabels the parameter and locks what it does not use
  V  the model's own messages, including the thin lens's zero focal length
  A  apply inserts the row on the arm
  T  the REAL Tk dialog RELABELS as the choice changes
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
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.dialogs.row_form_dialog import RowFormDialog
    from KrakenOS.UI.row_forms import build_path_component_form
    from KrakenOS.UI.uihost import host_of

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    splitter = next(index for index, row in enumerate(window.editor.rows)
                    if row.surface == "Beam Splitter")
    form = build_path_component_form(window.editor, splitter, "Transmit")
    dialog = RowFormDialog(form, parent=window, host=host_of(window))
    dialog.show()
    app.processEvents()
    first = dialog.labels["parameter"].text()
    dialog.widgets["component"].setCurrentText("Thin lens")
    app.processEvents()
    lens = (dialog.labels["parameter"].text(), dialog.widgets["glass"].isEnabled())
    dialog.widgets["component"].setCurrentText("Refractive surface")
    app.processEvents()
    refractive = (dialog.labels["parameter"].text(), dialog.widgets["glass"].isEnabled())
    dialog.close()
    app.processEvents()

    window.close()
    return [first, list(lens), list(refractive)]


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
        "from KrakenOS.UI.validate_open3d_0888_path_component_form import qt_runtime_checks\n"
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
    import tkinter.messagebox as tk_messagebox
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_path_component_form

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
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        splitter = next(index for index, row in enumerate(editor.rows)
                        if row.surface == "Beam Splitter")

        form = build_path_component_form(editor, splitter, "Transmit")
        refused = ""
        try:
            build_path_component_form(editor, 0, "Transmit")
        except FormRefused as exc:
            refused = str(exc)
        bad_role = ""
        try:
            build_path_component_form(editor, splitter, "Sideways")
        except FormRefused as exc:
            bad_role = str(exc)
        keys = [field.key for field in form.fields]
        ok(len(keys) == 10 and keys[0] == "component"
           and form.title == "Add Transmit Path Component"
           and refused == "Right-click a Beam Splitter row first."
           and bad_role == "Unsupported path: Sideways",
           f"B: {len(keys)} fields for the transmit arm; a non-splitter row refuses "
           f"({refused!r}) and so does an unknown path")

        field = form.field("component")
        seen = {}
        for kind in ("Thin lens", "Refractive surface", "Mirror", "Aperture stop"):
            field.on_change(form, kind)
            seen[kind] = (form.label_for("parameter"), form.label_for("glass"),
                          sorted(form.locked))
        ok(seen["Thin lens"][0] == "Focal length [mm]"
           and seen["Refractive surface"][0] == "Radius of curvature [mm]"
           and seen["Mirror"][0].startswith("Mirror radius")
           and seen["Aperture stop"][0] == "Parameter (not used)"
           and seen["Thin lens"][2] == ["glass"]
           and seen["Refractive surface"][2] == []
           and seen["Aperture stop"][2] == ["glass", "parameter"],
           f"L: the parameter is a {seen['Thin lens'][0]!r} for a thin lens, a "
           f"{seen['Refractive surface'][0]!r} for a refracting one, and nothing for an "
           f"aperture -- which also locks {seen['Aperture stop'][2]}")

        field.on_change(form, "Thin lens")
        messages = [form.validate(dict(form.values, parameter="0")),
                    form.validate(dict(form.values, distance="-3")),
                    form.validate(dict(form.values, diameter="nope")),
                    form.validate(dict(form.values, local_tilt_z="sideways")),
                    form.validate(dict(form.values))]
        ok(messages[0] == ["Thin lens focal length cannot be zero."]
           and messages[1] == ["Distance must be positive."]
           and messages[2] == ["Distance and diameter must be numbers."]
           and messages[3] == ["Local offset and tilt values must be numeric."]
           and messages[4] == [] and form.values["parameter"] == "100",
           f"V: {messages[0][0]!r}, {messages[1][0]!r}, {messages[2][0][:34]!r}; and choosing "
           f"a thin lens seeded f={form.values['parameter']}")

        before = len(editor.rows)
        status = form.apply(dict(form.values))
        ok(len(editor.rows) == before + 1 and "in the transmit path" in status
           and editor.status_var.get() == status,
           f"A: apply inserted one row ({before} -> {len(editor.rows)}) -- {status[:52]!r}")

        before_windows = {str(child) for child in editor.root.winfo_children()}
        editor.open_arm_path_component_placement(splitter, "Transmit")
        windows = [child for child in editor.root.winfo_children()
                   if str(child) not in before_windows and child.winfo_class() == "Toplevel"]
        labels_before, labels_after = [], []
        if windows:
            window = windows[-1]
            combos, texts = [], []

            def walk(widget):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Combobox):
                        combos.append(child)
                    elif isinstance(child, ttk.Label):
                        texts.append(child)
                    walk(child)

            walk(window)
            labels_before = [str(label.cget("text")) for label in texts]
            if combos:
                combos[0].set("Thin lens")
                combos[0].event_generate("<<ComboboxSelected>>")
                window.update_idletasks()
            labels_after = [str(label.cget("text")) for label in texts]
            window.destroy()
        ok(windows and "Parameter (not used)" in labels_before
           and "Focal length [mm]" in labels_after
           and "Parameter (not used)" not in labels_after and not boxes,
           "T: the REAL Tk dialog RELABELLED the parameter field when the component changed "
           "('Parameter (not used)' -> 'Focal length [mm]')")
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

    first, lens, refractive = payload
    ok(first == "Parameter (not used)" and lens[0] == "Focal length [mm]"
       and lens[1] is False and refractive[0] == "Radius of curvature [mm]"
       and refractive[1] is True,
       f"Q: the Qt dialog relabelled {first!r} -> {lens[0]!r} -> {refractive[0]!r}, and the "
       f"glass field followed (locked for a lens, live for a refracting surface)")

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
