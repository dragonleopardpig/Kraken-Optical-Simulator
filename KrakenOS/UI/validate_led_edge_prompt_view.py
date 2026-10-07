"""Guard for bugs/0977: the LED edge-distance window is a Tk panel; the service asks, it does not draw.

Phase 7d of the Qt migration, the third service. `services/scene_placement_commands.py` imported
tkinter for one small window -- a value, Save, Cancel -- that the Tk app opens for "Set LED edge
distance" (a shell asks in its own prompt instead, bugs/0950). The window is
`panels/main_led_edge_prompt.py` now and the service imports no tkinter.

What the two shells do with the whole command on a real scene is phase 723's (Q2 and T there). This
guard holds what that one does not:

  S  the service imports and names no tkinter; `_ask_led_edge_distance` reaches `shell_host_of`
     BEFORE it delegates, and delegates to a method the panel class defines
  M  the model under a shell, no display: the shell's number prompt is asked with the title, the
     prompt, the distance prefilled and a floor of zero; the answer comes back, a negative one as
     zero, a cancelled one as None, a negative start is prefilled as zero -- and the Tk panel is
     never built
  T  the Tk window, in a real Tk editor: its title, its prompt, the value prefilled, Save and
     Cancel, Return and Escape bound; Save takes the typed value, a negative one as zero; a value
     that is no number says so on the status line and LEAVES THE WINDOW OPEN; Cancel gives None
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

RESULT_MARK = "LEDPROMPT_RESULT "
SKIP_MARK = "LEDPROMPT_SKIP "
SERVICE = Path("KrakenOS/UI/services/scene_placement_commands.py")
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
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin as Model

    def s():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.panels.main_led_edge_prompt import MainLedEdgePrompt

        tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
        imports = sorted({node.lineno for node in ast.walk(tree)
                          if (node.__class__ is ast.Import and any(a.name.split(".")[0] == "tkinter" for a in node.names))
                          or (isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tkinter")})
        named = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in TK_NAMES})
        toplevels = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Call)
                        and (getattr(node.func, "attr", "") or getattr(node.func, "id", "")) == "Toplevel")
        source = inspect.getsource(Model._ask_led_edge_distance)
        shell_at, panel_at = source.find("shell_host_of("), source.find("self._main_led_edge_prompt().ask_led_edge_distance(")
        factory = inspect.signature(KrakenLayoutEditor._main_led_edge_prompt).return_annotation
        return (imports == [] and named == [] and toplevels == 0 and 0 <= shell_at < panel_at
                and "ask_led_edge_distance" in vars(MainLedEdgePrompt) and factory in (MainLedEdgePrompt, "MainLedEdgePrompt"),
                f"{SERVICE.name}: tkinter imports at lines {imports or 'none'}, tkinter names {named or 'none'}, Toplevels built "
                f"{toplevels}; `_ask_led_edge_distance` reaches the shell (char {shell_at}) before the panel (char {panel_at}); "
                f"the panel defines the method: {'ask_led_edge_distance' in vars(MainLedEdgePrompt)}")

    def m():
        from KrakenOS.UI.panels.main_led_edge_prompt import PROMPT, TITLE
        from KrakenOS.UI.uihost import ScriptedUiHost

        def owner(answers):
            def no_panel():
                raise AssertionError("the Tk panel was asked for under a shell")

            return SimpleNamespace(ui=ScriptedUiHost(answers={"askfloat": list(answers)}), _main_led_edge_prompt=no_panel)

        asked = owner([12.5, -4.0, None, 3.0])
        answers = [Model._ask_led_edge_distance(asked, 128.7), Model._ask_led_edge_distance(asked, 128.7),
                   Model._ask_led_edge_distance(asked, 128.7), Model._ask_led_edge_distance(asked, -9.0)]
        calls = asked.ui.asked("askfloat")
        first_args, first_options = calls[0]
        return (answers == [12.5, 0.0, None, 3.0] and len(calls) == 4 and tuple(first_args) == (TITLE, PROMPT)
                and first_options == {"initialvalue": 128.7, "minvalue": 0.0} and calls[3][1]["initialvalue"] == 0.0,
                f"under a shell the prompt is asked as {tuple(first_args)!r} with {first_options}; the answers 12.5, -4, a "
                f"cancel and 3 come back as {answers}; a start of -9 is prefilled as {calls[3][1]['initialvalue']}; the Tk "
                f"panel was never asked for")

    return _claims((("S", s), ("M", m)))


def tk_checks() -> list:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels.main_led_edge_prompt import PROMPT, TITLE

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    def press(window, text) -> None:
        next(b for b in widgets(window, ttk.Button) if str(b.cget("text")) == text).invoke()

    plan: list = []          # what the next waited-on window is told: [(typed text or None, button), ...]
    seen: list = []          # what it showed: title, prompt, prefill, buttons, bindings, and after each step

    def scripted_wait(self, window=None):
        target = window or self
        entry = widgets(target, ttk.Entry)[0]
        shown = {"title": str(target.title()), "labels": [str(w.cget("text")) for w in widgets(target, ttk.Label)],
                 "prefill": entry.get(), "buttons": [str(b.cget("text")) for b in widgets(target, ttk.Button)],
                 "keys": [bool(target.bind("<Return>")), bool(target.bind("<Escape>"))], "steps": []}
        for typed, button in plan.pop(0):
            if typed is not None:
                entry.delete(0, "end")
                entry.insert(0, typed)
            press(target, button)
            shown["steps"].append((bool(target.winfo_exists()), str(editor.status_var.get())))
        seen.append(shown)

    wait, tk.Misc.wait_window = tk.Misc.wait_window, scripted_wait
    editor = KrakenLayoutEditor()
    for _ in range(3):
        editor.update()

    def claim_t():
        try:
            answers = []
            for start, steps in ((12.5, [("7.25", "Save")]), (12.5, [("-3", "Save")]),
                                 (12.5, [("abc", "Save"), (None, "Cancel")]), (12.5, [(None, "Cancel")]),
                                 (-9.0, [(None, "Save")])):
                editor.status_var.set("")
                plan.append(steps)
                answers.append(editor._ask_led_edge_distance(start))
        finally:
            tk.Misc.wait_window = wait
        first, invalid, negative_start = seen[0], seen[2], seen[4]
        return (answers == [7.25, 0.0, None, None, 0.0] and len(seen) == 5
                and first["title"] == TITLE and first["labels"] == [PROMPT] and first["prefill"] == "12.5"
                and first["buttons"] == ["Save", "Cancel"] and first["keys"] == [True, True]
                and first["steps"] == [(False, "")]
                and invalid["steps"] == [(True, "Invalid LED edge distance."), (False, "Invalid LED edge distance.")]
                and negative_start["prefill"] == "0",
                f"the window {first['title']!r} shows {first['labels']}, prefilled {first['prefill']!r}, buttons "
                f"{first['buttons']}, Return and Escape bound {first['keys']}; typing 7.25 / -3 and Save, 'abc' and Save then "
                f"Cancel, Cancel, and Save on a start of -9 give {answers}; after 'abc' the window is still open "
                f"({invalid['steps'][0][0]}) and the status line says {invalid['steps'][0][1]!r}")

    return _claims((("T", claim_t),))


def _run(call: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_led_edge_prompt_view import tk_checks\n"
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
