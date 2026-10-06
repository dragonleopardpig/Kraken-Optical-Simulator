"""Guard for bugs/0971: both interfaces stay, and the user chooses which one opens.

The user, 2026-10-06: "I would like to have both TK and QT available, let user to choose his usage
preference." `python -m KrakenOS.UI` starts the preferred interface; the preference is a per-user
file, set from either interface with Interface Preference... or by a question asked once.

Every claim runs with ``KRAKEN_CONFIG_DIR`` pointed at a temp folder -- the real preferences file
is never read or written.

  P1 the preferences file: nothing saved reads as nothing; a value is saved and read back, another
     key survives it, None removes it; a file that is not JSON reads as nothing and is saved over;
     a folder that cannot be made is REPORTED, not raised
  P2 which interface starts: the command line (``--shell qt``, ``--shell=tk``, ``--qt``, ``--tk``)
     beats the environment, which beats the saved preference; the request is REMOVED from the
     arguments passed on; nothing set decides nothing; an unknown name on the command line is
     refused, in the environment or the file it is ignored; an interface that cannot run here falls
     back to the other with a note, and with neither there is a refusal
  P3 the first-run question: both offered, Qt first; "remember" saves the answer and the next start
     reads it; unticked, nothing is saved; closing the question starts nothing; with one interface
     installed nothing is asked
  P4 the form both interfaces show: it offers the interfaces that can run here and "ask me"; it
     opens on the saved choice; Apply writes the file -- read back THROUGH the start decision -- and
     "ask me" removes it; an unknown choice is refused
  L  the launcher, run as the real command with nothing started (a dry run): with nothing set it
     says it would ask -- and asks nothing; it reports the interface and passes the layout on for
     the command line, the environment and the saved preference; an unknown interface exits 2
     with a message. And the dispatch: "qt" runs the Qt entry with the arguments, "tk" the Tk
     entry with the layout
  W  the first-run window itself (Tk): a radio per interface, Qt selected, "Remember my choice"
     ticked; Open returns the selection; closing it returns no interface
  T  the Tk interface: File > Interface Preference... is there, and it opens the form's window with
     the choices; Apply in that window writes the file
  Q  the Qt interface: the action is in the Help dropdown, opens a Qt dialog (no Tk window) on the
     saved choice and naming the running interface; a real click on Apply writes the file
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_MARK = "INTERFACEPREF_RESULT "
SKIP_MARK = "INTERFACEPREF_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")


def _fresh_config() -> Path:
    folder = Path(tempfile.mkdtemp(prefix="krakenpref0971_"))
    os.environ["KRAKEN_CONFIG_DIR"] = str(folder)
    return folder


def pure_checks() -> list:
    from types import SimpleNamespace

    from KrakenOS.UI import launcher, user_preferences
    from KrakenOS.UI.row_forms import FormRefused
    from KrakenOS.UI.row_forms import interface_preference as form_module
    from KrakenOS.UI.uihost import ScriptedUiHost

    rows = []
    both = {"qt": "", "tk": ""}
    claim = "P1"
    try:
        _pure_claims(rows, both, launcher, user_preferences, form_module, FormRefused, SimpleNamespace, ScriptedUiHost)
    except Exception as exc:
        claim = ("P1", "P2", "P3", "P4")[min(len(rows), 3)]
        rows.append([claim, False, f"raised {type(exc).__name__}: {exc}"])
    return rows


def _pure_claims(rows, both, launcher, user_preferences, form_module, FormRefused, SimpleNamespace, ScriptedUiHost) -> None:
    # ---- P1
    folder = _fresh_config()
    empty = user_preferences.load()
    saved = user_preferences.set_value("shell", "qt")
    user_preferences.set_value("other", 7)
    after = dict(user_preferences.load())
    user_preferences.set_value("shell", None)
    removed = dict(user_preferences.load())
    user_preferences.path().write_text("{not json", encoding="utf-8")
    try:
        corrupt = user_preferences.load()
    except Exception as exc:
        corrupt = f"RAISED {type(exc).__name__}"
    over = user_preferences.set_value("shell", "tk")
    recovered = dict(user_preferences.load())
    blocker = folder / "a_file"
    blocker.write_text("x", encoding="utf-8")
    os.environ["KRAKEN_CONFIG_DIR"] = str(blocker / "below")
    try:
        refused = user_preferences.set_value("shell", "qt")
    except Exception as exc:
        refused = ""
        corrupt = f"an unwritable folder RAISED {type(exc).__name__}"
    unread = user_preferences.load()
    rows.append(["P1", empty == {} and saved == "" and after == {"shell": "qt", "other": 7} and removed == {"other": 7}
                 and corrupt == {} and over == "" and recovered == {"shell": "tk"} and bool(refused) and unread == {}
                 and user_preferences.path().name == "preferences.json",
                 f"nothing saved reads {empty}; saved then read {after}; None removes: {removed}; a file that is not JSON "
                 f"reads {corrupt} and is saved over: {recovered}; a folder that cannot be made says "
                 f"{refused.split(':')[0]!r} and reads {unread}"])

    # ---- P2
    folder = _fresh_config()
    R = launcher.resolve_shell
    forms = [R(["prog", "--shell", "qt", "a.py"], {}, ""), R(["prog", "--shell=tk", "a.py"], {}, ""),
             R(["prog", "a.py", "--qt"], {}, ""), R(["prog", "--tk"], {}, "")]
    precedence = [R(["prog", "--tk"], {"KRAKEN_UI_SHELL": "qt"}, "qt")[:2], R(["prog"], {"KRAKEN_UI_SHELL": "tk"}, "qt")[:2],
                  R(["prog"], {}, "qt")[:2], R(["prog", "a.py"], {}, "")]
    ignored = [R(["prog"], {"KRAKEN_UI_SHELL": "gtk"}, "")[0], R(["prog"], {}, "curses")[0]]
    try:
        R(["prog", "--shell", "gtk"], {}, "")
        refusal = ""
    except launcher.ShellRefused as exc:
        refusal = str(exc)
    fallback = launcher.runnable("qt", {"qt": "PySide6 is not installed", "tk": ""})
    straight = launcher.runnable("tk", both)
    try:
        launcher.runnable("qt", {"qt": "no", "tk": "no"})
        none_left = ""
    except launcher.ShellRefused as exc:
        none_left = str(exc)
    rows.append(["P2", forms == [("qt", "the command line", ["prog", "a.py"]), ("tk", "the command line", ["prog", "a.py"]),
                                 ("qt", "the command line", ["prog", "a.py"]), ("tk", "the command line", ["prog"])]
                 and precedence == [("tk", "the command line"), ("tk", "KRAKEN_UI_SHELL"), ("qt", "your saved preference"),
                                    ("", "", ["prog", "a.py"])]
                 and ignored == ["", ""] and "gtk" in refusal and fallback[0] == "tk" and "PySide6" in fallback[1]
                 and straight == ("tk", "") and "no interface can run here" in none_left,
                 f"the four spellings give {[f[0] for f in forms]} and pass on {forms[0][2]}; command line over environment "
                 f"over saved: {[p[:2] for p in precedence[:3]]}; nothing set: {precedence[3]}; an unknown name in the "
                 f"environment or the file is ignored {ignored}, on the command line refused ({refusal!r}); Qt asked for "
                 f"without PySide6 -> {fallback[0]!r} ({fallback[1][:44]}...); neither: {none_left[:26]!r}"])

    # ---- P3
    folder = _fresh_config()
    asked: list = []

    def ask(answer):
        return lambda offered, default: (asked.append((list(offered), default)), answer)[1]

    remembered = launcher.first_run_choice(ask(("tk", True)), both)
    then = launcher.resolve_shell(["prog"], {})[:2]
    folder = _fresh_config()
    once = launcher.first_run_choice(ask(("qt", False)), both)
    not_saved = user_preferences.load()
    closed = launcher.first_run_choice(ask(("", True)), both)
    still_nothing = user_preferences.load()
    count = len(asked)
    only = launcher.first_run_choice(ask(("qt", True)), {"qt": "PySide6 is not installed", "tk": ""})
    rows.append(["P3", asked[0] == (["qt", "tk"], "qt") and remembered == "tk" and then == ("tk", "your saved preference")
                 and once == "qt" and not_saved == {} and closed == "" and still_nothing == {}
                 and only == "tk" and len(asked) == count,
                 f"asked {asked[0]}; an answer with 'remember' is saved and the next start reads {then}; without, "
                 f"{once!r} opens and the file holds {not_saved}; closing the question -> {closed!r}; with one interface "
                 f"installed it opens {only!r} and asks {len(asked) - count}x"])

    # ---- P4
    folder = _fresh_config()
    owner = SimpleNamespace(ui=ScriptedUiHost())
    form = form_module.build_interface_preference_form(owner)
    field = form.field("shell")
    offered = list(field.choices)
    opened_on = form.values["shell"]
    message = form.apply({"shell": "Tk interface"})
    through_start = launcher.resolve_shell(["prog"], {})[:2]
    reopened = form_module.build_interface_preference_form(owner).values["shell"]
    form.apply({"shell": form_module.ASK})
    asks_again = (user_preferences.load(), launcher.resolve_shell(["prog"], {})[0])
    try:
        form.apply({"shell": "GTK interface"})
        refused_choice = ""
    except FormRefused as exc:
        refused_choice = str(exc)
    rows.append(["P4", offered == ["Qt interface", "Tk interface", form_module.ASK] and opened_on == form_module.ASK
                 and "Tk interface" in message and through_start == ("tk", "your saved preference")
                 and reopened == "Tk interface" and asks_again == ({}, "") and bool(refused_choice)
                 and form_module.running_shell(owner) == "" and form.title == "Interface Preference",
                 f"the form offers {offered} and opens on {opened_on!r}; Apply says {message!r} and the start decision reads "
                 f"{through_start}; reopened it shows {reopened!r}; 'ask me' leaves {asks_again}; an unknown choice: "
                 f"{refused_choice!r}"])


def launcher_checks() -> list:
    from KrakenOS.UI import launcher, user_preferences

    folder = _fresh_config()

    def dry(arguments, environment=None) -> tuple:
        env = dict(os.environ)
        env.pop("KRAKEN_UI_SHELL", None)
        env.update(KRAKEN_CONFIG_DIR=str(folder), KRAKEN_LAUNCHER_DRY_RUN="1")
        env.update(environment or {})
        try:
            proc = subprocess.run([sys.executable, "-m", "KrakenOS.UI", *arguments], capture_output=True, text=True,
                                  timeout=90, env=env, cwd=str(Path.cwd()))
        except subprocess.TimeoutExpired:
            return -1, "TIMED OUT (a dry run must start nothing and ask nothing)", "", [""]
        line = next((text for text in proc.stdout.splitlines() if "dry run:" in text), "")
        said = next((text for text in proc.stdout.splitlines() if "opening the" in text), "")
        return proc.returncode, line.split("dry run: ", 1)[-1], said, proc.stderr.strip().splitlines()[-1:] or [""]

    nothing_set = dry([str(SCENE)])              # nothing decides: a dry run says so and asks nothing
    by_flag = dry(["--shell", "tk", str(SCENE)])
    by_environment = dry([str(SCENE)], {"KRAKEN_UI_SHELL": "qt"})
    user_preferences.set_value("shell", "qt")
    by_file = dry([])
    unknown = dry(["--shell", "gtk"])

    ran: list = []
    import KrakenOS.UI.layout_editor as tk_entry
    import KrakenOS.UI.qt.app as qt_entry

    real_tk, real_qt = tk_entry.main, qt_entry.run
    tk_entry.main = lambda scene=None: ran.append(("tk", scene))
    qt_entry.run = lambda argv=None: (ran.append(("qt", list(argv))), 0)[1]
    try:
        launcher.start("qt", ["prog", str(SCENE)])
        launcher.start("tk", ["prog", str(SCENE)])
        launcher.start("tk", ["prog"])
    finally:
        tk_entry.main, qt_entry.run = real_tk, real_qt
    return [["L", nothing_set[:2] == (0, f"shell=(ask) arguments={[str(SCENE)]}")
             and by_flag[:2] == (0, f"shell=tk arguments={[str(SCENE)]}") and "the command line" in by_flag[2]
             and by_environment[:2] == (0, f"shell=qt arguments={[str(SCENE)]}") and "KRAKEN_UI_SHELL" in by_environment[2]
             and by_file[:2] == (0, "shell=qt arguments=[]") and "your saved preference" in by_file[2]
             and unknown[0] == 2 and "gtk" in unknown[3][0]
             and ran == [("qt", ["prog", str(SCENE)]), ("tk", str(SCENE)), ("tk", None)],
             f"with nothing set -> {nothing_set[1]!r} (it would ask; a dry run does not); "
             f"`python -m KrakenOS.UI --shell tk <layout>` -> {by_flag[1]!r}; with KRAKEN_UI_SHELL=qt -> {by_environment[1]!r}; "
             f"with the preference saved -> {by_file[1]!r} ({by_file[2].split('(')[-1].split(')')[0]}); --shell gtk exits "
             f"{unknown[0]} saying {unknown[3][0][:60]!r}; the dispatch ran {[(s, bool(a)) for s, a in ran]}"]]


def window_checks() -> list:
    """W: the first-run window, driven in place of its main loop."""
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI import launcher

    seen: dict = {}
    real_loop = tk.Tk.mainloop

    def drive(pick):
        def loop(root, *_a):
            def texts(widget, kind):
                found = [str(widget.cget("text"))] if isinstance(widget, kind) else []
                for child in widget.winfo_children():
                    found.extend(texts(child, kind))
                return found

            root.update()
            seen.setdefault("radios", texts(root, ttk.Radiobutton))
            seen.setdefault("checks", texts(root, ttk.Checkbutton))
            seen.setdefault("defaults", (root.kraken_choice.get(), bool(root.kraken_remember.get())))
            if pick is None:
                root.destroy()
                return
            root.kraken_choice.set(pick[0])
            root.kraken_remember.set(pick[1])
            root.kraken_open.invoke()
        return loop

    try:
        tk.Tk.mainloop = drive(("tk", False))
        opened = launcher.ask_which_shell(["qt", "tk"], "qt")
        tk.Tk.mainloop = drive(None)
        closed = launcher.ask_which_shell(["qt", "tk"], "qt")
    finally:
        tk.Tk.mainloop = real_loop
    return [["W", seen.get("radios") == ["Qt interface", "Tk interface"] and seen.get("checks") == ["Remember my choice"]
             and seen.get("defaults") == ("qt", True) and opened == ("tk", False) and closed[0] == "",
             f"the window offers {seen.get('radios')} with {seen.get('checks')}, opening on (choice, remember) "
             f"{seen.get('defaults')}; choosing Tk and unticking, then Open -> {opened}; closing it -> {closed[0]!r}"]]


def tk_checks() -> list:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI import user_preferences
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import interface_preference as form_module

    _fresh_config()
    editor = KrakenLayoutEditor()
    for _ in range(3):
        editor.update()
    menubar = editor.root.nametowidget(editor.root.cget("menu"))
    cascade = next(i for i in range(int(menubar.index("end")) + 1)
                   if menubar.type(i) == "cascade" and menubar.entrycget(i, "label") == "File")
    file_menu = menubar.nametowidget(menubar.entrycget(cascade, "menu"))
    labels = [file_menu.entrycget(i, "label") for i in range(int(file_menu.index("end")) + 1)
              if file_menu.type(i) == "command"]
    before = {id(w) for w in editor.root.winfo_children() if isinstance(w, tk.Toplevel)}
    position = next(i for i in range(int(file_menu.index("end")) + 1)
                    if file_menu.type(i) == "command" and file_menu.entrycget(i, "label") == "Interface Preference...")
    file_menu.invoke(position)                     # the real menu entry
    for _ in range(4):
        editor.update()
    windows = [w for w in editor.root.winfo_children() if isinstance(w, tk.Toplevel) and id(w) not in before]
    window = windows[0] if windows else None

    def find(widget, kind):
        found = [widget] if isinstance(widget, kind) else []
        for child in widget.winfo_children():
            found.extend(find(child, kind))
        return found

    title = window.title() if window is not None else ""
    combos = find(window, ttk.Combobox) if window is not None else []
    offered = list(combos[0].cget("values")) if combos else []
    shown = combos[0].get() if combos else ""
    wrote = {}
    if combos:
        combos[0].set("Tk interface")
        apply = next((b for b in find(window, ttk.Button) if str(b.cget("text")) == "Apply"), None)
        if apply is not None:
            apply.invoke()
            for _ in range(3):
                editor.update()
            wrote = user_preferences.load()
    return [["T", "Interface Preference..." in labels and labels[-1] == "Quit" and title == form_module.TITLE
             and offered == ["Qt interface", "Tk interface", form_module.ASK] and shown == form_module.ASK
             and wrote == {"shell": "tk"} and form_module.running_shell(editor) == "tk",
             f"the Tk File menu ends {labels[-2:]}; its entry opens a window titled {title!r} offering {offered}, on "
             f"{shown!r}; choosing Tk and Apply writes {wrote}; the running interface reads as "
             f"{form_module.running_shell(editor)!r}"]]


def qt_checks() -> list:
    import time
    import tkinter as tk

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QDialog

    from KrakenOS.UI import user_preferences
    from KrakenOS.UI.qt import ribbon
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.row_forms import interface_preference as form_module

    _fresh_config()
    user_preferences.set_value("shell", "tk")
    app, window = build(["guard"])
    window.resize(1500, 950)
    window.show()
    app.processEvents()

    def settle(seconds: float = 0.4) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(0.8)
    in_help = "interface_preference" in ribbon.DROPDOWNS["menu:help"][1]
    action = window.action_manager["interface_preference"]
    tk_windows: list = []
    init = tk.Toplevel.__init__
    tk.Toplevel.__init__ = lambda self, *a, **k: (init(self, *a, **k), tk_windows.append(type(self).__name__))[0]
    try:
        action.trigger()
        settle()
    finally:
        tk.Toplevel.__init__ = init
    dialog = window.last_model_form_dialog
    opened = isinstance(dialog, QDialog) and dialog.isVisible() and dialog.windowTitle() == form_module.TITLE
    if not opened:
        return [["Q", False, f"the action opened no Qt form: {type(dialog).__name__}; Tk windows {tk_windows}"]]
    box = dialog.widgets["shell"]
    offered = [box.itemText(i) for i in range(box.count())]
    shown = box.currentText()
    says = dialog.form.summary
    box.setCurrentText("Qt interface")
    QTest.mouseClick(dialog.apply_button, Qt.MouseButton.LeftButton)
    settle()
    wrote = user_preferences.load()
    return [["Q", in_help and opened and tk_windows == [] and offered == ["Qt interface", "Tk interface", form_module.ASK]
             and shown == "Tk interface" and "Running now: the Qt interface" in says and wrote == {"shell": "qt"}
             and not dialog.isVisible(),
             f"the action is in the Help dropdown: {in_help}; it opens a Qt dialog {opened}, Tk windows {tk_windows}; "
             f"offering {offered}, on the saved {shown!r}; it says {says.split('. ')[-1]!r}; choosing Qt and a click on "
             f"Apply writes {wrote} and closes it: {not dialog.isVisible()}"]]


def _run(call: str, needs: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        f"{needs}"
        "from KrakenOS.UI.validate_interface_preference import qt_checks, tk_checks, window_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.pop("KRAKEN_UI_SHELL", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    env["KRAKEN_CONFIG_DIR"] = tempfile.mkdtemp(prefix="krakenpref0971_")
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
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
    real = os.environ.get("KRAKEN_CONFIG_DIR")
    try:
        rows = pure_checks()
        try:
            rows += launcher_checks()
        except Exception as exc:
            rows.append(["L", False, f"raised {type(exc).__name__}: {exc}"])
    finally:
        if real is None:
            os.environ.pop("KRAKEN_CONFIG_DIR", None)
        else:
            os.environ["KRAKEN_CONFIG_DIR"] = real
    rows += (_run("window_checks()", "", "W") + _run("tk_checks()", "", "T")
             + _run("qt_checks()", "import PySide6\n", "Q"))
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
