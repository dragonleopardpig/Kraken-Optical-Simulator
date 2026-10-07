"""Guard for bugs/0986: the lens-drawing properties' Tk window is a view module; the panel and the import/export service let go of tkinter.

Phase 7d of the Qt migration. `panels/main_lens_drawing_dialogs.py` shows the lens-drawing
properties session in the running shell's dialog or in Tk's window, and exports the PDF. The Tk
window -- 110 lines of widgets -- was one of its methods, so the panel loaded tkinter, and through
the panel `services/layout_import_export.py` did. The window is
`panels/lens_drawing_properties_view.py` now, imported when Tk draws.

What the window DOES with real typing -- refuse, apply, save, clear, load, close -- and that both
shells leave the same properties is phase 719 (bugs/0945). This guard holds what the move added:

  S  the panel imports and names no tkinter and nothing from `widgets`; the view module defines the
     window; the panel asks for a shell BEFORE it reaches for the Tk view
  L  asked of the interpreter, each in a fresh process: importing the panel loads no tkinter, and
     neither does importing the import/export service
  Q  under a shell, on a headless editor: with no lens in the table the host is told so and the
     shell is not asked; with the two-arm doublets loaded the shell is handed a session of its 8
     lens surfaces, and the command answers True when the session is continued and False when it
     is cancelled, `for_export` passed on -- and no Tk window is made, the Tk view never imported
  T  the Tk app, no shell: the window is a Tk window owned by the editor, titled as the session
     says, with one entry per surface and property and the session's six buttons, waited on; Close
     answers True and Cancel Export answers False; afterwards the window is gone and the session
     has no listener left
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "LENSDRAWVIEW_RESULT "
SKIP_MARK = "LENSDRAWVIEW_SKIP "
ROOT = Path("KrakenOS/UI")
PANEL = ROOT / "panels/main_lens_drawing_dialogs.py"
VIEW_MODULE = "KrakenOS.UI.panels.lens_drawing_properties_view"
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
LENS_SURFACES = 8
TK_NAMES = {"tk", "ttk", "tkfont", "messagebox", "filedialog", "simpledialog", "WidgetTooltip"}


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def _fresh(code: str) -> str:
    """The last line a fresh interpreter prints for ``code``."""
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300, cwd=str(Path.cwd()))
    return (done.stdout.strip().splitlines() or ["ERROR " + done.stderr.strip()[-300:]])[-1]


def pure_checks() -> list:
    def s():
        from KrakenOS.UI.panels import lens_drawing_properties_view as view
        from KrakenOS.UI.panels.main_lens_drawing_dialogs import MainLensDrawingDialogs

        tree = ast.parse(PANEL.read_text(encoding="utf-8"))
        imports = sorted({node.lineno for node in ast.walk(tree)
                          if (node.__class__ is ast.Import and any(a.name.split(".")[0] == "tkinter" for a in node.names))
                          or (isinstance(node, ast.ImportFrom) and ((node.module or "").split(".")[0] == "tkinter"
                                                                    or (node.module or "").startswith("KrakenOS.UI.widgets")))})
        named = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in TK_NAMES})
        source = inspect.getsource(MainLensDrawingDialogs)
        shell_at, view_at = source.find('"show_lens_drawing_properties"'), source.find("lens_drawing_properties_view import")
        return (imports == [] and named == [] and callable(getattr(view, "show_tk_lens_drawing_properties", None))
                and 0 <= shell_at < view_at,
                f"{PANEL.name}: tkinter or widgets imports at lines {imports or 'none'}, tkinter names {named or 'none'}; the "
                f"view module defines the window: {callable(getattr(view, 'show_tk_lens_drawing_properties', None))}; the panel "
                f"asks for a shell (char {shell_at}) before the Tk view (char {view_at})")

    def l():
        panel = _fresh("import sys\nimport KrakenOS.UI.panels.main_lens_drawing_dialogs\nprint('tkinter' in sys.modules)\n")
        service = _fresh("import sys\nimport KrakenOS.UI.services.layout_import_export\nprint('tkinter' in sys.modules)\n")
        return (panel == "False" and service == "False",
                f"tkinter loaded by importing the panel: {panel}; by importing the import/export service: {service}")

    return _claims((("S", s), ("L", l)))


def shell_checks() -> list:
    def claim_q():
        import tkinter as tk

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.lens_drawing_session import MESSAGE_TITLE, NO_LENSES, has_lens_elements
        from KrakenOS.UI.uihost import ScriptedUiHost

        host = ScriptedUiHost(answers={})
        editor = KrakenLayoutEditor(headless=True, ui=host)
        handed: list = []
        editor.show_lens_drawing_properties = lambda session: handed.append(session)
        empty = (has_lens_elements(editor.rows), editor._open_lens_drawing_surface_properties_dialog(), len(handed),
                 [list(args) for args, _kwargs in host.asked("showinfo")])

        editor.layout_files[LAYOUT.stem] = LAYOUT
        editor.load_layout_by_name(LAYOUT.stem, refresh=False)
        # a Tk window here would also WAIT, on nobody: refuse it at once, so the claim fails instead of hanging
        tk_windows: list = []

        def refuse(self, *_a, **_k):
            tk_windows.append(type(self).__name__)
            raise RuntimeError("a Tk window was made under a shell")

        init, tk.Toplevel.__init__ = tk.Toplevel.__init__, refuse
        try:
            editor.show_lens_drawing_properties = lambda session: (handed.append(session), session.continue_without_changes())
            continued = editor._open_lens_drawing_surface_properties_dialog()
            editor.show_lens_drawing_properties = lambda session: (handed.append(session), session.cancel())
            cancelled = editor._open_lens_drawing_surface_properties_dialog(for_export=True)
        finally:
            tk.Toplevel.__init__ = init
        sessions = [(len(session.surface_indices), bool(session.for_export)) for session in handed]
        told = len(host.asked("showinfo"))
        view_imported = VIEW_MODULE in sys.modules
        return (empty == (False, False, 0, [[MESSAGE_TITLE, NO_LENSES]]) and continued is True and cancelled is False
                and sessions == [(LENS_SURFACES, False), (LENS_SURFACES, True)] and told == 1 and tk_windows == []
                and not view_imported,
                f"with no lens in the table (lens elements {empty[0]}) the command answers {empty[1]}, the shell is asked "
                f"{empty[2]} times and the host is told {empty[3]}; with the doublets loaded the shell is handed sessions of "
                f"(surfaces, for_export) {sessions}; continued answers {continued}, cancelled answers {cancelled}; the host was "
                f"told {told} time in all; Tk windows made {tk_windows}; the Tk view was imported: {view_imported}")

    return _claims((("Q", claim_q),))


def tk_checks() -> list:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.lens_drawing_session import TITLE, LensDrawingPropertiesSession

    sessions: list = []
    init = LensDrawingPropertiesSession.__init__
    LensDrawingPropertiesSession.__init__ = lambda self, *a, **k: (init(self, *a, **k), sessions.append(self))[0]

    editor = KrakenLayoutEditor()
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    editor.update()

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    def claim_t():
        seen: list = []

        def press(label):
            def script(window):
                editor.update()
                buttons = widgets(window, ttk.Button)
                seen.append({"is_toplevel": isinstance(window, tk.Toplevel), "owner_is_editor": window.master is editor,
                             "title": str(window.title()), "entries": len(widgets(window, ttk.Entry)),
                             "buttons": sorted(str(b.cget("text")) for b in buttons), "window": window,
                             "listeners": len(sessions[-1].listeners)})
                next(b for b in buttons if str(b.cget("text")) == label).invoke()
                editor.update()
            return script

        editor.wait_window = press("Close")
        closed = editor._open_lens_drawing_surface_properties_dialog()
        editor.wait_window = press("Cancel Export")
        cancelled = editor._open_lens_drawing_surface_properties_dialog(for_export=True)
        editor.update()
        expected = [{"is_toplevel": True, "owner_is_editor": True, "title": TITLE,
                     "entries": LENS_SURFACES * len(session.fields()),
                     "buttons": sorted(label for label, _method in session.buttons()), "listeners": 1}
                    for session in sessions]
        shown = [{key: value for key, value in record.items() if key != "window"} for record in seen]
        gone = [not bool(record["window"].winfo_exists()) for record in seen]
        left = [len(session.listeners) for session in sessions]
        fields = len(sessions[0].fields()) if sessions else 0
        return (len(sessions) == 2 and shown == expected and fields >= 10 and all(len(e["buttons"]) == 6 for e in expected)
                and closed is True and cancelled is False and gone == [True, True] and left == [0, 0],
                f"with no shell the command opened {len(seen)} Tk windows owned by the editor, titled "
                f"{[record['title'] for record in shown]}, with {[record['entries'] for record in shown]} entries "
                f"({LENS_SURFACES} surfaces x {fields} properties) and the buttons {[record['buttons'] for record in shown]}, as "
                f"the sessions say: {shown == expected}; Close answers {closed}, Cancel Export answers {cancelled}; the windows "
                f"are gone {gone}; listeners left on the sessions {left}")

    return _claims((("T", claim_t),))


def _run(call: str, claim: str, needs_display: bool) -> list:
    driver = (
        "import json, os\n"
        + ("if not os.environ.get('DISPLAY'):\n"
           f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
           "    raise SystemExit(0)\n" if needs_display else "")
        + "from KrakenOS.UI.validate_lens_drawing_tk_view import shell_checks, tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk teardown crash must not lose it)
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
    rows += _run("shell_checks()", "Q", False) + _run("tk_checks()", "T", True)
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
