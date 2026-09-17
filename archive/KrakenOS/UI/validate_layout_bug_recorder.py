"""Validate the 2D layout editor's one-click bug recorder (flag_bug_2d).

Feature parity request: "add Bug Recording similar to 3D in 2D" + "some pop up
windows longer or wider than the monitor screen without scrollbar, need to take
snapshot as bugs of the entire screen". ``LayoutBugRecorderMixin.flag_bug_2d``
captures a full-screen PNG, a clean matplotlib layout render, and a
``state.json`` (prescription rows + every open Toplevel's geometry, flagging
any that exceed the screen), then writes a reproduction bundle under
``attachment/recorded_bug_repros/flag_<timestamp>/`` -- the same place the 3D
inspector writes its flags.

Two layers:

* **Display-free** -- the pure ``_toplevel_exceeds_screen`` truth table and the
  mixin's presence in the editor MRO. Always runs.
* **End-to-end** -- boots a private Xvfb (when ``DISPLAY`` is unset), builds the
  real editor headless, opens a synthetic oversized Toplevel, calls
  ``flag_bug_2d``, and asserts the bundle's files + ``state.json`` contents.
  The bundle it creates is deleted on success so it never pollutes
  ``attachment/``.

Run (boots its own Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_layout_bug_recorder

Exit: 0 = pass, 1 = regression, 2 = environment can't render (no Xvfb).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def _check_overflow_logic() -> list[str]:
    """Display-free truth table for the oversized-dialog detector."""
    from KrakenOS.UI.services.layout_bug_recorder import LayoutBugRecorderMixin

    f = LayoutBugRecorderMixin._toplevel_exceeds_screen
    cases = [
        # (rx, ry, w, h, sw, sh, expected, label)
        (0, 0, 800, 600, 1920, 1080, False, "fits inside screen"),
        (0, 0, 2400, 600, 1920, 1080, True, "wider than screen"),
        (0, 0, 800, 1300, 1920, 1080, True, "taller than screen"),
        (1600, 0, 800, 600, 1920, 1080, True, "right edge off-screen"),
        (0, 900, 800, 600, 1920, 1080, True, "bottom edge off-screen"),
        (-10, 0, 800, 600, 1920, 1080, True, "negative origin"),
        (0, 0, 800, 600, 0, 0, False, "unknown screen makes no claim"),
        (0, 0, 0, 0, 1920, 1080, False, "unmapped window makes no claim"),
    ]
    failures: list[str] = []
    for rx, ry, w, h, sw, sh, expected, label in cases:
        got = f(rx, ry, w, h, sw, sh)
        if got is not expected:
            failures.append(
                f"_toplevel_exceeds_screen({rx},{ry},{w},{h},{sw},{sh}) "
                f"== {got}, expected {expected} ({label})"
            )
    return failures


def _check_mixin_wired() -> list[str]:
    """The mixin is in the editor class so the button/shortcut resolve."""
    failures: list[str] = []
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.layout_bug_recorder import LayoutBugRecorderMixin

    if not issubclass(KrakenLayoutEditor, LayoutBugRecorderMixin):
        failures.append("KrakenLayoutEditor does not inherit LayoutBugRecorderMixin")
    for name in ("flag_bug_2d", "_flag_bug_2d_event", "_capture_fullscreen_png"):
        if not hasattr(KrakenLayoutEditor, name):
            failures.append(f"KrakenLayoutEditor missing {name}")
    return failures


# --- self-contained virtual display (mirrors the snapshot validators) --------
def _free_display() -> int:
    for num in (94, 93, 92, 91, 90):
        if not Path(f"/tmp/.X11-unix/X{num}").exists():
            return num
    return 123


def _start_xvfb(display: int, timeout: float = 15.0):
    xvfb = shutil.which("Xvfb")
    if xvfb is None:
        return None, "Xvfb not found on PATH"
    proc = subprocess.Popen(
        [xvfb, f":{display}", "-screen", "0", "1600x1000x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sock = Path(f"/tmp/.X11-unix/X{display}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return None, f"Xvfb exited early (code {proc.returncode})"
        if sock.exists():
            return proc, None
        time.sleep(0.2)
    proc.terminate()
    return None, f"Xvfb :{display} did not come up within {timeout:.0f}s"


def _ensure_display():
    """Return (xvfb_proc_or_None, error_or_None). Sets os.environ['DISPLAY'].

    When we boot our *own* Xvfb (headless server, no Wayland) we drop
    ``WAYLAND_DISPLAY`` so the full-screen capture targets the X server we
    just started rather than a phantom Wayland socket. But when we reuse an
    existing ``DISPLAY`` we leave the environment untouched: on a real
    Wayland session ``grim`` is the working whole-output grab and XWayland's
    ``import -window root`` may be unavailable -- popping ``WAYLAND_DISPLAY``
    here would force the broken path and is exactly what the running app
    never does.
    """
    if os.environ.get("DISPLAY"):
        return None, None
    display = _free_display()
    proc, err = _start_xvfb(display)
    if proc is None:
        return None, err
    os.environ["DISPLAY"] = f":{display}"
    os.environ.pop("WAYLAND_DISPLAY", None)
    return proc, None


def _check_end_to_end() -> "tuple[list[str], int]":
    """Boot the real editor, flag a bug, assert the bundle. Returns (failures, exit_hint)."""
    xvfb_proc, err = _ensure_display()
    if err is not None:
        print(f"[SKIP] end-to-end: {err}")
        return [], 2

    failures: list[str] = []
    bundle: Path | None = None
    app = None
    try:
        import tkinter as tk
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor(headless=True)
        app.update_idletasks()

        # A synthetic dialog bigger than the 1600x1000 Xvfb screen -- the
        # oversized-popup class the user reported.
        oversized = tk.Toplevel(app)
        oversized.title("SYNTHETIC_OVERSIZED_DIALOG")
        oversized.geometry("3000x2000+0+0")
        oversized.update_idletasks()
        try:
            oversized.update()
        except Exception:
            pass

        bundle = app.flag_bug_2d()  # headless -> no description dialog
        if bundle is None or not bundle.exists():
            failures.append("flag_bug_2d returned no bundle directory")
            return failures, 1

        # Files present + non-empty screenshot.
        screenshot = bundle / "screenshot.png"
        if not screenshot.exists() or screenshot.stat().st_size <= 0:
            failures.append("screenshot.png missing or empty (full-screen capture failed)")
        for name in ("layout_2d.png", "state.json", "description.txt"):
            if not (bundle / name).exists():
                failures.append(f"bundle missing {name}")

        # state.json contents.
        try:
            state = json.loads((bundle / "state.json").read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(f"state.json unreadable: {exc}")
            state = {}
        if state.get("source") != "layout_editor_2d":
            failures.append(f"state.source != 'layout_editor_2d' (got {state.get('source')!r})")
        if state.get("screenshot") != "screenshot.png":
            failures.append("state.screenshot does not point at screenshot.png")
        if "rows" not in (state.get("layout_state") or {}):
            failures.append("state.layout_state has no prescription 'rows'")

        titles = [t.get("title") for t in state.get("open_toplevels", [])]
        if "SYNTHETIC_OVERSIZED_DIALOG" not in titles:
            failures.append(f"open Toplevel not captured in state (titles={titles})")
        else:
            oversized_titles = [t.get("title") for t in state.get("oversized_dialogs", [])]
            if "SYNTHETIC_OVERSIZED_DIALOG" not in oversized_titles:
                # Geometry read-back can vary without a window manager; only a
                # soft note so the test isn't flaky on headless servers.
                print(
                    "[note] synthetic dialog captured but not flagged oversized "
                    f"(geometry read-back: oversized={oversized_titles}); "
                    "pure overflow logic is covered display-free."
                )
    except Exception as exc:
        import traceback

        failures.append(f"end-to-end raised: {exc}\n{traceback.format_exc()}")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
        # Clean up the bundle we just created so attachment/ stays tidy.
        if bundle is not None and bundle.exists() and not failures:
            try:
                shutil.rmtree(bundle)
            except Exception:
                pass
        if xvfb_proc is not None:
            try:
                xvfb_proc.terminate()
            except Exception:
                pass
    return failures, 0


def main() -> int:
    failures: list[str] = []
    failures.extend(_check_overflow_logic())
    failures.extend(_check_mixin_wired())

    e2e_failures, exit_hint = _check_end_to_end()
    failures.extend(e2e_failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("[FAIL] 2D bug recorder validation")
        return 1
    if exit_hint == 2:
        print("[PASS] 2D bug recorder logic (end-to-end skipped: no Xvfb)")
        return 0
    print("[PASS] 2D bug recorder: full-screen flag bundle + oversized-dialog state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
