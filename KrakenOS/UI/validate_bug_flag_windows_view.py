"""Guard for bugs/0979: the 2D bug flag's Tk windows are a panel; the recorder does not draw.

Phase 7d of the Qt migration, the fifth service. `services/layout_bug_recorder.py` imported tkinter
for two pieces of Tk: the scan of the Tk windows open when a flag is taken (each one's geometry,
and whether it spills past the screen), and the small window that asks for the flag's description.
Both are `panels/main_bug_flag_windows.py` now. What a flag captures, and what Save and Close do,
stay in the service.

Nothing guarded the 2D flag before this, so this guard runs it end to end as well.

  S  the service imports and names no tkinter and builds no window; the panel class defines both
     methods and the editor delegates both to it
  M  the model, no display, in a temp folder: Save with words writes description.txt and sets
     state.json's description, keeping its other keys, and says so; Save with none, and Close,
     write nothing and say the flag is kept; a missing state.json or bundle folder is a debug line,
     never an error
  T  a real Tk editor, with every flag written to a temp folder: a flag taken with a small and an
     oversized Tk window open lists both in state.json with their sizes and marks only the
     oversized one, and the status line counts it; the description window is titled for the
     bundle, is NOT modal, has Save and Close and Ctrl+Return; Save writes the words and closes
     it; Close -- even with words typed -- and the window's own close button keep the flag with
     its description empty
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

RESULT_MARK = "FLAG2DVIEW_RESULT "
SKIP_MARK = "FLAG2DVIEW_SKIP "
SERVICE = Path("KrakenOS/UI/services/layout_bug_recorder.py")
VIEW_METHODS = ("_collect_open_toplevels", "_open_2d_flag_description_dialog")
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
    from KrakenOS.UI.services.layout_bug_recorder import LayoutBugRecorderMixin as Model

    def s():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.panels.main_bug_flag_windows import MainBugFlagWindows

        tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
        imports = sorted({node.lineno for node in ast.walk(tree)
                          if (node.__class__ is ast.Import and any(a.name.split(".")[0] == "tkinter" for a in node.names))
                          or (isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tkinter")})
        named = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in TK_NAMES})
        toplevels = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Call)
                        and (getattr(node.func, "attr", "") or getattr(node.func, "id", "")) == "Toplevel")
        still_there = [name for name in VIEW_METHODS if name in vars(Model)]
        panel_defines = [name for name in VIEW_METHODS if name in vars(MainBugFlagWindows)]
        delegations = [name for name in VIEW_METHODS if name in vars(KrakenLayoutEditor)
                       and f"self._main_bug_flag_windows().{name}(" in inspect.getsource(vars(KrakenLayoutEditor)[name])]
        return (imports == [] and named == [] and toplevels == 0 and still_there == []
                and panel_defines == list(VIEW_METHODS) and delegations == list(VIEW_METHODS),
                f"{SERVICE.name}: tkinter imports at lines {imports or 'none'}, tkinter names {named or 'none'}, Toplevels built "
                f"{toplevels}, view methods still defined there {still_there or 'none'}; the panel defines "
                f"{len(panel_defines)} of {len(VIEW_METHODS)} and the editor delegates {len(delegations)} of them to it")

    def m():
        def owner():
            fake = SimpleNamespace(status=[], debug=[])
            fake._set_bug_status = fake.status.append
            fake._bug_recorder_debug = fake.debug.append
            return fake

        work = Path(tempfile.mkdtemp(prefix="g0979_"))
        bundle = work / "flag_20261007_120000_000"
        bundle.mkdir()
        state = bundle / "state.json"
        state.write_text(json.dumps({"version": 1, "description": "", "open_toplevels": []}), encoding="utf-8")
        saved = owner()
        wrote = Model._save_2d_flag_description(saved, bundle, state, "  the legend overlaps the plot  \n")
        on_disk = ((bundle / "description.txt").read_text(encoding="utf-8"), json.loads(state.read_text(encoding="utf-8")))

        empty_bundle = work / "flag_20261007_120001_000"
        empty_bundle.mkdir()
        empty_state = empty_bundle / "state.json"
        empty_state.write_text(json.dumps({"description": ""}), encoding="utf-8")
        empty, closed = owner(), owner()
        wrote_empty = Model._save_2d_flag_description(empty, empty_bundle, empty_state, "   \n")
        Model._keep_2d_flag_without_description(closed, empty_bundle)
        untouched = (not (empty_bundle / "description.txt").exists(), json.loads(empty_state.read_text(encoding="utf-8")))

        stateless_bundle = work / "flag_20261007_120002_000"
        stateless_bundle.mkdir()
        stateless = owner()
        wrote_stateless = Model._save_2d_flag_description(stateless, stateless_bundle, stateless_bundle / "state.json", "words")
        gone = owner()
        wrote_gone = Model._save_2d_flag_description(gone, work / "no_such_bundle", work / "no_such_bundle" / "state.json", "words")
        return (wrote is True and on_disk[0] == "the legend overlaps the plot\n"
                and on_disk[1] == {"version": 1, "description": "the legend overlaps the plot", "open_toplevels": []}
                and saved.status == [f"Flag description saved: {bundle.name}"] and saved.debug == []
                and wrote_empty is False and empty.status == [f"Flag kept without description: {empty_bundle.name}"]
                and closed.status == [f"Flag kept without description: {empty_bundle.name}"]
                and untouched == (True, {"description": ""})
                and wrote_stateless is True and (stateless_bundle / "description.txt").read_text(encoding="utf-8") == "words\n"
                and stateless.debug == [] and not (stateless_bundle / "state.json").exists()
                and wrote_gone is True and len(gone.debug) == 1 and gone.debug[0].startswith("2D flag description save failed:"),
                f"Save with words wrote {on_disk[0]!r}, set state.json's description and kept its {len(on_disk[1]) - 1} other "
                f"keys, saying {saved.status}; Save with none wrote nothing ({untouched[0]}) and says {empty.status}; Close "
                f"says {closed.status}; with no state.json the words are still written ({wrote_stateless}); with no bundle "
                f"folder there is one debug line and no error: {gone.debug[0][:34]!r}")

    return _claims((("S", s), ("M", m)))


def tk_checks() -> list:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import layout_bug_recorder as recorder

    editor = KrakenLayoutEditor()
    for _ in range(3):
        editor.update()
    work = Path(tempfile.mkdtemp(prefix="g0979_"))
    recorder._ATTACHMENT_DIR = work                         # every flag of this guard goes to a temp folder
    editor._capture_fullscreen_png = lambda out_path: False  # no screen grabber is run

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    def press(window, text) -> None:
        next(b for b in widgets(window, ttk.Button) if str(b.cget("text")) == text).invoke()

    def pump() -> None:
        for _ in range(4):
            editor.update()

    def flag_window(bundle):
        return next((w for w in widgets(editor.root, tk.Toplevel) if str(w.title()) == f"Flag: {bundle.name}"), None)

    def claim_t():
        small, oversized = tk.Toplevel(editor), tk.Toplevel(editor)
        small.title("Small dialog")
        small.geometry("220x120+40+40")
        oversized.title("Oversized dialog")
        oversized.geometry("9000x9000+0+0")
        pump()
        bundle = editor.flag_bug_2d()
        pump()
        flagged_status = str(editor.status_var.get())
        state_path = bundle / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        listed = {entry["title"]: (entry["width"], entry["height"], entry["exceeds_screen"]) for entry in state["open_toplevels"]}
        oversized_titles = [entry["title"] for entry in state["oversized_dialogs"]]
        small.destroy()
        oversized.destroy()
        pump()

        window = flag_window(bundle)
        shown = {"under_temp": work in bundle.parents, "buttons": [str(b.cget("text")) for b in widgets(window, ttk.Button)],
                 "prompt": [str(w.cget("text")).splitlines()[0] for w in widgets(window, ttk.Label)],
                 "modal": window.grab_current() is not None,
                 "ctrl_return": bool(widgets(window, tk.Text)[0].bind("<Control-Return>")),
                 "close": bool(window.protocol("WM_DELETE_WINDOW"))}
        widgets(window, tk.Text)[0].insert("1.0", "the dialog runs off the screen")
        press(window, "Save")
        pump()
        saved = (not bool(window.winfo_exists()), (bundle / "description.txt").read_text(encoding="utf-8"),
                 json.loads(state_path.read_text(encoding="utf-8"))["description"], str(editor.status_var.get()))

        second = editor.flag_bug_2d()
        pump()
        window = flag_window(second)
        widgets(window, tk.Text)[0].insert("1.0", "typed and then closed")
        press(window, "Close")
        pump()
        # (taking a flag writes an EMPTY description.txt at once; Close must leave it empty)
        closed = (not bool(window.winfo_exists()), (second / "description.txt").read_text(encoding="utf-8"),
                  str(editor.status_var.get()), json.loads((second / "state.json").read_text(encoding="utf-8"))["description"])

        third = editor.flag_bug_2d()
        pump()
        window = flag_window(third)
        window.tk.call(window.protocol("WM_DELETE_WINDOW"))
        pump()
        by_button = (not bool(window.winfo_exists()), (third / "description.txt").read_text(encoding="utf-8"),
                     str(editor.status_var.get()), (third / "state.json").exists())
        return (listed.get("Small dialog", (0, 0, True))[2] is False and listed.get("Small dialog", (0, 0))[:2] == (220, 120)
                and listed.get("Oversized dialog", (0, 0, False))[2] is True and oversized_titles == ["Oversized dialog"]
                and "(1 dialog(s) exceed the screen)" in flagged_status
                and shown == {"under_temp": True, "buttons": ["Save", "Close"],
                              "prompt": ["Describe the 2D bug (the editor stays usable while this is open)."],
                              "modal": False, "ctrl_return": True, "close": True}
                and saved == (True, "the dialog runs off the screen\n", "the dialog runs off the screen",
                              f"Flag description saved: {bundle.name}")
                and closed == (True, "", f"Flag kept without description: {second.name}", "")
                and by_button == (True, "", f"Flag kept without description: {third.name}", True),
                f"a flag taken with two Tk windows open lists them as {listed} and marks {oversized_titles}; status "
                f"{flagged_status[-58:]!r}; the description window has {shown['buttons']}, modal {shown['modal']}, Ctrl+Return "
                f"{shown['ctrl_return']}; Save wrote {saved[1]!r} and says {saved[3]!r}; Close with words typed left the "
                f"description {closed[1]!r} and says {closed[2]!r}; the window's close button left it {by_button[1]!r} "
                f"(bundle kept {by_button[3]})")

    return _claims((("T", claim_t),))


def _run(call: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_bug_flag_windows_view import tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=300,
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
