"""Display-free guard: the galvo scan overlay and grating settings row forms (bugs/0890,
docs/design_qt_migration.md phase 3).

Two small per-surface dialogs, and the first pair in the phase-3 tail that needed NOTHING new
from the framework -- which is what the tail is supposed to look like. Both are one row's data
and both validate in the model.

  G  the galvo overlay: seeded from the mirror's own angle, 25-angle limit, Clear
  N  the MIDDLE angle becomes the nominal pose; the rest are display-only
  R  the two refusals: no row, and a row that is not a Mirror -- to the STATUS LINE, as before
  T  the grating fields, their messages, and what Apply writes
  D  both REAL Tk dialogs open on the builders' fields
  Q  both Qt dialogs do the same
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


def _mirror_row(editor) -> int:
    """A Mirror row to work on. om05a_folded has none -- its folds are promoted solids -- so
    make one in memory rather than pinning the guard to a scene that might change."""
    found = next((index for index, row in enumerate(editor.rows)
                  if row.surface == "Mirror"), None)
    if found is not None:
        return found
    editor.rows[1].surface = "Mirror"
    return 1


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    mirror = _mirror_row(window.editor)
    window.refresh_from_model()
    app.processEvents()
    window.rows_view.selectRow(mirror)
    app.processEvents()
    galvo = window.action_manager["galvo_scan"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    galvo_state = [sorted(galvo.widgets), galvo.widgets["angles"].text(),
                   [action.label for action in galvo.form.actions]]
    galvo.close()
    app.processEvents()

    grating = window.action_manager["grating_settings"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    grating.widgets["grating_d"].setText("2.5")
    errors = list(grating.validate())
    applied = grating.apply_to_row()
    app.processEvents()
    pitch = float(window.editor.rows[mirror].grating_d)
    grating.close()
    app.processEvents()

    window.close()
    return [galvo_state, errors, bool(applied), pitch]


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
        "from KrakenOS.UI.validate_open3d_0890_surface_settings_forms import qt_runtime_checks\n"
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


def _tk_buttons(editor, opener):
    from tkinter import ttk

    before = {str(child) for child in editor.root.winfo_children()}
    opener()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None, []
    window = windows[-1]
    buttons, entries = [], 0
    try:
        def walk(widget):
            nonlocal entries
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
                    buttons.append(str(child.cget("text")))
                elif isinstance(child, ttk.Entry):
                    entries += 1
                walk(child)

        walk(window)
        return (window.title(), buttons, entries)
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import (FormRefused, build_galvo_scan_form,
                                       build_grating_settings_form)
    from KrakenOS.UI.row_forms.surface_settings import GALVO_LIMIT, model

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
        mirror = _mirror_row(editor)
        parts = model(editor)

        form = build_galvo_scan_form(editor, mirror)
        nominal = editor._mirror_display_slant_deg_for_rows(editor.rows, mirror)
        seeded = [float(value) for value in parts.parse_sequence(form.values["angles"])]
        messages = [form.validate({"angles": "0:100:1"}),
                    form.validate({"angles": "left a bit"}),
                    form.validate(dict(form.values))]
        ok(len(seeded) == 3 and abs(seeded[1] - nominal) < 1e-9
           and abs(seeded[0] - (nominal - 5)) < 1e-9
           and messages[0] == [f"Use {GALVO_LIMIT} or fewer overlay angles to keep the plot "
                               "readable."]
           and messages[1] and messages[1][0].startswith("Invalid TiltX list:")
           and messages[2] == []
           and [action.label for action in form.actions] == ["Clear"],
           f"G: seeded {seeded} around the mirror's own {nominal:g} deg; 101 angles refuse and "
           f"so does unparseable text")

        status = form.apply(dict(form.values))
        branch = editor._mirror_branch_angle_before_index(editor.rows, mirror)
        expected = editor._mirror_local_tilt_deg_from_display(branch, seeded[1])
        overlay = dict((editor.rows[mirror].advanced or {}).get("Display2D", {}) or {})
        ok(abs(float(editor.rows[mirror].tilt_x) - expected) < 1e-9
           and len(list(overlay.get(parts.overlay_key) or [])) == 3
           and "Galvo scan overlay set to" in status,
           f"N: the MIDDLE angle became the nominal pose (tilt_x={editor.rows[mirror].tilt_x:g}) "
           f"and all 3 went to the display-only overlay")

        cleared_form = build_galvo_scan_form(editor, mirror)
        cleared = cleared_form.actions[0].run(cleared_form, None)
        after = dict((editor.rows[mirror].advanced or {}).get("Display2D", {}) or {})
        ok("cleared" in cleared and not list(after.get(parts.overlay_key) or []),
           f"G2: Clear emptied the overlay ({cleared[:44]!r})")

        refusals = []
        plain = next(index for index, row in enumerate(editor.rows)
                     if row.surface not in ("Mirror", "Object", "Image"))
        for index, expected_message in ((len(editor.rows) + 5, "No mirror row selected."),
                                        (plain, "Galvo scan overlay applies to Mirror rows.")):
            try:
                build_galvo_scan_form(editor, index)
                refusals.append(("no refusal", index))
            except FormRefused as exc:
                if str(exc) != expected_message:
                    refusals.append((str(exc), expected_message))
        ok(not refusals,
           "R: an out-of-range row and a non-Mirror row each refuse with their own message"
           + (f" -- wrong: {refusals}" if refusals else ""))

        grating = build_grating_settings_form(editor, plain)
        grating_messages = [grating.validate(dict(grating.values, grating_d="x")),
                            grating.validate(dict(grating.values, grating_d="0")),
                            grating.validate(dict(grating.values, grating_d="1.5"))]
        grating_status = grating.apply(dict(grating.values, grating_d="1.5", diff_ord="1"))
        ok(grating_messages[0] == ["Pitch [um] expects a number."]
           and grating_messages[1] == ["Pitch [um] must be non-zero."]
           and grating_messages[2] == []
           and abs(float(editor.rows[plain].grating_d) - 1.5) < 1e-12
           and abs(float(editor.rows[plain].diff_ord) - 1.0) < 1e-12
           and "Updated grating settings" in grating_status,
           f"T: {grating_messages[0][0]!r}, {grating_messages[1][0]!r}; apply wrote pitch "
           f"{editor.rows[plain].grating_d} and order {editor.rows[plain].diff_ord}")

        galvo_tk = _tk_buttons(editor, lambda: editor.open_galvo_scan_overlay_settings(mirror))
        grating_tk = _tk_buttons(editor, lambda: editor._open_grating_settings_editor(plain))
        ok(galvo_tk and galvo_tk[1] == ["Validate", "Apply", "Clear", "Cancel"]
           and galvo_tk[2] == 1
           and grating_tk and grating_tk[1] == ["Validate", "Apply", "Cancel"]
           and grating_tk[2] == 3,
           f"D: the REAL Tk dialogs drew {galvo_tk[1]} over {galvo_tk[2]} entry and "
           f"{grating_tk[1]} over {grating_tk[2]}")
    finally:
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    galvo_state, errors, applied, pitch = payload
    ok(galvo_state[0] == ["angles"] and galvo_state[1] and galvo_state[2] == ["Clear"]
       and errors == [] and applied and abs(float(pitch) - 2.5) < 1e-12,
       f"Q: the Qt galvo dialog showed {galvo_state[0]} seeded {galvo_state[1]!r} with its "
       f"Clear verb, and the grating dialog applied pitch {pitch}")

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
