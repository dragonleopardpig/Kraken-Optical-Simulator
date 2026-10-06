"""Guard for bugs/0976: "copy this text" is a toolkit-free model command with a Tk view.

Phase 7d of the Qt migration, the second service. `services/analysis_compute_workflow.py` held the
copy shortcuts and the right-click menu of the main window's Tk text boxes, and the window-wide
Ctrl+C / Ctrl+V that follow the focus -- nine methods of Tk code, which is why the service imported
tkinter. They are `panels/main_text_copy.py` now; the service keeps what is not a view's: copy the
text to the system clipboard and say so on the status line.

  P  the model, no display: selected text is copied and the status line says with what; no
     selection, and an empty text, each say so and copy nothing; a clipboard that fails says
     "Copy failed"; one that RAISES is a debug line, not a crash -- for "selected" and for "all"
  S  the service module imports no tkinter and names none, and every one of the editor's nine view
     methods is a delegation the panel class defines itself (a missing one would recurse, bugs/0941)
  T  a real Tk editor: both logs carry the copy shortcuts and the right-click binding; copying a
     selection, with none, and all of a log go through the model with the right text; the
     right-click menu is ONE menu of two entries re-aimed at the box it was opened on; the
     window-wide copy takes a text box's selection, hands a focused table to the row copy, and paste
     to the row paste; a focus that Tk can no longer name is no focus, not an error
  Q  the Qt shell: the model command works there with no Tk widget asked -- the status line the
     window shows says what was copied, and with nothing selected says so. (The hidden Tk window
     the Qt shell's editor still builds binds its own copy keys; that goes with phase 7f.)

Each claim fails on its own: one that raises is reported as that claim's failure.
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

RESULT_MARK = "TEXTCOPY_RESULT "
SKIP_MARK = "TEXTCOPY_SKIP "
SERVICE = Path("KrakenOS/UI/services/analysis_compute_workflow.py")
VIEW_METHODS = ("_bind_text_copy_shortcuts", "_bind_text_context_menu", "_bind_global_copy_shortcuts",
                "_show_text_context_menu", "_safe_focus_get", "_copy_selection_from_focus", "_paste_rows_from_focus",
                "_copy_selection_from_text_widget", "_copy_all_from_text_widget")
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
    from KrakenOS.UI.services.analysis_compute_workflow import AnalysisComputeWorkflowMixin as Model

    class Status:
        def __init__(self) -> None:
            self.text = ""

        def set(self, value) -> None:
            self.text = str(value)

    def owner(clipboard):
        copied, debug = [], []

        def copy(text):
            copied.append(text)
            return clipboard()

        fake = SimpleNamespace(status_var=Status(), _copy_text_to_clipboard=copy, append_debug=debug.append,
                               copied=copied, debug=debug)
        fake._copy_text_and_report = lambda text, what: Model._copy_text_and_report(fake, text, what)
        return fake

    def p():
        def boom():
            raise RuntimeError("no clipboard tool")

        results = {}
        for name, call, text in (("selected", Model.copy_selected_text, "abc"), ("all", Model.copy_all_text, "whole log")):
            ok_owner, none_owner, empty_owner = owner(lambda: (True, "xclip")), owner(lambda: (True, "xclip")), owner(lambda: (True, "xclip"))
            failing, raising = owner(lambda: (False, "")), owner(boom)
            results[name] = [
                (call(ok_owner, text), ok_owner.copied, ok_owner.status_var.text),
                (call(none_owner, None), none_owner.copied, none_owner.status_var.text),
                (call(empty_owner, ""), empty_owner.copied, empty_owner.status_var.text),
                (call(failing, text), failing.copied, failing.status_var.text),
                (call(raising, text), raising.copied, raising.status_var.text, raising.debug),
            ]
        expected = {
            "selected": [(True, ["abc"], "Selected text copied to clipboard (xclip)"), (False, [], "No text selected"),
                         (False, [], "No text selected"), (False, ["abc"], "Copy failed"),
                         (False, ["abc"], "", ["Copy selected text failed: no clipboard tool"])],
            "all": [(True, ["whole log"], "All text copied to clipboard (xclip)"), (False, [], "No text to copy"),
                    (False, [], "No text to copy"), (False, ["whole log"], "Copy failed"),
                    (False, ["whole log"], "", ["Copy all text failed: no clipboard tool"])],
        }
        return (results == expected,
                f"selected: copied {results['selected'][0]}, none {results['selected'][1][2]!r}, a failing clipboard "
                f"{results['selected'][3][2]!r}, a raising one {results['selected'][4][3]}; all: copied {results['all'][0]}, "
                f"empty {results['all'][2][2]!r}, failing {results['all'][3][2]!r}, raising {results['all'][4][3]}")

    def s():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.panels.main_text_copy import MainTextCopy

        tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
        imports = sorted({node.lineno for node in ast.walk(tree)
                          if (node.__class__ is ast.Import and any(a.name.split(".")[0] == "tkinter" for a in node.names))
                          or (isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tkinter")})
        named = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in TK_NAMES})
        service_defines = sorted(name for name in VIEW_METHODS
                                 if any(isinstance(node, ast.FunctionDef) and node.name == name for node in ast.walk(tree)))
        panel_defines = [name for name in VIEW_METHODS if name in vars(MainTextCopy)]
        delegations = [name for name in VIEW_METHODS
                       if name in vars(KrakenLayoutEditor)
                       and f"self._main_text_copy().{name}(" in inspect.getsource(vars(KrakenLayoutEditor)[name])]
        return (imports == [] and named == [] and service_defines == [] and panel_defines == list(VIEW_METHODS)
                and delegations == list(VIEW_METHODS) and len(VIEW_METHODS) == 9,
                f"{SERVICE.name}: tkinter imports at lines {imports or 'none'}, tkinter names {named or 'none'}, view methods "
                f"still defined there {service_defines or 'none'}; the panel defines {len(panel_defines)} of {len(VIEW_METHODS)} "
                f"and the editor delegates {len(delegations)} of them to it")

    return _claims((("P", p), ("S", s)))


def tk_checks() -> list:
    import tkinter as tk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels.main_text_copy import MainTextCopy

    editor = KrakenLayoutEditor()
    for _ in range(3):
        editor.update()
    copied: list = []
    editor._copy_text_to_clipboard = lambda text: (copied.append(text), (True, "guard"))[1]
    status = lambda: str(editor.status_var.get())

    def fill(widget, text: str) -> None:
        state = str(widget.cget("state"))
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state=state)
        widget.tag_remove("sel", "1.0", "end")

    debug, progress = editor.debug_text, editor.progress_text

    def claim_t():
        notes, ok = [], True

        def check(condition, note) -> None:
            nonlocal ok
            ok = ok and bool(condition)
            notes.append(f"{note}: {bool(condition)}")

        bound = {name: [sequence for sequence in MainTextCopy.COPY_SEQUENCES if widget.bind(sequence)]
                 for name, widget in (("debug", debug), ("progress", progress))}
        check(all(len(sequences) == len(MainTextCopy.COPY_SEQUENCES) for sequences in bound.values())
              and len(MainTextCopy.COPY_SEQUENCES) == 6, f"both logs carry the {len(MainTextCopy.COPY_SEQUENCES)} copy shortcuts")
        check(bool(debug.bind("<Button-3>")) and bool(progress.bind("<Button-3>")), "both carry the right-click binding")
        check(all(bool(editor.root.bind_all(sequence)) for sequence in ("<Control-c>", "<Control-Insert>", "<Control-v>", "<Shift-Insert>")),
              "the window-wide copy and paste are bound")

        fill(debug, "alpha beta gamma\nsecond line")
        fill(progress, "progress text")
        del copied[:]
        debug.tag_add("sel", "1.6", "1.10")
        first = (editor._copy_selection_from_text_widget(debug), list(copied), status())
        check(first == ("break", ["beta"], "Selected text copied to clipboard (guard)"), f"a selection is copied {first[1:]}")
        debug.tag_remove("sel", "1.0", "end")
        del copied[:]
        none = (editor._copy_selection_from_text_widget(debug), list(copied), status())
        check(none == ("break", [], "No text selected"), f"with none selected {none[1:]}")
        whole = (editor._copy_all_from_text_widget(debug), list(copied), status())
        check(whole == ("break", ["alpha beta gamma\nsecond line"], "All text copied to clipboard (guard)"),
              f"all of the log is copied ({len(whole[1][0]) if whole[1] else 0} characters)")

        # the right-click menu: one menu, two entries, re-aimed at the box it is opened on
        posted: list = []
        popup, tk.Menu.tk_popup = tk.Menu.tk_popup, lambda self, x, y, entry="": posted.append((x, y))
        try:
            event = SimpleNamespace(x_root=11, y_root=22)
            editor._show_text_context_menu(event, debug)
            menu = editor._text_popup_menu
            labels = [menu.entrycget(index, "label") for index in range(menu.index("end") + 1)]
            del copied[:]
            menu.invoke(1)
            from_debug = list(copied)
            editor._show_text_context_menu(event, progress)
            del copied[:]
            menu.invoke(1)
            from_progress = list(copied)
            same_menu = editor._text_popup_menu is menu
        finally:
            tk.Menu.tk_popup = popup
        check(labels == ["Copy Selected", "Copy All"] and posted == [(11, 22), (11, 22)] and same_menu
              and from_debug == ["alpha beta gamma\nsecond line"] and from_progress == ["progress text"],
              f"the menu {labels} is posted at the pointer, is one menu ({same_menu}) and copies from the box it was opened on")

        # the window-wide copy and paste follow the focus
        panel = editor._main_text_copy()
        rows_copied, rows_pasted = [], []
        editor.copy_selected_rows_to_clipboard = lambda event=None: (rows_copied.append(1), "rows copied")[1]
        editor.paste_rows_from_clipboard = lambda event=None: (rows_pasted.append(1), "rows pasted")[1]
        try:
            object.__setattr__(panel, "_safe_focus_get", lambda: None)
            del copied[:]
            nothing = editor._copy_selection_from_focus()
            progress.tag_add("sel", "1.0", "1.8")
            from_log = (editor._copy_selection_from_focus(), list(copied))
            progress.tag_remove("sel", "1.0", "end")
            paste_elsewhere = editor._paste_rows_from_focus()
            object.__setattr__(panel, "_safe_focus_get", lambda: editor.table)
            from_table = (editor._copy_selection_from_focus(), editor._paste_rows_from_focus())
        finally:
            object.__delattr__(panel, "_safe_focus_get")
        check(nothing is None and from_log == ("break", ["progress"]) and paste_elsewhere is None
              and from_table == ("rows copied", "rows pasted") and (rows_copied, rows_pasted) == ([1], [1]),
              f"window-wide: nothing selected {nothing!r}, a log's selection {from_log}, the table focused {from_table}")

        # a focus Tk can no longer name is no focus
        seen = []
        for error in (KeyError("gone"), tk.TclError("bad window path name")):
            def raising(error=error):
                raise error

            editor.focus_get = raising
            try:
                seen.append(editor._safe_focus_get())
            finally:
                del editor.focus_get
        check(seen == [None, None], f"a focus that raises KeyError or TclError reads as {seen}")
        return ok, "; ".join(notes)

    return _claims((("T", claim_t),))


def qt_checks() -> list:
    def claim_q():
        import time

        from KrakenOS.UI.qt.app import build

        app, window = build(["guard"])
        window.show()
        app.processEvents()

        def settle(seconds: float = 0.4) -> None:
            end = time.time() + seconds
            while time.time() < end:
                app.processEvents()
                time.sleep(0.02)

        settle(1.0)
        editor = window.editor
        copied: list = []
        editor._copy_text_to_clipboard = lambda text: (copied.append(text), (True, "guard"))[1]
        done = editor.copy_all_text("a report's text")
        settle()
        shown = window.statusBar().currentMessage() if hasattr(window, "statusBar") else ""
        model_status = str(editor.status_var.get())
        nothing = editor.copy_selected_text("")
        settle()
        shown_none = window.statusBar().currentMessage() if hasattr(window, "statusBar") else ""
        return (done is True and copied == ["a report's text"]
                and model_status == "All text copied to clipboard (guard)" and shown == model_status
                and nothing is False and str(editor.status_var.get()) == "No text selected" and shown_none == "No text selected",
                f"in the Qt shell the model copied {copied} and says {model_status!r}; the window's status line shows "
                f"{shown!r}; with nothing selected it shows {shown_none!r}")

    return _claims((("Q", claim_q),))


def _run(call: str, needs: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        f"{needs}"
        "from KrakenOS.UI.validate_text_copy_view import qt_checks, tk_checks\n"
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
    try:
        rows = pure_checks()
    except Exception as exc:
        rows = [["P", False, f"raised {type(exc).__name__}: {exc}"]]
    rows += _run("tk_checks()", "", "T") + _run("qt_checks()", "import PySide6\n", "Q")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
