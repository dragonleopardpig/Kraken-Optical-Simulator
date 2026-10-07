"""Guard for bugs/0978: the inline thickness editor is a Tk panel; the service decides, it does not draw.

Phase 7d of the Qt migration, the fourth service. `services/open3d_thickness_dimensions.py` imported
tkinter for the small window a click on a thickness dimension opens in the 3D view -- the row's
label, one entry, OK -- and for the routine that places it. Both are
`panels/thickness_inline_editor.py` now. The service keeps what is not a view's: which row, the
value it is prefilled with, a shell's own prompt, and what the typed value does.

That the window opens on a real scene and the typed value lands, in both shells, is phase 723's
(its Q3 and T). This guard holds what that one does not:

  S  the service imports and names no tkinter and builds no window; `edit_dimension` reaches
     `shell_host_of` BEFORE it asks for the Tk window; the panel module defines the window and its
     placing, and the service no longer has the placing routine
  M  the model under a shell, no display, on a three-row table: the shell's number prompt is asked
     with the row's label and the thickness to six figures; the typed value is applied to that
     row; a cancel and a value that is not finite each say so and apply nothing; the last row is
     refused; a re-anchored row is prefilled with its MEASURED distance and a trailing spacer with
     its real gap -- and the Tk window is never asked for
  T  the Tk window, in a real Tk editor's 3D view: its title, the row's label, the prefill, OK,
     Return / keypad Enter / Escape bound and the close button wired; a value that is no number,
     and "inf", each leave the window OPEN with a status line; a number closes it and changes the
     row; opening it again on another row leaves ONE window; closing it by the window's own close
     button cancels with a status line and changes nothing
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

RESULT_MARK = "THICKEDIT_RESULT "
SKIP_MARK = "THICKEDIT_SKIP "
SERVICE = Path("KrakenOS/UI/services/open3d_thickness_dimensions.py")
SCENE_NAME = "Doublet Lens"
TK_NAMES = {"tk", "ttk", "tkfont", "messagebox", "filedialog", "simpledialog"}


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def pure_checks() -> list:
    from KrakenOS.UI.panels import thickness_inline_editor as view
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService as Service

    def s():
        tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
        imports = sorted({node.lineno for node in ast.walk(tree)
                          if (node.__class__ is ast.Import and any(a.name.split(".")[0] == "tkinter" for a in node.names))
                          or (isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tkinter")})
        named = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in TK_NAMES})
        toplevels = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Call)
                        and (getattr(node.func, "attr", "") or getattr(node.func, "id", "")) == "Toplevel")
        source = inspect.getsource(Service.edit_dimension)
        shell_at, view_at = source.find("shell_host_of("), source.find("open_thickness_inline_editor(self, row_index, current)")
        defined = [name for name in ("open_thickness_inline_editor", "position_inline_editor") if callable(getattr(view, name, None))]
        return (imports == [] and named == [] and toplevels == 0 and 0 <= shell_at < view_at and len(defined) == 2
                and not hasattr(Service, "_position_inline_editor"),
                f"{SERVICE.name}: tkinter imports at lines {imports or 'none'}, tkinter names {named or 'none'}, Toplevels built "
                f"{toplevels}; `edit_dimension` reaches the shell (char {shell_at}) before the Tk window (char {view_at}); the "
                f"panel module defines {defined}; the service still has the placing routine: "
                f"{hasattr(Service, '_position_inline_editor')}")

    def m():
        from KrakenOS.UI.uihost import ScriptedUiHost

        class Status:
            def __init__(self) -> None:
                self.text = ""

            def set(self, value) -> None:
                self.text = str(value)

        opened: list = []
        real_open, view.open_thickness_inline_editor = view.open_thickness_inline_editor, lambda *args: opened.append(args)
        try:
            def service(answers, *, override=None, gap=None):
                rows = [SimpleNamespace(name="Object", surface="Object", thickness=100.0),
                        SimpleNamespace(name="Crown Front", surface="Standard", thickness=6.123456789),
                        SimpleNamespace(name="Image", surface="Image", thickness=0.0)]
                host = ScriptedUiHost(answers={"askfloat": list(answers)})
                made = Service.__new__(Service)
                made.inspector = SimpleNamespace(status_var=Status(), ui=host)
                made.editor = SimpleNamespace(rows=rows, _dimension_anchor_override_for_row=lambda index: override)
                made._inline_editor_window = None
                made._inline_editor_row_index = None
                made._inline_editor_committing = False
                made._trailing_spacer_gap_offset = dict(gap or {})
                made.applied = []
                made.apply_dimension_value = lambda row_index, value: made.applied.append((row_index, value))
                return made, host

            typed, host = service([12.5])
            typed.edit_dimension(1)
            asked = host.asked("askfloat")[0]
            cancelled, _ = service([None])
            cancelled.edit_dimension(1)
            infinite, _ = service([float("inf")])
            infinite.edit_dimension(1)
            last, last_host = service([1.0])
            last.edit_dimension(2)
            measured, measured_host = service([None], override={"ref_z": 300.0, "fixed_z": 87.4})
            measured.edit_dimension(0)
            spacer, spacer_host = service([None], gap={1: 2.5})
            spacer.edit_dimension(1)
        finally:
            view.open_thickness_inline_editor = real_open
        prefills = (asked[1].get("initialvalue"), measured_host.asked("askfloat")[0][1].get("initialvalue"),
                    spacer_host.asked("askfloat")[0][1].get("initialvalue"))
        return (tuple(asked[0]) == ("Edit Thickness", "S1: Crown Front\nThickness [mm]") and prefills[0] == 6.12346
                and typed.applied == [(1, 12.5)]
                and cancelled.applied == [] and cancelled.inspector.status_var.text == "Thickness edit cancelled."
                and infinite.applied == [] and infinite.inspector.status_var.text == "Thickness must be a finite number."
                and last.applied == [] and last_host.asked("askfloat") == []
                and last.inspector.status_var.text == "Thickness dimension: choose a non-terminal table row."
                and abs(prefills[1] - 212.6) < 1e-9 and abs(prefills[2] - 8.62346) < 1e-9 and opened == [],
                f"under a shell the prompt is asked as {tuple(asked[0])!r} prefilled {prefills[0]}; typing 12.5 applies "
                f"{typed.applied}; a cancel says {cancelled.inspector.status_var.text!r}, infinity "
                f"{infinite.inspector.status_var.text!r}, the last row {last.inspector.status_var.text!r}; a re-anchored row is "
                f"prefilled {prefills[1]:.6g} and a trailing spacer {prefills[2]:.6g}; the Tk window was asked for "
                f"{len(opened)} times")

    return _claims((("S", s), ("M", m)))


def tk_checks() -> list:
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.load_layout_by_name(SCENE_NAME)
    editor.open_3d_view()
    for _ in range(6):
        editor.update()
    inspector = getattr(editor, "_three_d_inspector", None)
    if inspector is None or not getattr(inspector, "available", False):
        return [["T", True, "SKIP: the embedded 3D inspector is unavailable"]]

    def pump() -> None:
        for _ in range(6):
            inspector.update()
            editor.update()

    pump()
    service = inspector._open3d_thickness_dimension_service()

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    def press(window, text) -> None:
        next(b for b in widgets(window, ttk.Button) if str(b.cget("text")) == text).invoke()

    def type_and_ok(window, text) -> tuple:
        entry = widgets(window, ttk.Entry)[0]
        entry.delete(0, "end")
        entry.insert(0, text)
        inspector.status_var.set("")
        press(window, "OK")
        pump()
        return bool(window.winfo_exists()), str(inspector.status_var.get())

    def claim_t():
        row = 1
        start = float(editor.rows[row].thickness)
        service.edit_dimension(row)
        pump()
        window = service._inline_editor_window
        shown = {"title": str(window.title()), "labels": [str(w.cget("text")) for w in widgets(window, ttk.Label)],
                 "prefill": widgets(window, ttk.Entry)[0].get(), "buttons": [str(b.cget("text")) for b in widgets(window, ttk.Button)],
                 "keys": [bool(window.bind(key)) for key in ("<Return>", "<KP_Enter>", "<Escape>")],
                 "close": bool(window.protocol("WM_DELETE_WINDOW")), "open": service.has_inline_editor()}
        not_a_number = type_and_ok(window, "abc")
        infinite = type_and_ok(window, "inf")
        unchanged = float(editor.rows[row].thickness)
        typed = round(start + 0.75, 6)
        accepted = type_and_ok(window, str(typed))
        after = (float(editor.rows[row].thickness), service.has_inline_editor())
        # opening it on one row and then on another leaves ONE window
        service.edit_dimension(row)
        pump()
        first = service._inline_editor_window
        service.edit_dimension(0)
        pump()
        second = service._inline_editor_window
        one_window = (not bool(first.winfo_exists()), bool(second.winfo_exists()), second is not first,
                      [str(w.cget("text")) for w in widgets(second, ttk.Label)][0])
        # the window's own close button cancels
        before_close = [float(r.thickness) for r in editor.rows]
        inspector.status_var.set("")
        second.tk.call(second.protocol("WM_DELETE_WINDOW"))
        pump()
        closed = (bool(second.winfo_exists()), service.has_inline_editor(), str(inspector.status_var.get()),
                  [float(r.thickness) for r in editor.rows] == before_close)
        label = service._row_label(row)
        return (shown == {"title": "Edit Thickness", "labels": [label, "Thickness [mm]"], "prefill": f"{start:.6g}",
                          "buttons": ["OK"], "keys": [True, True, True], "close": True, "open": True}
                and not_a_number == (True, "Thickness must be a finite number.") and infinite == (True, "Thickness must be a finite number.")
                and unchanged == start and accepted[0] is False and abs(after[0] - typed) < 1e-9 and after[1] is False
                and one_window == (True, True, True, service._row_label(0))
                and closed == (False, False, "Thickness edit cancelled.", True),
                f"the window {shown['title']!r} shows {shown['labels']}, prefilled {shown['prefill']!r}, buttons "
                f"{shown['buttons']}, keys bound {shown['keys']}, close button wired {shown['close']}; 'abc' and 'inf' leave "
                f"it open ({not_a_number[0]}, {infinite[0]}) saying {not_a_number[1]!r}; {typed} closes it and the row is "
                f"{after[0]} (was {start}); opened on row {row} then row 0 there is one window, on {one_window[3]!r}; its "
                f"close button leaves no window ({not closed[0]}), says {closed[2]!r} and changes nothing: {closed[3]}")

    return _claims((("T", claim_t),))


def _run(call: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_thickness_inline_editor_view import tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/VTK teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=600,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [[claim, False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
    return [[claim, False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    try:
        rows = pure_checks()
    except Exception as exc:
        rows = [["S", False, f"raised {type(exc).__name__}: {exc}"]]
    rows += _run("tk_checks()", "T")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
