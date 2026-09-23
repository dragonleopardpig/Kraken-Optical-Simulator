"""Display-free guard: the Qt UI host (bugs/0854, docs/design_qt_migration.md phase 2).

`QtUiHost` is the third implementation of the seam cut in 0851: the same calls model/controller
code already makes through `host_of(self)`, served by QTimer / QMessageBox / QFileDialog /
QInputDialog / the Qt clipboard instead of tkinter.

The Qt half runs in a SUBPROCESS on the offscreen platform, with no DISPLAY: a QApplication must
never be created inside the penta harness, which already holds a Tk interpreter and a live VTK
render window in-process. Without PySide6 the Qt sections report SKIP and the rest still runs.

  A  QtUiHost implements every UiHost method -- nothing is left inherited and raising
  B  importing `KrakenOS.UI.uihost` does NOT import PySide6 (a Tk run must not pull in Qt)
  C  qt_filter converts the file filters this repository really passes, keeping every glob
  Q1 timers: the callback gets its args, handles differ, after_cancel stops one, a callback may
     schedule another, and a timer freeing itself inside its own callback does not crash
  Q2 `after(ms)` with no callback blocks, which is what Tk's does
  Q3 update_idletasks repaints what asked to be repainted and runs NOTHING else -- in
     particular no scheduled `after` callback, which a plain processEvents does run (so Tk's
     no-re-entrancy guarantee survives the port)
  Q4 message dialogs map each Qt button onto the value tkinter returns
  Q5 file dialogs hand Qt the converted filter, the title and the start directory, and normalise
     the empty answer to "" / ()
  Q6 input dialogs return the value on OK and None on cancel, forwarding initialvalue/min/max
  Q7 REAL model code on a Qt host: the declared model variables come up as working variables, and
     `_autosave_plot` (services/layout_analysis_display.py) reads one, cancels its previous timer
     and schedules the next -- firing exactly once through QTimer
  Q8 clipboard round-trip
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
UI_DIR = Path("KrakenOS/UI")


def repo_filetypes() -> list[tuple[str, list]]:
    """Every `filetypes=[...]` literal the UI passes to a file dialog, read from the source."""
    found: list[tuple[str, list]] = []
    for path in sorted(UI_DIR.rglob("*.py")):
        if "archive" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg != "filetypes":
                    continue
                try:
                    value = ast.literal_eval(keyword.value)
                except (ValueError, TypeError, SyntaxError):
                    continue  # built from a constant, e.g. "*" + CELL_SUFFIX
                if isinstance(value, (list, tuple)) and value:
                    found.append((f"{path.name}:{node.lineno}", list(value)))
    return found


# --------------------------------------------------------------------------------------------
# The Qt half. Everything below runs in the subprocess started by _run_qt_subprocess().
# --------------------------------------------------------------------------------------------
def qt_runtime_checks() -> list[list]:
    """Drive a REAL QtUiHost against a real QApplication. Returns [name, ok, detail] rows."""
    import gc

    from PySide6.QtCore import QEventLoop
    from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

    from KrakenOS.UI.uihost import QtUiHost, host_of, qt_filter
    from KrakenOS.UI.uihost.values import ObservableValue

    rows: list[list] = []

    def row(name, ok, detail):
        rows.append([name, bool(ok), detail])

    app = QApplication.instance() or QApplication([])

    def pump(until, timeout=3.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not until():
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 10)
        return until()

    # ---- Q1 timers ---------------------------------------------------------------------------
    host = QtUiHost()
    fired: list[str] = []
    handle_a = host.after(0, fired.append, "a")
    handle_b = host.after(0, fired.append, "cancelled")
    host.after_cancel(handle_b)

    def nested():
        fired.append("n1")
        host.after(0, fired.append, "n2")

    host.after(1, nested)
    pump(lambda: "n2" in fired)

    # a callback that frees its own timer and collects: this is what crashes when the last
    # reference to a QObject is dropped from inside its own signal
    self_free: list[int] = []

    def free_self(index):
        gc.collect()
        self_free.append(index)

    for index in range(25):
        host.after(0, free_self, index)
    survived = pump(lambda: len(self_free) == 25)
    row("Q1", fired == ["a", "n1", "n2"] and handle_a != handle_b and survived,
        f"fired={fired}, distinct handles={handle_a != handle_b}, "
        f"{len(self_free)}/25 self-freeing timers fired without a crash")

    # ---- Q2 the blocking form ----------------------------------------------------------------
    start = time.monotonic()
    blocked = host.after(120)
    elapsed_ms = (time.monotonic() - start) * 1000.0
    row("Q2", blocked is None and elapsed_ms >= 110.0,
        f"after(120) with no callback blocked {elapsed_ms:.0f} ms and returned {blocked!r}")

    # ---- Q3 update_idletasks flushes redraws and runs nothing else ---------------------------
    painted: list[int] = []

    class Canvas(QWidget):
        def paintEvent(self, event):
            painted.append(1)

    canvas = Canvas()
    canvas.resize(80, 60)
    canvas.show()
    app.processEvents()
    painted.clear()

    idle_ran: list[str] = []
    host.after(0, idle_ran.append, "scheduled")
    canvas.update()
    host.update_idletasks()
    flushed, ran_during_idle = len(painted), list(idle_ran)
    pump(lambda: idle_ran, timeout=2.0)
    row("Q3", flushed == 1 and ran_during_idle == [] and idle_ran == ["scheduled"],
        f"update_idletasks repainted the widget ({flushed} paint event) and ran no scheduled "
        f"callback ({ran_during_idle}); the callback ran once the loop turned ({idle_ran})")

    # ---- Q4 messages -------------------------------------------------------------------------
    class FakeBox:
        StandardButton = QMessageBox.StandardButton
        answer = None
        calls: list[tuple] = []

        @classmethod
        def _record(cls, kind, parent, title, text, buttons=None):
            cls.calls.append((kind, title, text))
            return cls.answer

        @classmethod
        def question(cls, parent, title, text, buttons=None):
            return cls._record("question", parent, title, text, buttons)

        @classmethod
        def warning(cls, parent, title, text, buttons=None):
            return cls._record("warning", parent, title, text, buttons)

        @classmethod
        def information(cls, parent, title, text, buttons=None):
            return cls._record("information", parent, title, text, buttons)

        @classmethod
        def critical(cls, parent, title, text, buttons=None):
            return cls._record("critical", parent, title, text, buttons)

    class BoxHost(QtUiHost):
        def _box(self):
            return FakeBox

    box_host = BoxHost()
    button = QMessageBox.StandardButton
    answers = {}
    for name, method, value in (
        ("askyesno-yes", "askyesno", button.Yes), ("askyesno-no", "askyesno", button.No),
        ("askokcancel-ok", "askokcancel", button.Ok), ("askokcancel-cancel", "askokcancel", button.Cancel),
        ("askyesnocancel-yes", "askyesnocancel", button.Yes),
        ("askyesnocancel-cancel", "askyesnocancel", button.Cancel),
        ("askretrycancel-retry", "askretrycancel", button.Retry),
        ("askretrycancel-cancel", "askretrycancel", button.Cancel),
        ("askquestion-yes", "askquestion", button.Yes), ("askquestion-no", "askquestion", button.No),
    ):
        FakeBox.answer = value
        answers[name] = getattr(box_host, method)("Kraken", "Proceed?")
    FakeBox.calls.clear()
    shown = [box_host.showinfo("t", "m"), box_host.showwarning("t", "m"), box_host.showerror("t", "m")]
    kinds = [call[0] for call in FakeBox.calls]
    row("Q4", answers == {"askyesno-yes": True, "askyesno-no": False, "askokcancel-ok": True,
                          "askokcancel-cancel": False, "askyesnocancel-yes": True,
                          "askyesnocancel-cancel": None, "askretrycancel-retry": True,
                          "askretrycancel-cancel": False, "askquestion-yes": "yes",
                          "askquestion-no": "no"}
        and shown == ["ok", "ok", "ok"] and kinds == ["information", "warning", "critical"],
        f"button -> tkinter value: {answers}; show* returned {shown} through {kinds}")

    # ---- Q5 files ----------------------------------------------------------------------------
    class FakeFileDialog:
        calls: list[tuple] = []
        open_one = ("/tmp/lens.step", "STEP (*.step *.stp)")
        open_many: tuple = ([], "")
        save_one = ("", "")
        directory = ""

        @classmethod
        def getOpenFileName(cls, parent, caption, directory, filt):
            cls.calls.append(("open", caption, directory, filt))
            return cls.open_one

        @classmethod
        def getOpenFileNames(cls, parent, caption, directory, filt):
            cls.calls.append(("open-many", caption, directory, filt))
            return cls.open_many

        @classmethod
        def getSaveFileName(cls, parent, caption, directory, filt):
            cls.calls.append(("save", caption, directory, filt))
            return cls.save_one

        @classmethod
        def getExistingDirectory(cls, parent, caption, directory):
            cls.calls.append(("dir", caption, directory, None))
            return cls.directory

    class FileHost(QtUiHost):
        def _dialog(self):
            return FakeFileDialog

    file_host = FileHost()
    filetypes = [("STEP", "*.step *.stp"), ("All files", "*")]
    opened = file_host.askopenfilename(title="Import STEP", initialdir="/data", filetypes=filetypes)
    many = file_host.askopenfilenames(title="Import", initialdir="/data", filetypes=filetypes)
    saved = file_host.asksaveasfilename(title="Save", initialdir="/data", filetypes=filetypes)
    folder = file_host.askdirectory(title="Choose folder", initialdir="/data")
    expected_filter = qt_filter(filetypes)
    row("Q5", opened == "/tmp/lens.step" and many == () and saved == "" and folder == ""
        and FakeFileDialog.calls[0] == ("open", "Import STEP", "/data", expected_filter)
        and all(call[2] == "/data" for call in FakeFileDialog.calls),
        f"Qt received {FakeFileDialog.calls[0]}; empty answers normalised to "
        f"{many!r} / {saved!r} / {folder!r}")

    # ---- Q6 input ----------------------------------------------------------------------------
    class FakeInput:
        calls: list[tuple] = []
        ok = True

        @classmethod
        def getText(cls, parent, title, prompt, text=""):
            cls.calls.append(("text", title, prompt, text))
            return "L1 assembly", cls.ok

        @classmethod
        def getInt(cls, parent, title, prompt, value=0, minimum=0, maximum=0):
            cls.calls.append(("int", title, prompt, (value, minimum, maximum)))
            return 7, cls.ok

        @classmethod
        def getDouble(cls, parent, title, prompt, value=0.0, minimum=0.0, maximum=0.0, decimals=1):
            cls.calls.append(("double", title, prompt, (value, minimum, maximum, decimals)))
            return 12.5, cls.ok

    class InputHost(QtUiHost):
        def _input(self):
            return FakeInput

    input_host = InputHost()
    got_ok = [input_host.askstring("Name", "Element name", initialvalue="L1"),
              input_host.askinteger("Rays", "How many?", initialvalue=3, minvalue=1, maxvalue=99),
              input_host.askfloat("Shift", "mm", initialvalue=1.5, minvalue=-10.0, maxvalue=10.0)]
    forwarded = list(FakeInput.calls)
    FakeInput.ok = False
    got_cancel = [input_host.askstring("Name", "Element name"),
                  input_host.askinteger("Rays", "How many?"),
                  input_host.askfloat("Shift", "mm")]
    row("Q6", got_ok == ["L1 assembly", 7, 12.5] and got_cancel == [None, None, None]
        and forwarded[0][3] == "L1" and forwarded[1][3] == (3, 1, 99)
        and forwarded[2][3][:3] == (1.5, -10.0, 10.0),
        f"OK -> {got_ok}, cancel -> {got_cancel}; initialvalue/min/max forwarded as "
        f"{forwarded[1][3]} and {forwarded[2][3][:3]}")

    # ---- Q7 REAL model code on a Qt host -----------------------------------------------------
    from types import MethodType, SimpleNamespace

    from KrakenOS.UI.model_variables import MODEL_VARIABLES, ensure_model_variables
    from KrakenOS.UI.services.layout_analysis_display import LayoutAnalysisDisplayMixin

    owner = SimpleNamespace(ui=QtUiHost())
    created = ensure_model_variables(owner)
    kinds_ok = all(isinstance(getattr(owner, name), ObservableValue)
                   and getattr(owner, name).kind == kind
                   and getattr(owner, name).get() == ObservableValue(kind, value).get()
                   for name, (kind, value) in MODEL_VARIABLES.items())

    autosaves: list[float] = []
    owner.auto_save_plot_var = owner.ui.boolean_var(value=False)
    owner._autosave_after_id = None
    owner._do_autosave_plot = lambda: autosaves.append(time.monotonic())
    owner._autosave_plot = MethodType(LayoutAnalysisDisplayMixin._autosave_plot, owner)

    owner._autosave_plot()                      # the variable says no: nothing is scheduled
    off_id = owner._autosave_after_id
    owner.auto_save_plot_var.set(True)
    owner._autosave_plot()                      # schedules
    first_id = owner._autosave_after_id
    owner._autosave_plot()                      # cancels the first, schedules the second
    second_id = owner._autosave_after_id
    pump(lambda: len(autosaves) >= 1, timeout=3.0)
    pump(lambda: len(autosaves) >= 2, timeout=1.0)
    row("Q7", host_of(owner) is owner.ui and len(created) == len(MODEL_VARIABLES) and kinds_ok
        and off_id is None and first_id is not None and second_id != first_id
        and len(autosaves) == 1,
        f"{len(created)} declared model variables came up on the Qt host (kinds/defaults "
        f"{'match' if kinds_ok else 'DIFFER'}); _autosave_plot scheduled {first_id!r} then "
        f"replaced it with {second_id!r} and fired {len(autosaves)} time(s)")

    # ---- Q8 clipboard ------------------------------------------------------------------------
    host.clipboard_set("EFL 85.0 mm")
    clipped = host.clipboard_get()
    row("Q8", clipped == "EFL 85.0 mm", f"clipboard round-trip returned {clipped!r}")

    return rows


def _run_qt_subprocess() -> tuple[str, list[list]]:
    """Run qt_runtime_checks() in a fresh interpreter on the offscreen platform."""
    driver = (
        "import json, sys\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0854_qt_ui_host import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=300, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Qt subprocess", False, "timed out after 300 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["PySide6", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-4:]
    return "error", [["Qt subprocess", False,
                      f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.uihost import QtUiHost, UiHost, qt_filter

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- A the interface is fully implemented ------------------------------------------------
    interface = [name for name, value in vars(UiHost).items()
                 if callable(value) and not name.startswith("__")]
    missing = [name for name in interface if getattr(QtUiHost, name) is getattr(UiHost, name)]
    ok(interface and not missing,
       f"A: QtUiHost implements all {len(interface)} UiHost methods"
       + (f" -- still inherited: {missing}" if missing else ""))

    # ---- B a Tk run does not pull in Qt ------------------------------------------------------
    probe = ("import sys\n"
             "import KrakenOS.UI.uihost as uihost\n"
             "print(sorted(m for m in sys.modules if m.split('.')[0] in ('PySide6', 'PyQt5', 'shiboken6')))\n")
    proc = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=180)
    loaded = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "<no output>"
    ok(proc.returncode == 0 and loaded == "[]",
       f"B: importing KrakenOS.UI.uihost loaded no Qt binding ({loaded})")

    # ---- C the repository's own file filters -------------------------------------------------
    literals = repo_filetypes()
    bad: list[str] = []
    for where, filetypes in literals:
        converted = qt_filter(filetypes)
        for label, patterns in filetypes:
            globs = patterns.split() if isinstance(patterns, str) else [str(p) for p in patterns]
            if f"{label} (" not in converted or not all(glob in converted for glob in globs):
                bad.append(f"{where} {label!r}")
    dotted = qt_filter([("Python layout", ".py")])
    ok(len(literals) >= 10 and not bad and dotted == "Python layout (*.py)",
       f"C: {len(literals)} real filetypes literals convert with every label and glob intact"
       + (f" -- wrong: {bad[:3]}" if bad else "") + f"; a bare extension becomes {dotted!r}")

    # ---- Q the Qt host itself, in its own process --------------------------------------------
    status, rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q1-Q8: PySide6 is not installed -- {rows[0][2]}")
    else:
        for name, passed, detail in rows:
            ok(passed, f"{name}: {detail}")

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
