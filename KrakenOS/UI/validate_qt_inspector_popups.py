"""Guard for bugs/0950: the inspector's small popups open in the running shell.

Five small windows the 3D inspector builds by hand in Tk -- the centred one-value prompt (Quick
Estimation's field value / field type), LED Edge Distance, Edit Thickness, Resize Solid and the
bug-flag description -- were invisible in the Qt shell, and the four that wait on themselves froze
it. Each now asks the shell first; the Tk windows are unchanged for the Tk app.

  S  static: every function in `open3d_inspector.py` and `services/` that builds a `tk.Toplevel`
     either asks the shell before it does, or is listed in `KNOWN_TK_POPUPS` with the reason --
     an exact list, so it can only shrink
  P  pure: the resize rule (`_step_overlay_resize_target`) -- three free sizes, or one
     cross-section + depth for a coupled cube -- and its two refusals
  Q  in a real Qt shell on om05a_folded, each popup asks through the shell and the answer lands in
     the model:
       Q1 field value + field type: the host's text prompt, prefilled; the typed value is set
       Q2 LED edge distance: the host's number prompt, prefilled with the live distance
       Q3 Edit Thickness: the host's number prompt; after typing V the NEXT prompt is prefilled
          with V; a cancelled prompt changes nothing
       Q4 Resize Solid: a Qt row form with the popup's fields; Apply stores the typed extents; a
          non-positive size is refused and stores nothing
       Q5 the flag description: a Qt window that is NOT modal; Save writes description.txt,
          state.json and the recording's event; Keep keeps the bundle without words; closing an
          empty box deletes the bundle; closing a typed box saves it
  N  none of Q creates a Tk window or waits on one
  T  in the Tk app the same five still open their own Tk windows (titles as before), take the
     typed value, and ask nothing through tkinter.simpledialog
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QTPOPUPS_RESULT "
SKIP_MARK = "QTPOPUPS_SKIP "
SCENE = Path("attachment/om05a_folded.py")
SOURCES = ("KrakenOS/UI/open3d_inspector.py", "KrakenOS/UI/services")
#: what a function must reach BEFORE its Toplevel to count as asking the shell first
SHELL_MARKS = ("shell_host_of(", '"show_flag_description"', '"show_report"')
#: Toplevel builders that do not ask the shell yet -> why. Exact: a port must delete its entry.
KNOWN_TK_POPUPS: dict = {}          # the last two became panels (bugs/0979, 0980); nothing is listed now


# ---- S -----------------------------------------------------------------------------------------
def toplevel_builders() -> dict:
    """"file.py:method" -> whether the method reaches a shell mark before its first Toplevel."""
    files = []
    for source in SOURCES:
        path = Path(source)
        files += sorted(path.glob("*.py")) if path.is_dir() else [path]
    found: dict = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        tree = ast.parse(text)
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            name = callee.attr if isinstance(callee, ast.Attribute) else getattr(callee, "id", "")
            if name != "Toplevel":
                continue
            holders = [f for f in functions if f.lineno <= node.lineno <= f.end_lineno]
            if not holders:
                continue
            outer = max(holders, key=lambda f: f.end_lineno - f.lineno)     # the method, not a closure
            before = "\n".join(lines[outer.lineno - 1:node.lineno - 1])
            key = f"{path.name}:{outer.name}"
            asks = any(mark in before for mark in SHELL_MARKS)
            found[key] = found.get(key, True) and asks
    return found


def static_checks() -> list:
    builders = toplevel_builders()
    tk_only = sorted(key for key, asks in builders.items() if not asks)
    unlisted = sorted(set(tk_only) - set(KNOWN_TK_POPUPS))
    stale = sorted(set(KNOWN_TK_POPUPS) - set(tk_only))
    shell_aware = sorted(key for key, asks in builders.items() if asks)
    return [["S", len(shell_aware) >= 5 and not unlisted and not stale,
             f"{len(builders)} Toplevel builders: {len(shell_aware)} ask the shell first "
             f"{[key.split(':')[1] for key in shell_aware]}; {len(tk_only)} listed as Tk-only; Tk-only and "
             f"not listed: {unlisted}; listed but no longer Tk-only (delete them): {stale}"]]


def pure_checks() -> list:
    from types import SimpleNamespace

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    target = Kraken3DInspector._step_overlay_resize_target
    free = target(["10", "20.5", "30"], None)
    cube = target(["25", "40"], SimpleNamespace(coupled_axes=(0, 2), free_axis=1))
    refusals = {}
    for texts in (["abc", "1", "1"], ["", "1", "1"], ["0", "1", "1"], ["-2", "1", "1"], ["nan", "1", "1"],
                  ["inf", "1", "1"]):
        try:
            target(texts, None)
            refusals[texts[0]] = "ACCEPTED"
        except ValueError as exc:
            refusals[texts[0]] = str(exc)
    numbers = "Dimensions must be numbers."
    positive = "Dimensions must be positive."
    expected = {"abc": numbers, "": numbers, "0": positive, "-2": positive, "nan": positive, "inf": positive}
    return [["P", free == ([10.0, 20.5, 30.0], None) and cube == ([25.0, 40.0, 25.0], 1) and refusals == expected,
             f"free {free}; coupled cube (axes 0+2 share the cross-section, 1 is the depth) {cube}; "
             f"refusals {refusals}"]]


# ---- Q + N -------------------------------------------------------------------------------------
def qt_runtime_checks() -> list:
    import tempfile
    import tkinter as tk

    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtTest import QTest

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost import host_of

    tk_windows: list = []
    tk_waits: list = []
    real_init = tk.Toplevel.__init__

    def counting_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        tk_windows.append(self)

    def no_wait(self, window=None):
        tk_waits.append(window)
        try:
            (window or self).destroy()          # a real wait would stop the shell for good
        except Exception:
            pass

    tk.Toplevel.__init__ = counting_init
    tk.Misc.wait_window = no_wait

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()
    for _ in range(40):
        app.processEvents()
    editor = window.editor
    inspector = view.inspector
    host = host_of(inspector)
    asked: list = []

    def answer(kind: str, value):
        def ask(title, prompt, **options):
            asked.append((kind, str(title), options.get("initialvalue"), str(prompt)))
            return value
        setattr(host, kind, ask)

    rows = []

    # Q1 -- the centred one-value prompt
    before_value = str(editor.field_value_var.get())
    answer("askstring", "7.25")
    inspector._quick_estimation_edit_field_value()
    value_ask = asked[-1] if asked else None
    value_after = str(editor.field_value_var.get())
    before_type = str(editor.field_type_var.get())
    answer("askstring", before_type)                # the same type again: asked, and nothing breaks
    inspector._quick_estimation_edit_field_type()
    type_ask = asked[-1]
    answer("askstring", None)                       # cancelled
    inspector._quick_estimation_edit_field_value()
    rows.append(["Q1", value_ask is not None and value_ask[:3] == ("askstring", "Object Field Value", before_value)
                 and value_after == "7.25" and type_ask[:3] == ("askstring", "Field Type", before_type)
                 and str(editor.field_value_var.get()) == "7.25" and len(asked) == 3,
                 f"field value asked {value_ask[:3] if value_ask else None} -> {value_after!r}; field type asked "
                 f"{type_ask[:3]}; a cancelled prompt left {editor.field_value_var.get()!r}"])

    # Q2 -- LED edge distance
    offset_z = float(editor._step_placement_offset_xyz("led")[2])
    live_before = max(float(getattr(editor, "led_object_edge_distance_mm", 0.0)) + offset_z, 0.0)
    if live_before <= 0.0:
        live_before = float(editor._default_led_object_edge_distance())
    del asked[:]
    answer("askfloat", 123.5)
    editor.set_led_edge_distance()
    led_ask = asked[-1] if asked else None
    live_after = float(editor.led_object_edge_distance_mm) + offset_z
    rows.append(["Q2", led_ask is not None and led_ask[:2] == ("askfloat", "LED Edge Distance")
                 and abs(float(led_ask[2]) - live_before) < 1e-9 and abs(live_after - 123.5) < 1e-9,
                 f"asked {led_ask[:2] if led_ask else None} prefilled {led_ask[2] if led_ask else None} (live "
                 f"distance {live_before:g}); typed 123.5 -> live distance {live_after:g}"])

    # Q3 -- Edit Thickness: the next prompt is prefilled with what was typed
    service = inspector._open3d_thickness_dimension_service()
    thickness_rows = []
    for row_index in range(len(editor.rows) - 1):
        del asked[:]
        answer("askfloat", None)
        service.edit_dimension(row_index)
        if not asked or asked[-1][1] != "Edit Thickness":
            continue
        start = float(asked[-1][2])
        cancelled_status = str(inspector.status_var.get())
        typed = round(start + 0.5, 6)
        answer("askfloat", typed)
        service.edit_dimension(row_index)
        answer("askfloat", None)
        service.edit_dimension(row_index)
        again = float(asked[-1][2])
        thickness_rows.append((row_index, start, typed, again, cancelled_status))
        if abs(again - typed) < 1e-6:
            break
    good = [item for item in thickness_rows if abs(item[3] - item[2]) < 1e-6]
    rows.append(["Q3", bool(good) and good[0][4] == "Thickness edit cancelled.",
                 f"rows tried (row, prefill, typed, next prefill): {[item[:4] for item in thickness_rows]}; a "
                 f"cancelled prompt said {thickness_rows[-1][4] if thickness_rows else None!r}"])

    # Q4 -- Resize Solid as a Qt row form
    labels = [label for label in ("camera", "lens", "led", "optical")
              if editor._step_overlay_original_extents(label) is not None]
    if not labels:
        rows.append(["Q4", True, "SKIP: no imported STEP body loaded (the vendor CAD is not in git)"])
    else:
        label = labels[0]
        seen: dict = {}

        def drive(values, *, expect_refusal: bool):
            dialog = window.last_model_form_dialog
            seen["title"] = dialog.windowTitle()
            seen["labels"] = [dialog.form.label_for(key) for key in dialog.widgets]
            seen["prefill"] = [dialog.widgets[key].text() for key in dialog.widgets]
            seen["modal"] = dialog.isModal()
            for key, value in zip(dialog.widgets, values):
                dialog.widgets[key].setText(str(value))
            host.showerror = lambda *a, **k: seen.setdefault("refused", str(a[1] if len(a) > 1 else k.get("message")))
            applied = dialog.apply_to_row()
            seen["applied"] = applied
            if not applied:
                dialog.reject()

        original = [float(v) for v in editor._step_overlay_original_extents(label)[:3]]
        coupled = editor._step_overlay_resize_axes(label) is not None
        count = 2 if coupled else 3
        QTimer.singleShot(0, lambda: drive(["0"] * count, expect_refusal=True))
        inspector._open_step_overlay_resize_popup(label)
        refused = dict(seen)
        spec_after_refusal = editor._step_resize_for_label(label)
        seen.clear()
        typed = [round(original[i] * 1.25, 3) for i in range(count)]
        QTimer.singleShot(0, lambda: drive(typed, expect_refusal=False))
        inspector._open_step_overlay_resize_popup(label)
        spec = editor._step_resize_for_label(label) or {}
        stored = [float(v) for v in (spec.get("target_extents") or []) if v]
        wanted_labels = ["Cross-section (mm)", "Depth (mm)"] if coupled else ["Width (mm)", "Height (mm)", "Depth (mm)"]
        rows.append(["Q4", seen.get("title", "").endswith("STEP — Resize Solid") and seen.get("labels") == wanted_labels
                     and seen.get("modal") is True and seen.get("applied") is True
                     and sorted(set(stored)) == sorted(set(float(v) for v in typed))
                     and refused.get("applied") is False and "positive" in str(refused.get("refused"))
                     and not spec_after_refusal,
                     f"{label}: form {seen.get('title')!r}, fields {seen.get('labels')}, prefilled "
                     f"{refused.get('prefill')}; sizes of 0 refused ({refused.get('refused')!r}) and stored "
                     f"{spec_after_refusal}; typed {typed} -> stored target extents {spec.get('target_extents')}"])

    # Q5 -- the flag description, not modal
    root = Path(tempfile.mkdtemp(prefix="flag0950_"))

    def flag(name: str):
        bundle = root / name
        bundle.mkdir()
        state = bundle / "state.json"
        state.write_text(json.dumps({"kind": "open3d"}), encoding="utf-8")
        payload: dict = {}
        inspector._open_flag_description_dialog(bundle_dir=bundle, state_path=state, flag_event_payload=payload)
        app.processEvents()
        return bundle, state, payload, window.last_flag_description_dialog

    bundle, state, payload, dialog = flag("flag_saved")
    shown = (dialog is not None and dialog.isVisible(), dialog.isModal(), dialog.windowTitle())
    dialog.text.setPlainText("the arrow points the wrong way\nsecond line")
    QTest.mouseClick(dialog.save_button, Qt.MouseButton.LeftButton)
    app.processEvents()
    saved = ((bundle / "description.txt").read_text(encoding="utf-8") if (bundle / "description.txt").exists() else None,
             json.loads(state.read_text(encoding="utf-8")).get("description"), payload.get("description"),
             dialog.isVisible())
    text = "the arrow points the wrong way\nsecond line"

    bundle_k, _state, payload_k, dialog = flag("flag_kept")
    QTest.mouseClick(dialog.keep_button, Qt.MouseButton.LeftButton)
    app.processEvents()
    kept = (bundle_k.exists(), (bundle_k / "description.txt").exists(), payload_k, str(inspector.status_var.get()))

    bundle_e, _state, payload_e, dialog = flag("flag_empty_closed")
    dialog.close()                                   # the window's close button, empty box
    app.processEvents()
    emptied = (bundle_e.exists(), payload_e.get("discarded"))

    bundle_t, _state, payload_t, dialog = flag("flag_typed_escaped")
    dialog.text.setPlainText("typed, then Escape")
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    app.processEvents()
    escaped = (bundle_t.exists(), (bundle_t / "description.txt").read_text(encoding="utf-8").strip()
               if (bundle_t / "description.txt").exists() else None, payload_t.get("discarded"))

    bundle_d, _state, payload_d, dialog = flag("flag_discarded")
    dialog.text.setPlainText("never mind")
    QTest.mouseClick(dialog.discard_button, Qt.MouseButton.LeftButton)
    app.processEvents()
    discarded = (bundle_d.exists(), payload_d.get("discarded"))
    rows.append(["Q5", shown == (True, False, "Flag: flag_saved") and saved == (text + "\n", text, text, False)
                 and kept[:3] == (True, False, {}) and "screenshot only" in kept[3]
                 and emptied == (False, True) and escaped == (True, "typed, then Escape", None)
                 and discarded == (False, True),
                 f"shown/modal/title {shown}; Save -> description.txt, state.json, event, window open: "
                 f"{(bool(saved[0]), saved[1] == text, saved[2] == text, saved[3])}; Keep -> bundle kept "
                 f"{kept[0]}, description.txt {kept[1]}; closing an empty box -> bundle exists {emptied[0]}, "
                 f"event discarded {emptied[1]}; Escape with typed text -> saved {escaped[1]!r}; Discard with "
                 f"typed text -> bundle exists {discarded[0]}"])

    # the inspector itself is a Tk object the shell hosts (bugs/0906); it is not a popup
    popups = [w for w in tk_windows if w is not inspector]
    rows.append(["N", not popups and not tk_waits,
                 f"Tk popups created {len(popups)}, waits on a Tk window {len(tk_waits)}"])
    return rows


# ---- T -----------------------------------------------------------------------------------------
def tk_runtime_checks() -> list:
    import tempfile
    import tkinter as tk
    import tkinter.simpledialog as simpledialog
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    made: list = []
    real_init = tk.Toplevel.__init__

    def recording_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        made.append(self)

    tk.Toplevel.__init__ = recording_init
    prompts: list = []
    for name in ("askstring", "askfloat", "askinteger"):
        setattr(simpledialog, name, lambda *a, _n=name, **_k: prompts.append(_n))

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    def press(window, text):
        next(b for b in widgets(window, ttk.Button) if str(b.cget("text")) == text).invoke()

    plan: list = []          # what the next waited-on window is told: (entry texts, button)
    waited_titles: list = []

    def scripted_wait(self, window=None):
        target = window or self
        waited_titles.append(str(target.title()))
        texts, button = plan.pop(0)
        for entry, text in zip(widgets(target, ttk.Entry), texts):
            entry.delete(0, "end")
            entry.insert(0, str(text))
        press(target, button)

    tk.Misc.wait_window = scripted_wait

    editor = KrakenLayoutEditor()
    editor.layout_files[SCENE.stem] = SCENE
    editor.load_layout_by_name(SCENE.stem)
    editor.open_3d_view()
    for _ in range(6):
        editor.update()
    inspector = getattr(editor, "_three_d_inspector", None)
    if inspector is None or not getattr(inspector, "available", False):
        return [["T", True, "SKIP: the embedded 3D inspector is unavailable"]]
    for _ in range(6):
        inspector.update()
        editor.update()

    def title_of(window) -> str:
        try:
            return str(window.title())
        except Exception:
            return "?"

    notes = {}
    # the centred prompt
    del made[:]
    plan.append((["7.25"], "OK"))
    inspector._quick_estimation_edit_field_value()
    notes["field value"] = (len(made) == 1 and waited_titles[-1:] == ["Object Field Value"]
                            and str(editor.field_value_var.get()) == "7.25")
    # LED edge distance
    del made[:]
    plan.append((["123.5"], "Save"))
    offset_z = float(editor._step_placement_offset_xyz("led")[2])
    editor.set_led_edge_distance()
    notes["LED edge distance"] = (len(made) == 1 and waited_titles[-1:] == ["LED Edge Distance"]
                                  and abs(float(editor.led_object_edge_distance_mm) + offset_z - 123.5) < 1e-9)
    # Edit Thickness (it does not wait: Enter / OK commits)
    service = inspector._open3d_thickness_dimension_service()
    thickness = None
    for row_index in range(len(editor.rows) - 1):
        del made[:]
        service.edit_dimension(row_index)
        if not made:
            continue
        window = made[-1]
        entry = widgets(window, ttk.Entry)[0]
        start = float(entry.get())
        typed = round(start + 0.5, 6)
        entry.delete(0, "end")
        entry.insert(0, str(typed))
        title = title_of(window)
        press(window, "OK")
        del made[:]
        service.edit_dimension(row_index)
        again = float(widgets(made[-1], ttk.Entry)[0].get()) if made else float("nan")
        service.cancel_inline_editor()
        thickness = (row_index, title, start, typed, again)
        if abs(again - typed) < 1e-4:
            break
    notes["Edit Thickness"] = (thickness is not None and thickness[1] == "Edit Thickness"
                               and abs(thickness[4] - thickness[3]) < 1e-4)
    # Resize Solid
    labels = [label for label in ("camera", "lens", "led", "optical")
              if editor._step_overlay_original_extents(label) is not None]
    resize = "SKIP: no imported STEP body"
    if labels:
        label = labels[0]
        original = [float(v) for v in editor._step_overlay_original_extents(label)[:3]]
        count = 2 if editor._step_overlay_resize_axes(label) is not None else 3
        typed = [round(original[i] * 1.25, 3) for i in range(count)]
        del made[:]
        plan.append((typed, "Resize"))
        inspector._open_step_overlay_resize_popup(label)
        spec = editor._step_resize_for_label(label) or {}
        stored = sorted({float(v) for v in (spec.get("target_extents") or []) if v})
        resize = (label, waited_titles[-1:], stored, sorted(set(typed)))
        notes["Resize Solid"] = (len(made) == 1 and waited_titles[-1].endswith("STEP — Resize Solid")
                                 and stored == sorted(set(float(v) for v in typed)))
    # the flag description (it does not wait)
    root = Path(tempfile.mkdtemp(prefix="flag0950_tk_"))
    bundle = root / "flag_saved"
    bundle.mkdir()
    state = bundle / "state.json"
    state.write_text(json.dumps({}), encoding="utf-8")
    payload: dict = {}
    del made[:]
    inspector._open_flag_description_dialog(bundle_dir=bundle, state_path=state, flag_event_payload=payload)
    popup = made[-1] if made else None
    flag_title = title_of(popup) if popup is not None else None
    if popup is not None:
        widgets(popup, tk.Text)[0].insert("1.0", "tk words")
        press(popup, "Save")
    saved = (bundle / "description.txt").read_text(encoding="utf-8").strip() if (bundle / "description.txt").exists() else None
    bundle2 = root / "flag_discarded"
    bundle2.mkdir()
    del made[:]
    inspector._open_flag_description_dialog(bundle_dir=bundle2, state_path=bundle2 / "state.json", flag_event_payload=None)
    if made:
        press(made[-1], "Discard")
    notes["flag description"] = (flag_title == "Flag: flag_saved" and saved == "tk words"
                                 and payload.get("description") == "tk words" and not bundle2.exists())
    failed = sorted(name for name, good in notes.items() if not good)
    return [["T", not failed and not prompts and len(notes) >= 4,
             f"Tk windows still open and take the typed value: {sorted(notes)}; failed {failed}; waited-on "
             f"windows {waited_titles}; Edit Thickness "
             f"(row, title, prefill, typed, next prefill) {thickness}; Resize Solid {resize}; "
             f"tkinter.simpledialog prompts {prompts}"]]


def _run(call: str) -> list:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_qt_inspector_popups import qt_runtime_checks, tk_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1500,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = static_checks() + pure_checks()
    if SCENE.exists():
        rows += _run("qt_runtime_checks()") + _run("tk_runtime_checks()")
    else:
        rows.append(["X", True, f"SKIP = {SCENE} absent"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
