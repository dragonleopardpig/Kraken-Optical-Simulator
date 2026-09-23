"""Display-free guard: the Paraxial Calculator's model, in both toolkits (bugs/0865,
docs/design_qt_migration.md phase 3).

The first FORM dialog ported: fields, a solve and an apply that writes back into the layout. About
200 lines of paraxial arithmetic lived inside a Tk closure -- the conjugate relations, the
matrix-solution path when the layout's cardinal points are loaded, and what a solved value means
when applied. They are now `KrakenOS/UI/paraxial_calculator.py`, which the Tk dialog was rewired
onto and the Qt dialog uses.

  M  both forms open on the same values, because the model supplies them
  S  the module solves all four targets; the REAL Tk dialog displays the module's own result
  F  the field-state rule is the module's, and the Tk entries follow it
  A  apply writes the solved value into the layout's own cell; a magnification solve refuses
     with NothingToApply (a status line, not an error box)
  E  a refusal carries the model's message
  Q  the Qt dialog opens on the same values, solves each target to the module's result, honours
     the same field states, and applies to the same row
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
TARGETS = ("Image distance", "Object distance", "Magnification", "Distances from magnification")


def usable_opening(opening):
    """The opening values, with a magnification the last target can actually use.

    A form opens with m = 0, and "Distances from magnification" rightly refuses that ("object
    distance goes to infinity") -- so the comparison needs a real one, the same on both sides.
    """
    from dataclasses import replace

    try:
        current = float(opening.magnification)
    except (TypeError, ValueError):
        current = 0.0
    return replace(opening,
                   magnification="0.5" if abs(current) <= 1e-12 else opening.magnification)


def solve_all(owner, opening):
    """The module's answer for each target, from one set of opening values."""
    from dataclasses import replace

    from KrakenOS.UI.paraxial_calculator import CalculatorFailed, solve

    opening = usable_opening(opening)
    out = {}
    for target in TARGETS:
        try:
            solution = solve(owner, replace(opening, solve_for=target))
            out[target] = [solution.result, solution.detail]
        except CalculatorFailed as exc:
            out[target] = [f"Solve failed: {exc}", ""]
    return out


def qt_runtime_checks() -> list:
    from KrakenOS.UI.paraxial_calculator import field_states, initial_inputs
    from KrakenOS.UI.qt.app import build

    from KrakenOS.UI.validate_open3d_0865_paraxial_calculator import solve_all, usable_opening

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor

    opening = usable_opening(initial_inputs(editor))
    expected = solve_all(editor, opening)

    dialog = window.action_manager["paraxial_calculator"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    opened = {"effl": dialog.fields["effl"].text(), "ppa": dialog.fields["ppa"].text(),
              "ppp": dialog.fields["ppp"].text(),
              "object_mode": dialog.object_mode.currentText(),
              "object_distance": dialog.fields["object_distance"].text(),
              "image_distance": dialog.fields["image_distance"].text()}

    solved = {}
    states_ok = True
    for target in TARGETS:
        dialog.solve_for.setCurrentText(target)
        app.processEvents()
        # re-seed the distances so every target solves from the same numbers the module used
        dialog.fields["object_distance"].setText(opening.object_distance)
        dialog.fields["image_distance"].setText(opening.image_distance)
        dialog.fields["magnification"].setText(opening.magnification)
        dialog.solve()
        solved[target] = [dialog.result.text(), dialog.detail.text()]
        wanted = field_states(target, dialog.object_mode.currentText())
        for key, state in wanted.items():
            widget = dialog.fields[key]
            if widget.isEnabled() != (state != "disabled") or widget.isReadOnly() != (state == "readonly"):
                states_ok = False

    # apply an image-distance solve
    dialog.solve_for.setCurrentText("Image distance")
    dialog.fields["object_distance"].setText(opening.object_distance)
    app.processEvents()
    payload = dialog.solve()
    image_row = max(0, len(editor.rows) - 2)
    before = float(editor.rows[image_row].thickness)
    applied = dialog.apply_to_layout()
    after = float(editor.rows[image_row].thickness)

    dialog.close()
    window.close()
    return [opened, solved, expected, states_ok,
            [bool(applied), image_row, before, after, float(payload.get("value", 0.0))]]


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
        "from KrakenOS.UI.validate_open3d_0865_paraxial_calculator import qt_runtime_checks\n"
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


def _tk_calculator(editor):
    """Open the REAL Tk calculator and read back everything it displays."""
    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_paraxial_calculator()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None, None
    window = windows[-1]
    try:
        shown: list[str] = []
        states: dict[str, str] = {}

        def walk(widget):
            for child in widget.winfo_children():
                try:
                    name = str(child.cget("textvariable"))
                except Exception:
                    name = ""
                if name:
                    try:
                        shown.append(str(window.getvar(name)))
                    except Exception:
                        pass
                try:
                    text = str(child.cget("text"))
                    if text:
                        shown.append(text)
                except Exception:
                    pass
                if child.winfo_class() == "TEntry":
                    try:
                        states[str(child.cget("textvariable"))] = str(child.cget("state"))
                    except Exception:
                        pass
                walk(child)

        walk(window)
        return shown, states
    finally:
        try:
            window.grab_release()
        except Exception:
            pass
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    from dataclasses import replace

    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.paraxial_calculator import (CalculatorFailed, NothingToApply, apply_solution,
                                                 field_states, initial_inputs, solve)

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
    opening = None
    expected = {}
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        opening = initial_inputs(editor)
        expected = solve_all(editor, opening)

        ok(float(opening.effl) != 0.0 and opening.object_mode in ("Finite", "Infinity")
           and float(opening.object_distance) == float(editor.rows[0].thickness),
           f"M: the form opens on the model's own values -- EFL {opening.effl}, mode "
           f"{opening.object_mode}, object gap {opening.object_distance} from row 0")

        solved_targets = [t for t, (result, _detail) in expected.items()
                          if not result.startswith("Solve failed")]
        ok(len(solved_targets) == len(TARGETS),
           f"S1: the module solved all {len(TARGETS)} targets from one set of opening values "
           f"({expected['Image distance'][0]!r}; "
           f"{expected['Distances from magnification'][0][:40]!r}...)")

        shown, tk_states = _tk_calculator(editor)
        ok(shown is not None and expected["Image distance"][0] in shown
           and expected["Image distance"][1] in shown and not boxes,
           f"S2: the REAL Tk dialog displays the module's own result and detail"
           + (f" -- boxes {boxes}" if boxes else ""))

        wanted = field_states(opening.solve_for, opening.object_mode)
        matched = sum(1 for value in tk_states.values() if value in
                      {"normal", "disabled", "readonly"})
        ok(set(wanted) == {"object_distance", "image_distance", "magnification"}
           and "disabled" in set(tk_states.values()) and matched >= 3,
           f"F: the field-state rule is the module's, and the Tk entries carry real states "
           f"({sorted(set(tk_states.values()))})")

        image_row = max(0, len(editor.rows) - 2)
        before = float(editor.rows[image_row].thickness)
        solution = solve(editor, opening)
        status = apply_solution(editor, solution.payload, solution.result)
        after = float(editor.rows[image_row].thickness)
        ok(abs(after - float(solution.payload["value"])) < 1e-9 and after != before
           and "Click Update" in status,
           f"A1: apply wrote the solved image distance into row {image_row} "
           f"({before:.6g} -> {after:.6g}) and returned {status[:48]!r}...")

        refused = ""
        try:
            apply_solution(editor, {"target": "magnification", "value": 1.0}, "m")
        except NothingToApply as exc:
            refused = str(exc)
        ok("No layout cell to apply" in refused,
           f"A2: a magnification solve refuses with NothingToApply ({refused!r}) -- a status "
           f"line, not an error box")

        message = ""
        try:
            solve(editor, replace(opening, effl="0"))
        except CalculatorFailed as exc:
            message = str(exc)
        ok(message == "EFL must be non-zero",
           f"E: a refusal carries the model's own message ({message!r})")
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

    opened, qt_solved, qt_expected, states_ok, applied = payload
    ok(opened["effl"] == opening.effl and opened["object_mode"] == opening.object_mode
       and opened["object_distance"] == opening.object_distance,
       f"Q1: the Qt form opened on the same values as Tk (EFL {opened['effl']}, mode "
       f"{opened['object_mode']})")
    differing = [target for target in TARGETS if qt_solved[target] != qt_expected[target]]
    ok(not differing and qt_solved["Image distance"][0] == expected["Image distance"][0],
       f"Q2: the Qt dialog solved all {len(TARGETS)} targets to the module's own results, the "
       f"same ones Tk shows" + (f" -- differing {differing}" if differing else ""))
    ok(states_ok, "Q3: the Qt fields honour the module's field-state rule for every target")
    was_applied, row_index, before_value, after_value, solved_value = applied
    ok(was_applied and abs(after_value - solved_value) < 1e-9 and after_value != before_value,
       f"Q4: Apply wrote the solved value into row {row_index} "
       f"({before_value:.6g} -> {after_value:.6g})")

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
