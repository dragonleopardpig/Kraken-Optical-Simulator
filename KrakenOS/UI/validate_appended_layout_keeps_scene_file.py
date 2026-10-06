"""Guard for bugs/0973: a layout APPENDED to the open scene leaves the scene's own file alone.

Six common layouts are "insertable" (Doublet Lens, Single Lens, Flat Mirror 45 Deg ...). Chosen from
the Layouts menu while a scene is open, they do not replace it: the loader appends them. The same
call had already pointed the scene at the appended layout's own file -- so File > Save overwrote
the SHIPPED layout with the merged scene, without a question, and never saved the file the user was
working in. Measured: Single Lens, then Layouts > Doublet Lens, then Save rewrote doublet_lens.py
with seven rows.

Decided 2026-10-06, on the user's go-ahead: after an append the scene keeps the file it had (not:
becomes untitled, as Insert > Common Component leaves it).

Every claim works on temp COPIES of the layouts: nothing under the repository can be written.

  The model, with scripted dialog answers (no window is built):
  A  a scene opened from the user's own file (File > Open) takes in Doublet Lens: the rows grow,
     the status says "Appended", and the scene is still that file -- its file, its title and its
     three selector names are what they were
  S  Save then asks nothing, writes the user's file -- the scene emptied and the file opened again
     gives the merged rows -- and leaves the appended layout's file byte for byte as it was
  U  an UNTITLED scene (rows, no file) stays untitled: Save asks where, writes there, and the
     appended layout's file is untouched
  I  a transient import (bugs/0375: Save must ask rather than overwrite the generated file) is
     still one after an append: the mark, the "* name" title, and Save asking
  H  undo takes the append back and redo puts it again; the scene's file is the same throughout
  R  a load that REPLACES the scene still takes the loaded layout's file, name and a clean
     transient mark: an insertable layout from the empty starter, and a layout that is not
     insertable over an open scene

  The two interfaces, through their real menu entries:
  T  Tk: Layouts > Single Lens, Layouts > Doublet Lens, File > Save -- the title stays the scene's,
     the scene's file is rewritten, Doublet Lens's is untouched
  Q  Qt: the same from the ribbon's Layouts menu and the Save action -- the window title and the
     table follow, the same two files, and no Tk window

Each claim fails on its own: one that raises is reported as that claim's failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_MARK = "APPENDKEEPSFILE_RESULT "
SKIP_MARK = "APPENDKEEPSFILE_SKIP "
SCENE = "Single Lens"          # the scene that is open (insertable too, but loaded from the empty starter it replaces)
COMPONENT = "Doublet Lens"     # the insertable layout chosen over it


def _digest(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def _copies(editor, work: Path, names) -> dict:
    """Point the named layouts at temp COPIES, so that no claim can write a shipped file."""
    copies = {}
    for name in names:
        shipped = Path(editor.layout_files[name])
        copy = work / shipped.name
        if not copy.exists():
            shutil.copy2(shipped, copy)
        editor.layout_files[name] = copy
        copies[name] = copy
    return copies


def _name(path) -> str:
    return Path(str(path)).name if path else "(none)"


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def model_checks() -> list:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.uihost import ScriptedUiHost

    # ONE editor for the six claims (an editor's first load costs some 20 s, a later one under a
    # second); each claim starts from `fresh()`.
    work = Path(tempfile.mkdtemp(prefix="g0973_"))
    mine, asked_file = work / "my_bench.py", work / "asked.py"
    host = ScriptedUiHost(answers={"askopenfilename": str(mine), "asksaveasfilename": str(asked_file)})
    editor = KrakenLayoutEditor(headless=True, ui=host)
    # These claims are about the scene's file, rows, title and Save -- not its picture. Redrawing the
    # 2D plot (with a trace) after every open, insert, undo and redo cost three minutes of the
    # run; T and Q go through the real redraw.
    editor.refresh_plot = lambda *args, **kwargs: None
    shipped = {name: Path(path) for name, path in editor.layout_files.items()}
    insertable = set(editor._insertable_common_layout_names())
    plain = min((name for name in shipped if name not in insertable and name in editor.layout_names),
                key=lambda name: (shipped[name].stat().st_size, name))
    copies = {name: work / shipped[name].name for name in (SCENE, COMPONENT, plain)}

    def fresh(*, open_mine: bool = True) -> int:
        """A clean slate: pristine temp copies, the empty starter, no transient mark -- then (unless
        told not to) the user's own file opened as File > Open does. Returns how many times Save
        has asked so far."""
        for name, copy in copies.items():
            shutil.copy2(shipped[name], copy)
            editor.layout_files[name] = copy
        shutil.copy2(shipped[SCENE], mine)
        asked_file.unlink(missing_ok=True)
        editor.reset_layout()
        editor._layout_is_unsaved_import = False
        if open_mine:
            editor.open_layout()
        return len(host.asked("asksaveasfilename"))

    def asked_since(count: int) -> int:
        return len(host.asked("asksaveasfilename")) - count

    def selectors() -> list:
        return [str(editor.layout_var.get()), str(editor.machine_vision_var.get()), str(editor.example_var.get())]

    def names() -> list:
        return [str(row.name) for row in editor.rows]

    def claim_a():
        fresh()
        before = (len(editor.rows), _name(editor.current_layout_file), editor.title(), selectors())
        editor.load_layout_by_name(COMPONENT)
        after = (len(editor.rows), _name(editor.current_layout_file), editor.title(), selectors())
        status = str(editor.status_var.get())
        return (before[1] == "my_bench.py" and COMPONENT not in before[3] and after[0] > before[0] > 2
                and status.startswith(f"Appended {COMPONENT}") and after[1:] == before[1:]
                and editor.current_layout_file == mine,
                f"opened {before[1]} ({before[0]} rows, title {before[2]!r}, selectors {before[3]}); after choosing "
                f"{COMPONENT}: {after[0]} rows, status {status[:24]!r}, file {after[1]}, title {after[2]!r}, selectors "
                f"{after[3]}")

    def claim_s():
        asked = fresh()
        editor.load_layout_by_name(COMPONENT)
        merged = names()
        before = (_digest(mine), _digest(copies[COMPONENT]))
        saved = editor.save_layout()
        questions = asked_since(asked)
        after = (_digest(mine), _digest(copies[COMPONENT]))
        editor.reset_layout()                                   # so that what is read back comes from the file
        emptied = len(editor.rows)
        editor.open_layout()
        read_back = names()
        return (saved is True and questions == 0 and after[0] != before[0] and after[1] == before[1] and emptied == 2
                and read_back == merged and len(merged) > 4 and not asked_file.exists(),
                f"Save returned {saved} and asked {questions} question(s); my_bench.py rewritten: {after[0] != before[0]}; "
                f"the scene emptied ({emptied} rows) and the file opened again gives {len(read_back)} rows, the merged "
                f"scene: {read_back == merged}; {copies[COMPONENT].name} unchanged: {after[1] == before[1]}")

    def claim_u():
        asked = fresh(open_mine=False)
        editor.insert_layout_component_by_name(SCENE)          # rows, and no file: an untitled scene
        untitled = (len(editor.rows), editor.current_layout_file)
        editor.load_layout_by_name(COMPONENT)
        appended = (len(editor.rows), editor.current_layout_file, str(editor.status_var.get())[:8])
        before = _digest(copies[COMPONENT])
        saved = editor.save_layout()
        questions = asked_since(asked)
        return (untitled[0] > 2 and untitled[1] is None and appended[0] > untitled[0] and appended[1] is None
                and appended[2] == "Appended" and saved is True and questions == 1 and asked_file.exists()
                and _digest(copies[COMPONENT]) == before and editor.current_layout_file == asked_file,
                f"an untitled scene of {untitled[0]} rows (file {_name(untitled[1])}) takes in {COMPONENT}: {appended[0]} "
                f"rows, file {_name(appended[1])}; Save asked {questions} time(s) and wrote "
                f"{'asked.py' if asked_file.exists() else 'nothing there'}; {copies[COMPONENT].name} unchanged: "
                f"{_digest(copies[COMPONENT]) == before}")

    def claim_i():
        asked = fresh()
        editor._layout_is_unsaved_import = True                # what the lens importer does after its load
        editor._update_window_title()
        marked = editor.title()
        editor.load_layout_by_name(COMPONENT)
        after = (bool(editor._layout_is_unsaved_import), _name(editor.current_layout_file), editor.title())
        before = (_digest(mine), _digest(copies[COMPONENT]))
        saved = editor.save_layout()
        questions = asked_since(asked)
        untouched = (_digest(mine), _digest(copies[COMPONENT])) == before
        return (marked == "* my_bench.py" and after == (True, "my_bench.py", "* my_bench.py") and saved is True
                and questions == 1 and untouched and asked_file.exists(),
                f"a transient import (title {marked!r}) takes in {COMPONENT}: still marked {after[0]}, file {after[1]}, "
                f"title {after[2]!r}; Save asked {questions} time(s) instead of writing over it; the import's file and "
                f"{copies[COMPONENT].name} untouched: {untouched}")

    def claim_h():
        fresh()
        trail = [(len(editor.rows), _name(editor.current_layout_file))]
        editor.load_layout_by_name(COMPONENT)
        trail.append((len(editor.rows), _name(editor.current_layout_file)))
        editor.undo()
        trail.append((len(editor.rows), _name(editor.current_layout_file)))
        editor.redo()
        trail.append((len(editor.rows), _name(editor.current_layout_file)))
        counts, files = [count for count, _file in trail], {file for _count, file in trail}
        return (counts[1] > counts[0] > 2 and counts[2] == counts[0] and counts[3] == counts[1] and files == {"my_bench.py"},
                f"open, append, undo, redo: rows {counts}, the scene's file throughout {sorted(files)}")

    def claim_r():
        fresh(open_mine=False)
        starter = len(editor.rows)
        editor._layout_is_unsaved_import = True
        editor.load_layout_by_name(COMPONENT)                  # from the empty starter: it replaces
        first = (len(editor.rows), editor.current_layout_file == copies[COMPONENT], str(editor.layout_var.get()),
                 bool(editor._layout_is_unsaved_import), str(editor.status_var.get())[:6])
        editor._layout_is_unsaved_import = True
        editor.load_layout_by_name(plain)                      # not insertable, over an open scene: it replaces
        second = (editor.current_layout_file == copies[plain], str(editor.layout_var.get()),
                  bool(editor._layout_is_unsaved_import), str(editor.status_var.get())[:6], editor.title())
        return (starter == 2 and first == (first[0], True, COMPONENT, False, "Loaded") and first[0] > 2
                and second == (True, plain, False, "Loaded", copies[plain].name),
                f"from the {starter}-row starter {COMPONENT} replaces: {first[0]} rows, takes its file {first[1]}, its "
                f"name {first[2]!r}, transient mark {first[3]}, status {first[4]!r}; then {plain!r} (not insertable) "
                f"replaces that: takes its file {second[0]}, name {second[1]!r}, mark {second[2]}, status {second[3]!r}, "
                f"title {second[4]!r}")

    return _claims((("A", claim_a), ("S", claim_s), ("U", claim_u), ("I", claim_i), ("H", claim_h), ("R", claim_r)))


def tk_checks() -> list:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    def claim_t():
        editor = KrakenLayoutEditor()
        for _ in range(3):
            editor.update()
        work = Path(tempfile.mkdtemp(prefix="g0973_"))
        copies = _copies(editor, work, (SCENE, COMPONENT))

        def choose(menu, label) -> bool:
            """Invoke the entry labelled ``label`` in ``menu`` or one of its submenus, as a click does."""
            last = menu.index("end")
            for index in range((last if last is not None else -1) + 1):
                kind = menu.type(index)
                if kind == "command" and menu.entrycget(index, "label") == label:
                    menu.invoke(index)
                    return True
                if kind == "cascade" and choose(menu.nametowidget(menu.entrycget(index, "menu")), label):
                    return True
            return False

        steps = [choose(editor.layout_menu, SCENE)]
        for _ in range(3):
            editor.update()
        loaded = (len(editor.rows), editor.title())
        steps.append(choose(editor.layout_menu, COMPONENT))
        for _ in range(3):
            editor.update()
        appended = (len(editor.rows), editor.title(), _name(editor.current_layout_file))
        before = (_digest(copies[SCENE]), _digest(copies[COMPONENT]))
        asks: list = []          # a Save that ASKS fails the claim; it must not put a chooser up and wait
        editor.ui.asksaveasfilename = lambda **options: (asks.append(options), "")[1]
        menubar = editor.nametowidget(editor.cget("menu"))
        file_menu = next((menubar.nametowidget(menubar.entrycget(index, "menu")) for index in range(menubar.index("end") + 1)
                          if menubar.type(index) == "cascade" and menubar.entrycget(index, "label") == "File"), None)
        steps.append(file_menu is not None and choose(file_menu, "Save"))
        for _ in range(3):
            editor.update()
        after = (_digest(copies[SCENE]), _digest(copies[COMPONENT]))
        return (all(steps) and loaded[1] == copies[SCENE].name and appended[0] > loaded[0] > 2
                and appended[1:] == (copies[SCENE].name, copies[SCENE].name) and asks == []
                and after[0] != before[0] and after[1] == before[1],
                f"the three real entries were found and run: {steps}; Layouts > {SCENE}: {loaded[0]} rows, title "
                f"{loaded[1]!r}; Layouts > {COMPONENT}: {appended[0]} rows, title {appended[1]!r}; File > Save asked "
                f"{len(asks)} question(s), rewrote "
                f"{copies[SCENE].name}: {after[0] != before[0]}, and left {copies[COMPONENT].name} as it was: "
                f"{after[1] == before[1]}")

    return _claims((("T", claim_t),))


def qt_checks() -> list:
    def claim_q():
        import time
        import tkinter as tk

        from KrakenOS.UI.qt.app import build

        app, window = build(["guard"])
        window.resize(1500, 950)
        window.show()
        app.processEvents()
        window.build_scene()
        window.refresh_from_model()

        def settle(seconds: float = 0.5) -> None:
            end = time.time() + seconds
            while time.time() < end:
                app.processEvents()
                time.sleep(0.02)

        settle(1.5)
        editor, ribbon = window.editor, window.ribbon
        work = Path(tempfile.mkdtemp(prefix="g0973_"))
        copies = _copies(editor, work, (SCENE, COMPONENT))

        def choose(label) -> bool:
            """Trigger the Layouts entry labelled ``label``, as choosing it on the ribbon does."""
            menu = ribbon.model_menus["model:layouts"].menu()
            menu.aboutToShow.emit()
            entry = next((entry for action in menu.actions() if action.menu() is not None
                          for entry in action.menu().actions() if entry.text() == label), None)
            if entry is None:
                return False
            entry.trigger()
            settle(1.5)
            return True

        tk_windows: list = []
        asks: list = []          # as in T: a Save that asks fails the claim
        init = tk.Toplevel.__init__
        tk.Toplevel.__init__ = lambda self, *a, **k: (init(self, *a, **k), tk_windows.append(type(self).__name__))[0]
        try:
            steps = [choose(SCENE)]
            loaded = (len(editor.rows), window.windowTitle())
            steps.append(choose(COMPONENT))
            appended = (len(editor.rows), window.rows_model.rowCount(), window.windowTitle(), _name(editor.current_layout_file))
            before = (_digest(copies[SCENE]), _digest(copies[COMPONENT]))
            editor.ui.asksaveasfilename = lambda **options: (asks.append(options), "")[1]
            save = ribbon.actions.get("save")
            steps.append(save is not None)
            if save is not None:
                save.trigger()                     # the real Save action
                settle(1.0)
            after = (_digest(copies[SCENE]), _digest(copies[COMPONENT]))
        finally:
            tk.Toplevel.__init__ = init
        return (all(steps) and copies[SCENE].name in loaded[1] and appended[0] > loaded[0] > 2 and appended[1] == appended[0]
                and copies[SCENE].name in appended[2] and copies[COMPONENT].name not in appended[2]
                and appended[3] == copies[SCENE].name and asks == [] and after[0] != before[0] and after[1] == before[1]
                and tk_windows == [],
                f"the entries and the Save action were found and run: {steps}; Layouts > {SCENE}: {loaded[0]} rows, title "
                f"{loaded[1]!r}; Layouts > {COMPONENT}: {appended[0]} rows (table {appended[1]}), title {appended[2]!r}; Save "
                f"asked {len(asks)} question(s), rewrote {copies[SCENE].name}: {after[0] != before[0]}, and left "
                f"{copies[COMPONENT].name} as it was: "
                f"{after[1] == before[1]}; Tk windows {tk_windows}")

    return _claims((("Q", claim_q),))


def _run(call: str, needs: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        f"{needs}"
        "from KrakenOS.UI.validate_appended_layout_keeps_scene_file import model_checks, qt_checks, tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
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
    rows = (_run("model_checks()", "", "A") + _run("tk_checks()", "", "T")
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
