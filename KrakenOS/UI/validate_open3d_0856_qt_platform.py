"""Display-free guard: the Qt shell picks a platform the VTK viewport can live on (bugs/0856,
docs/design_qt_migration.md phase 2).

`QVTKRenderWindowInteractor` gives VTK the Qt widget's window id, and VTK draws on X11. Under the
Wayland platform plugin that id is a Wayland surface, so VTK asks the X server to configure a
window it has never heard of -- and Xlib's default error handler EXITS THE PROCESS: no traceback,
no Python exception, which is how the user met this.

  D  the decision table, display-free: Wayland + DISPLAY -> xcb; an explicit QT_QPA_PLATFORM is
     never overridden; Wayland with no DISPLAY is refused with a reason; a plain X session and a
     non-Linux platform are left alone
  R  require_viewport_platform accepts xcb and offscreen, raises for wayland, and the message
     names the variable to set
  Q  in a SUBPROCESS with WAYLAND_DISPLAY set and QT_QPA_PLATFORM unset -- the environment that
     aborted -- the REAL build() brings the shell up on xcb with an OpenGL render window
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"


def qt_runtime_checks() -> list[list]:
    """Build the REAL shell in a Wayland-looking environment. Returns [name, ok, detail] rows."""
    from PySide6.QtWidgets import QApplication

    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    render_window = window.viewport.render_window
    ok = (QApplication.instance().platformName() == "xcb"
          and render_window.IsA("vtkOpenGLRenderWindow"))
    detail = (f"with WAYLAND_DISPLAY set and QT_QPA_PLATFORM unset, build() came up on "
              f"{QApplication.instance().platformName()!r} and the viewport got a "
              f"{render_window.GetClassName()}")
    window.close()
    return [["Q", ok, detail]]


def _run_qt_subprocess() -> tuple[str, list[list]]:
    driver = (
        "import json, os, sys\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the viewport needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0856_qt_platform import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None)
    # Reproduce the reported environment: a Wayland session with an X server alongside it.
    env["WAYLAND_DISPLAY"] = env.get("WAYLAND_DISPLAY") or "wayland-0"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Qt subprocess", False, "timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Qt platform", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Qt subprocess", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.qt.app import VIEWPORT_PLATFORM, choose_qt_platform, require_viewport_platform

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- D the decision table ------------------------------------------------------------------
    wayland_with_x = choose_qt_platform({"WAYLAND_DISPLAY": "wayland-1", "DISPLAY": ":0"})
    explicit = choose_qt_platform({"WAYLAND_DISPLAY": "wayland-1", "DISPLAY": ":0",
                                   "QT_QPA_PLATFORM": "offscreen"})
    wayland_only = choose_qt_platform({"WAYLAND_DISPLAY": "wayland-1"})
    plain_x = choose_qt_platform({"DISPLAY": ":0"})
    decisions = {"wayland+X": wayland_with_x[0], "explicit": explicit[0],
                 "wayland only": wayland_only[0], "plain X": plain_x[0]}
    ok(decisions == {"wayland+X": VIEWPORT_PLATFORM, "explicit": None, "wayland only": None,
                     "plain X": None}
       and "no X server" in wayland_only[1] and "already" in explicit[1],
       f"D: {decisions}; a Wayland session with no DISPLAY is refused with a reason "
       f"({wayland_only[1][:48]}...) and an explicit choice is kept ({explicit[1][:40]}...)")

    real = sys.platform.startswith("linux")
    ok(not real or choose_qt_platform({"DISPLAY": ":0", "WAYLAND_DISPLAY": "w"})[0] == "xcb",
       f"D2: on this platform ({sys.platform}) the Wayland case resolves to {VIEWPORT_PLATFORM!r}")

    # ---- R the refusal -------------------------------------------------------------------------
    accepted = []
    for name in ("xcb", "offscreen"):
        try:
            require_viewport_platform(name)
            accepted.append(name)
        except RuntimeError:
            pass
    message = ""
    try:
        require_viewport_platform("wayland")
    except RuntimeError as exc:
        message = str(exc)
    ok(accepted == ["xcb", "offscreen"] and "QT_QPA_PLATFORM=xcb" in message
       and "aborts" in message,
       f"R: accepts {accepted}, refuses 'wayland' with a message that names the fix "
       f"({message[-46:]!r})")

    # ---- Q the real build, in the environment that aborted -------------------------------------
    status, rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {rows[0][2]}")
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
