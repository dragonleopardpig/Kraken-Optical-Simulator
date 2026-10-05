"""Guard for bugs/0963: the ribbon folds by the WINDOW's height, not the screen's.

Noticed in bugs/0958: the ribbon decided at start-up, from the SCREEN's height, whether to start
folded. A 950-px window on a 1440-px screen opened with the ribbon open and a 339-px 3D view, and
a window made short or tall later never changed it. Now it follows the window -- until the user
folds or opens it by hand.

Run on a private 2560x1440 virtual screen -- a TALL screen, where the old rule left the ribbon open --
in a real Qt shell on the two-arm doublets example (in git):

  S  a 950-px window on the 1440-px screen starts with the ribbon folded
  G  made 1300 px tall, the window opens the ribbon; made 950 again, it folds it -- on CROSSING the
     line only: a programmatic open at 950 survives a resize to 940
  H  folded or opened BY HAND (the fold arrow) stays that way through resizes across the line
  C  while Clean 3D Scene is on, a resize across the line leaves the ribbon folded; turned off, it
     puts back what it saved
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RESULT_MARK = "RIBBONHEIGHT_RESULT "
SKIP_MARK = "RIBBONHEIGHT_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
TALL_SCREEN = "2560x1440x24"


def qt_runtime_checks() -> dict:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.ribbon import FOLD_BELOW_WINDOW_HEIGHT

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    view = window.build_scene()
    window.load_layout_path(SCENE)
    ribbon = window.ribbon
    rows = []

    def settle(seconds: float = 0.4) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    def resize(height: int) -> tuple:
        window.resize(window.width(), height)
        settle(0.5)
        return (window.height(), ribbon.collapsed, view.widget.height())

    settle(2.0)
    screen = window.screen().availableGeometry().height()
    start = (window.height(), ribbon.collapsed)
    rows.append(["S", screen >= FOLD_BELOW_WINDOW_HEIGHT and start == (950, True),
                 f"a {start[0]}-px window on a {screen}-px screen: folded {start[1]}"])

    tall = resize(1300)
    short = resize(950)
    ribbon.set_collapsed(False)                   # opened by code, not by hand
    settle(0.3)
    kept = resize(940)                            # still short: no crossing, no refold
    resize(950)
    ribbon.set_collapsed(True)
    settle(0.3)
    rows.append(["G", tall[:2] == (1300, False) and short[:2] == (950, True) and kept[:2] == (940, False)
                 and ribbon.follows_window,
                 f"(window height, folded, 3D view height): 1300 -> {tall}; 950 -> {short}; opened by code at 950, "
                 f"then 940 -> {kept}"])

    QTest.mouseClick(ribbon.fold_button, Qt.MouseButton.LeftButton)     # opened by hand at 950
    settle(0.3)
    by_hand_open = ribbon.collapsed
    after = [resize(height)[1] for height in (1300, 940, 1300)]
    QTest.mouseClick(ribbon.fold_button, Qt.MouseButton.LeftButton)     # folded by hand
    settle(0.3)
    after_fold = [resize(height)[1] for height in (1300, 950)]
    rows.append(["H", by_hand_open is False and after == [False, False, False] and after_fold == [True, True]
                 and not ribbon.follows_window,
                 f"opened by the arrow at 950: folded {by_hand_open}; resized 1300/940/1300 -> folded {after}; folded "
                 f"by the arrow, resized 1300/950 -> folded {after_fold}"])

    # a fresh ribbon state for C: following the window again, folded at 950
    ribbon.follows_window = True
    ribbon._window_short = True
    ribbon.set_collapsed(True)
    resize(950)
    window.action_manager["clean_scene"].trigger()
    settle(0.3)
    during = resize(1300)[1]
    window.action_manager["clean_scene"].trigger()
    settle(0.5)
    rows.append(["C", during is True and ribbon.collapsed is True,
                 f"Clean 3D Scene on, window made 1300 px: folded {during}; turned off: folded {ribbon.collapsed} "
                 f"(it was folded when the clean scene began)"])
    return {"rows": rows}


def _free_display() -> "int | None":
    for number in range(180, 200):
        if not Path(f"/tmp/.X11-unix/X{number}").exists() and not Path(f"/tmp/.X{number}-lock").exists():
            return number
    return None


def _run(call: str) -> list:
    xvfb = shutil.which("Xvfb")
    number = _free_display()
    if xvfb is None or number is None:
        return [["X", True, "SKIP: no Xvfb for a tall private screen"]]
    server = subprocess.Popen([xvfb, f":{number}", "-screen", "0", TALL_SCREEN, "-nolisten", "tcp"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 15
        while time.time() < deadline and not Path(f"/tmp/.X11-unix/X{number}").exists():
            time.sleep(0.1)
        driver = (
            "import json, os\n"
            "try:\n"
            "    import PySide6\n"
            "except Exception as exc:\n"
            f"    print({SKIP_MARK!r} + repr(exc))\n"
            "    raise SystemExit(0)\n"
            "from KrakenOS.UI.validate_qt_ribbon_window_height import qt_runtime_checks\n"
            # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
            f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
            "os._exit(0)\n"
        )
        env = dict(os.environ)
        env.pop("WAYLAND_DISPLAY", None)
        env["QT_QPA_PLATFORM"] = "xcb"
        env["DISPLAY"] = f":{number}"
        try:
            proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                                  env=env, cwd=str(Path.cwd()))
        except subprocess.TimeoutExpired:
            return [["X", False, f"{call} timed out"]]
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])["rows"]
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = _run("qt_runtime_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
