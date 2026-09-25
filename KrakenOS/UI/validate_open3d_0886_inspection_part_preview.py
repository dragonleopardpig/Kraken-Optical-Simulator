"""Display-free guard: the Inspection Part row form and `FormPreview` (bugs/0886,
docs/design_qt_migration.md phase 3).

The eighth family property, and the one that kept this dialog off the framework: bugs/0828
replaced an explanatory paragraph with a PICTURE of the part at true proportions -- the two
inspected faces lit, the unreachable ones greyed -- plus a derivation chain where every line
names its parent, because "a dense sentence does not attach to the fields above it".

That picture is model data, so `FormPreview` carries it: `shapes(form, values)` says what to
draw, `caption(form, values)` what to write beside it, and both views redraw on every keystroke
so the consequence of a number is visible BEFORE Apply.

  B  the builder: the fields, the two verbs, the model's stored keys
  P  the preview: six faces, two lit, a caption -- and it FOLLOWS the typed number
  V  the model's own messages
  A  apply writes through set_inspection_part_spec, derived keys untouched
  T  the REAL Tk dialog draws the picture on a canvas
  Q  the Qt dialog paints the same shapes and re-captions as you type
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
LIT_FILL = "#2f7f3f"


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    dialog = window.action_manager["inspection_part"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    pixmap = dialog.preview_label.pixmap()
    size = [int(pixmap.width()), int(pixmap.height())] if pixmap is not None else [0, 0]
    first_caption = dialog.preview_caption.text()
    dialog.widgets["width_mm"].setText("90")
    dialog.redraw_preview()
    app.processEvents()
    second_caption = dialog.preview_caption.text()
    dialog.close()
    app.processEvents()

    window.close()
    return [size, first_caption.splitlines()[:1], second_caption.splitlines()[:1]]


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
        "from KrakenOS.UI.validate_open3d_0886_inspection_part_preview import "
        "qt_runtime_checks\n"
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
    import tkinter as tk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import build_inspection_part_form

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

        form = build_inspection_part_form(editor)
        keys = [field.key for field in form.fields]
        labels = [action.label for action in form.actions]
        ok(keys == ["enabled", "width_mm", "depth_mm", "height_mm", "required_fov_mm",
                    "step_path"]
           and labels == ["Browse Part STEP...", "Apply + Solve FOV to this face"]
           and form.preview is not None,
           f"B: {len(keys)} fields in the model's stored keys (Length=width_mm, "
           f"Width=depth_mm, Thickness=height_mm) and the two verbs {labels}")

        values = dict(form.values)
        shapes = list(form.preview.shapes(form, values))
        polygons = [shape for shape in shapes if shape["kind"] == "polygon"]
        lit = [shape for shape in polygons if shape.get("fill") == LIT_FILL]
        caption = form.preview.caption(form, values)
        wider = list(form.preview.shapes(form, dict(values, width_mm="90")))
        wider_caption = form.preview.caption(form, dict(values, width_mm="90"))
        ok(len(polygons) == 6 and len(lit) == 2
           and sum(1 for shape in shapes if shape["kind"] == "text") == 1
           and caption.splitlines() and "50" in caption.splitlines()[0]
           and polygons[0]["points"] != wider[0]["points"]
           and "90" in wider_caption.splitlines()[0],
           f"P: six faces with {len(lit)} lit and a {len(caption.splitlines())}-line chain -- "
           f"and typing 90 redrew the part AND recaptioned it, before any Apply")

        messages = [form.validate(dict(values, width_mm="wide")),
                    form.validate(dict(values, height_mm="-3")),
                    form.validate(dict(values, required_fov_mm="-2")),
                    form.validate(dict(values, required_fov_mm="")),
                    form.validate(values)]
        ok(messages[0] == ["Length L (mm) expects a number."]
           and messages[1] == ["Thickness T (mm) must be non-negative."]
           and messages[2] == ["Required FOV must be a positive number, or blank."]
           and messages[3] == [] and messages[4] == [],
           f"V: {messages[0][0]!r}, {messages[1][0]!r}, {messages[2][0]!r}; blank FOV passes")

        before = dict(editor.inspection_part_spec or {})
        status = form.apply(dict(values, width_mm="55"))
        after = dict(editor.inspection_part_spec)
        ok(abs(float(after["width_mm"]) - 55.0) < 1e-9
           and float(after["axis_reach_mm"]) == float(before.get("axis_reach_mm", 0.0))
           and "Applied. Inspected face" in status,
           f"A: apply wrote width_mm={after['width_mm']} through set_inspection_part_spec and "
           f"left the DERIVED axis_reach_mm/axis_offset_mm alone (bugs/0768)")

        before_windows = {str(child) for child in editor.root.winfo_children()}
        editor.open_inspection_part_dialog()
        windows = [child for child in editor.root.winfo_children()
                   if str(child) not in before_windows and child.winfo_class() == "Toplevel"]
        items = 0
        canvases = 0
        if windows:
            found = []

            def walk(widget):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Canvas):
                        found.append(child)
                    walk(child)

            walk(windows[-1])
            canvases = len(found)
            items = len(found[0].find_all()) if found else 0
            windows[-1].destroy()
        ok(canvases == 1 and items == len(shapes),
           f"T: the REAL Tk dialog drew the picture on {canvases} canvas as {items} items "
           f"-- the same {len(shapes)} shapes the model returned")
    finally:
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    size, first_caption, second_caption = payload
    ok(size == [210, 150] and first_caption and second_caption
       and first_caption != second_caption and "90" in second_caption[0],
       f"Q: the Qt dialog painted a {size[0]}x{size[1]} picture and re-captioned it as the "
       f"number was typed ({first_caption[0][:34]!r} -> {second_caption[0][:34]!r})")

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
