"""Guard for the lens-drawing surface properties and the PDF lens drawing in both shells (bugs/0945).

The dialog was a Tk window whose logic lived in its closures, and the PDF export asked with Tk's
file dialog: the Qt shell could do neither. It is now `lens_drawing_session` rendered by a Tk view
and a Qt dialog. On the two-arm doublets example (8 lens surfaces):

  S  neither the panel nor the session calls a tkinter dialog: every question goes through the host
  O  Edit -> "Lens Drawing Surface Properties" opens the Qt dialog, modal, one row per lens surface
     (the model's own list) with 7 + 14 columns and the session's six buttons
  Q  REAL typing into its fields: a negative clear aperture is refused (a host message, the status
     says why, nothing written); valid values Apply into the rows' DrawingProperties; Save JSON
     writes the sidecar; Clear empties the fields; Load JSON brings them back; Apply & Close closes
     the dialog and the command reports success
  P  File -> "Export Lens Drawing": Cancel Export reports "cancelled" and writes nothing; Continue
     Without Changes asks for the PDF through the host and writes it
  T  the same script in the Tk window leaves the same DrawingProperties, and the two shells' JSON
     sidecars are byte-identical
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_MARK = "QTLENSDRAW_RESULT "
SKIP_MARK = "QTLENSDRAW_SKIP "
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
#: (field index in row-major order, text): surface 1's clear aperture, R and CT tolerance; surface 2's
TYPED = ((0, "24"), (1, "+/-0.035"), (14, "22.5"))
BAD = (0, "-3")
LATE = (2, "+/-0.1")


def static_checks() -> list:
    import re

    sources = {name: Path(f"KrakenOS/UI/{name}").read_text(encoding="utf-8")
               for name in ("panels/main_lens_drawing_dialogs.py", "lens_drawing_session.py")}
    direct = {name: re.findall(r"\b(?:messagebox|filedialog|simpledialog)\.\w+\(", text)
              for name, text in sources.items()}
    return [["S", not any(direct.values()), f"direct tkinter dialog calls: {direct}"]]


def _props(editor) -> list:
    return [[index, dict((row.advanced or {}).get("DrawingProperties", {}) or {})]
            for index, row in enumerate(editor.rows) if (row.advanced or {}).get("DrawingProperties")]


def qt_runtime_checks(folder: str) -> list:
    import webbrowser

    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtTest import QTest

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost import host_of

    folder = Path(folder)
    opened: list = []
    webbrowser.open = lambda url, *a, **k: opened.append(Path(url).name) or True
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.load_layout_path(LAYOUT)
    app.processEvents()
    editor, actions = window.editor, window.action_manager.actions
    host = host_of(window)
    said: list = []
    answers = {"save": "", "open": ""}
    for name in ("showinfo", "showwarning", "showerror"):
        setattr(host, name, (lambda n: lambda title=None, message=None, **_k: said.append((n, str(title), str(message))))(name))
    host.asksaveasfilename = lambda **kw: (said.append(("save", kw.get("title"), "")), answers["save"])[1]
    host.askopenfilename = lambda **kw: (said.append(("open", kw.get("title"), "")), answers["open"])[1]
    rows: list = []
    seen: dict = {}

    def edits(dialog) -> list:
        return [dialog.edits[key] for key in sorted(dialog.edits, key=lambda k: (dialog.session.surface_indices.index(k[0]),
                                                                             [f.key for f in dialog.session.fields()].index(k[1])))]

    def type_into(dialog, index, text) -> None:
        edit = edits(dialog)[index]
        edit.setFocus()
        edit.selectAll()
        QTest.keyClick(edit, Qt.Key.Key_Delete)
        QTest.keyClicks(edit, text)

    def drive_properties() -> None:
        dialog = window.last_lens_drawing_dialog
        session = dialog.session
        seen["shape"] = (dialog.isModal(), dialog.isVisible(), dialog.table.rowCount(), dialog.table.columnCount(),
                         sorted(dialog.buttons))
        type_into(dialog, *BAD)
        dialog.buttons["Apply"].click()
        seen["bad"] = (session.status, list(said), _props(editor))
        said.clear()
        for index, text in TYPED:
            type_into(dialog, index, text)
        dialog.buttons["Apply"].click()
        seen["applied"] = _props(editor)
        answers["save"] = str(folder / "qt_props.json")
        dialog.buttons["Save JSON..."].click()
        dialog.buttons["Clear"].click()
        seen["cleared"] = [edit.text() for edit in edits(dialog)][:15]
        answers["open"] = str(folder / "qt_props.json")
        dialog.buttons["Load JSON..."].click()
        seen["loaded"] = [edit.text() for edit in edits(dialog)][:15]
        type_into(dialog, *LATE)
        dialog.buttons["Apply && Close"].click()

    QTimer.singleShot(0, drive_properties)
    actions["lens_drawing_properties"].trigger()
    app.processEvents()
    dialog = window.last_lens_drawing_dialog
    shape = seen.get("shape")
    from KrakenOS.UI.lens_drawing_session import lens_surface_indices

    surfaces = len(lens_surface_indices(editor.rows))
    rows.append(["O", shape is not None and shape[0] and shape[1] and surfaces >= 4 and shape[2] == surfaces
                 and shape[3] == 21 and len(shape[4]) == 6,
                 f"modal, shown, rows x columns, buttons: {shape} ({surfaces} lens surfaces in the model)"])
    bad = seen.get("bad", ("", [], None))
    loaded = seen.get("loaded", [])
    rows.append(["Q", "must be positive" in bad[0] and any(entry[0] == "showerror" for entry in bad[1]) and bad[2] == []
                 and len(seen.get("applied", [])) == 2 and (folder / "qt_props.json").exists()
                 and not any(seen.get("cleared", ["x"])) and loaded[:2] == ["24", "+/-0.035"] and loaded[14] == "22.5"
                 and dialog is not None and not dialog.isVisible() and dialog.session.result_ok
                 and _props(editor)[0][1].get("thickness_tolerance") == "+/-0.1",
                 f"bad value -> status {bad[0][:60]!r}, messages {[e[0] for e in bad[1]]}, rows written {bad[2]}; "
                 f"applied {seen.get('applied')}; cleared all: {not any(seen.get('cleared', ['x']))}; loaded back "
                 f"{loaded[:2]}+{loaded[14:15]}; closed {dialog is not None and not dialog.isVisible()}, "
                 f"result {dialog.session.result_ok if dialog else None}; final {_props(editor)}"])

    # P -- the PDF export: cancel, then continue without changes
    def press(label):
        def run():
            window.last_lens_drawing_dialog.buttons[label].click()
        return run

    said.clear()
    QTimer.singleShot(0, press("Cancel Export"))
    actions["export_lens_drawing"].trigger()
    app.processEvents()
    cancelled = editor.status_var.get()
    asked_on_cancel = [entry for entry in said if entry[0] == "save"]
    answers["save"] = str(folder / "qt_drawing.pdf")
    QTimer.singleShot(0, press("Continue Without Changes"))
    actions["export_lens_drawing"].trigger()
    app.processEvents()
    pdf = folder / "qt_drawing.pdf"
    rows.append(["P", cancelled == "Lens drawing export cancelled." and not asked_on_cancel
                 and pdf.exists() and pdf.stat().st_size > 1000 and opened == ["qt_drawing.pdf"]
                 and editor.status_var.get() == "Lens drawing exported: qt_drawing.pdf",
                 f"cancel -> {cancelled!r} (asked for a file: {bool(asked_on_cancel)}); continue -> "
                 f"{editor.status_var.get()!r}, PDF {pdf.stat().st_size if pdf.exists() else 0} bytes, opened {opened}"])
    return rows + [["_props", True, json.dumps(_props(editor))]]


def tk_runtime_checks(folder: str) -> list:
    import tkinter as tk
    import tkinter.filedialog as tk_filedialog
    import tkinter.messagebox as tk_messagebox
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    folder = Path(folder)
    for name in ("showinfo", "showwarning", "showerror"):
        setattr(tk_messagebox, name, lambda *a, **k: None)
    answers = {"save": str(folder / "tk_props.json"), "open": str(folder / "tk_props.json")}
    tk_filedialog.asksaveasfilename = lambda **k: answers["save"]
    tk_filedialog.askopenfilename = lambda **k: answers["open"]
    editor = KrakenLayoutEditor()
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    editor.update()

    def widgets(root, kind):
        found = []

        def walk(widget):
            if isinstance(widget, kind):
                found.append(widget)
            for child in widget.winfo_children():
                walk(child)
        walk(root)
        return found

    def entries(window):
        return sorted(widgets(window, ttk.Entry),
                      key=lambda e: (int(e.master.grid_info()["row"]), int(e.master.grid_info()["column"])))

    def set_entry(window, index, text):
        entry = entries(window)[index]
        entry.delete(0, tk.END)
        entry.insert(0, text)

    def click(window, text):
        next(b for b in widgets(window, ttk.Button) if b.cget("text") == text).invoke()

    def script(window):
        editor.update()
        set_entry(window, *BAD)
        click(window, "Apply")
        for index, text in TYPED:
            set_entry(window, index, text)
        click(window, "Apply")
        click(window, "Save JSON...")
        click(window, "Clear")
        click(window, "Load JSON...")
        set_entry(window, *LATE)
        click(window, "Apply && Close")

    editor.wait_window = script
    ok = editor._open_lens_drawing_surface_properties_dialog()
    return [["_props", bool(ok), json.dumps(_props(editor))]]


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
        "from KrakenOS.UI.validate_qt_lens_drawing import qt_runtime_checks, tk_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Qt/Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"{call}: exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    folder = tempfile.mkdtemp(prefix="qt_lens_drawing_")
    qt_rows = _run(f"qt_runtime_checks({folder!r})")
    tk_rows = _run(f"tk_runtime_checks({folder!r})")
    qt_props = next((d for k, _o, d in qt_rows if k == "_props"), None)
    tk_props = next((d for k, _o, d in tk_rows if k == "_props"), None)
    tk_ok = next((o for k, o, _d in tk_rows if k == "_props"), False)
    qt_json, tk_json = Path(folder) / "qt_props.json", Path(folder) / "tk_props.json"
    same_json = qt_json.exists() and tk_json.exists() and qt_json.read_bytes() == tk_json.read_bytes()
    rows = static_checks() + [r for r in qt_rows if r[0] != "_props"] + [r for r in tk_rows if r[0] != "_props"]
    rows.append(["T", tk_ok and qt_props is not None and qt_props == tk_props and same_json,
                 f"Tk returned {tk_ok}; the shells' DrawingProperties match: {qt_props == tk_props} ({tk_props}); "
                 f"byte-identical JSON sidecars: {same_json}"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
