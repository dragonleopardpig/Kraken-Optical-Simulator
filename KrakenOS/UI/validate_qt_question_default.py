"""Guard for bugs/0988: a question's default answer is the same in both shells.

The model asks its yes/no questions through the UI host and may say which answer is the safe one:
"Import Lens from Folder" replaces the whole working scene, so its "Replace the scene now?" is
asked with `default="no"`. Tk's message box honours that -- Enter answers No. The Qt host dropped
the option: the dialog opened with Yes focused, and Enter replaced the scene.

  P  the Tk host hands `default` to tkinter unchanged, for each of its four questions
  M  the model's one question that names a default, on a headless editor holding the two-arm
     doublets: with nothing an import would discard it is not asked at all; with a camera body
     attached it is asked once, with `default="no"`, and answered no the scene is kept, the status
     line says so, the command returns nothing and no folder is asked for
  Q  the real Qt dialogs, each opened by the Qt host and answered by pressing Enter: with a
     default, that button is the dialog's default button, has the focus, and is what Enter
     answers -- for yes/no, ok/cancel, yes/no/cancel and retry/cancel; with no default the
     affirmative button has the focus and answers, which is Tk's first button; a word that is no
     button of that dialog changes nothing
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

RESULT_MARK = "QUESTIONDEFAULT_RESULT "
SKIP_MARK = "QUESTIONDEFAULT_SKIP "
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
#: question -> the button that answers when no default is given: Tk's first button
AFFIRMATIVE = {"askyesno": "Yes", "askokcancel": "OK", "askyesnocancel": "Yes", "askretrycancel": "Retry", "askquestion": "Yes"}
#: question -> [(the default asked for, the button that must be default, what Enter must answer)]
EXPECTED = {
    "askyesno": [("no", "No", False), ("yes", "Yes", True), (None, None, True), ("cancel", None, True)],
    "askokcancel": [("cancel", "Cancel", False), ("ok", "OK", True), (None, None, True)],
    "askyesnocancel": [("cancel", "Cancel", None), ("no", "No", False), ("yes", "Yes", True), (None, None, True)],
    "askretrycancel": [("cancel", "Cancel", False), ("retry", "Retry", True), (None, None, True)],
    "askquestion": [("no", "No", "no"), (None, None, "yes")],
}


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
    def p():
        import tkinter.messagebox as tk_messagebox

        from KrakenOS.UI.uihost.tk_host import TkUiHost

        host = TkUiHost(SimpleNamespace())
        got = {}
        for name, default in (("askyesno", "no"), ("askokcancel", "cancel"), ("askyesnocancel", "cancel"), ("askretrycancel", "cancel")):
            seen: list = []
            real = getattr(tk_messagebox, name)
            setattr(tk_messagebox, name, lambda *args, _seen=seen, **options: _seen.append((args, options)))
            try:
                getattr(host, name)("A title", "A question?", default=default)
            finally:
                setattr(tk_messagebox, name, real)
            got[name] = seen
        handed = {name: [options.get("default") for _args, options in seen] for name, seen in got.items()}
        return (handed == {"askyesno": ["no"], "askokcancel": ["cancel"], "askyesnocancel": ["cancel"], "askretrycancel": ["cancel"]}
                and all(seen[0][0] == ("A title", "A question?") for seen in got.values()),
                f"the Tk host hands tkinter the default it was given: {handed}")

    return _claims((("P", p),))


def model_checks() -> list:
    def m():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.uihost import ScriptedUiHost

        host = ScriptedUiHost(answers={"askyesno": False})
        editor = KrakenLayoutEditor(headless=True, ui=host)
        editor.layout_files[LAYOUT.stem] = LAYOUT
        editor.load_layout_by_name(LAYOUT.stem, refresh=False)
        before = [(row.surface, row.name) for row in editor.rows]
        plain = (bool(editor._import_would_discard_scene()), editor.import_machine_vision_lens_from_folder(),
                 len(host.asked("askyesno")), len(host.asked("askdirectory")))
        host.calls.clear()
        editor.imported_camera_step_path = "a vendor camera body.step"
        would_discard = bool(editor._import_would_discard_scene())
        answer = editor.import_machine_vision_lens_from_folder()
        asked = host.asked("askyesno")
        defaults = [options.get("default") for _args, options in asked]
        texts = [str(args[1])[-22:] for args, _options in asked]
        kept = [(row.surface, row.name) for row in editor.rows] == before
        status = str(editor.status_var.get())
        folders = len(host.asked("askdirectory"))
        return (plain == (False, None, 0, 1) and would_discard and defaults == ["no"] and texts == ["Replace the scene now?"]
                and answer is None and kept and status == "Import Lens from Folder cancelled; scene kept." and folders == 0
                and len(before) >= 10,
                f"with nothing to discard (would discard, answer, questions, folders asked for) {plain}; with a camera body "
                f"attached ({would_discard}, {len(before)} rows) the model asks {texts} with the "
                f"default {defaults}; answered no it returns {answer!r}, keeps the rows ({kept}), says {status!r} and asks for "
                f"a folder {folders} times")

    return _claims((("M", m),))


def qt_checks() -> list:
    def q():
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication, QMessageBox

        from KrakenOS.UI.uihost.qt_host import QtUiHost

        app = QApplication.instance() or QApplication(["guard"])
        host = QtUiHost(None)
        seen: list = []

        def press_enter(tries: int = 0) -> None:
            box = app.activeModalWidget()
            if not isinstance(box, QMessageBox):
                if tries < 200:
                    QTimer.singleShot(25, lambda: press_enter(tries + 1))
                return
            default, focus = box.defaultButton(), box.focusWidget()
            seen.append((default.text().replace("&", "") if default is not None else None,
                         focus.text().replace("&", "") if focus is not None and hasattr(focus, "text") else None,
                         [button.text().replace("&", "") for button in box.buttons()]))
            QTest.keyClick(box, Qt.Key_Return)

        wrong, opened = [], 0
        for name, cases in EXPECTED.items():
            for default, button, expected in cases:
                options = {} if default is None else {"default": default}
                before = len(seen)
                QTimer.singleShot(40, press_enter)
                answer = getattr(host, name)("A title", "A question?", **options)
                opened += 1
                shown = seen[before] if len(seen) > before else (None, None, [])
                # with a default: that button is the default one and focused; without: the affirmative one is focused
                right_button = (shown[0] == button and shown[1] == button) if button is not None else shown[1] == AFFIRMATIVE[name]
                if not (right_button and answer == expected and type(answer) is type(expected)):
                    wrong.append((name, default, {"default_button": shown[0], "focus": shown[1], "buttons": shown[2],
                                                   "enter_answers": answer, "expected": [button, expected]}))
        return (not wrong and opened == 16 and len(seen) == 16,
                f"{opened} Qt dialogs opened and answered with Enter; with a default that button is the default one, focused, "
                f"and what Enter answers; with none, or a word that is no button, the affirmative button answers; wrong: "
                f"{wrong or 'none'}")

    return _claims((("Q", q),))


def _run(call: str, claim: str, needs: str) -> list:
    driver = (
        "import json, os\n"
        + ("if not os.environ.get('DISPLAY'):\n"
           f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
           "    raise SystemExit(0)\n" if needs else "")
        + needs
        + "from KrakenOS.UI.validate_qt_question_default import model_checks, qt_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
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
        rows = [["P", False, f"raised {type(exc).__name__}: {exc}"]]
    rows += _run("model_checks()", "M", "") + _run("qt_checks()", "Q", "import PySide6\n")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
