"""Regression: the ``s`` bug-flag captures the focused popup dialog, not just
the 3D scene behind it.

Bug 0003 Issue 1 made the ``s`` hotkey *fire* inside the CAD/STL face editor,
but ``flag_bug`` still screenshotted the VTK render window -- so a press while
the face editor was open saved the 3D scene, never the dialog the user was
looking at (confirmed from ``flag_20260603_072730_717`` "still 160 faces": the
saved PNG is the 3D scene, not the face list).

This pins the fix:

  * ``Kraken3DInspector._classify_dialog_toplevel`` routes a focused popup (the
    face editor) to a dialog capture, and the main inspector window / editor
    root to the 3D scene (pure decision -- only needs Tk widgets built).
  * ``Kraken3DInspector._capture_toplevel_png`` actually grabs a Toplevel's
    pixels: a window filled solid red comes back as a mostly-red PNG of about
    the right size. This exercises the Linux X11/XWayland ``import -window
    <xid>`` path under Xvfb; macOS/Windows use PIL ``ImageGrab``, Wayland uses
    ``grim`` (universal across the GitHub user base, not just this dev box).

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_flag_dialog_capture

Exit: 0 = pass, 1 = regression, 2 = environment can't render / no capture backend.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _free_display() -> int:
    for num in (95, 94, 93, 92, 91, 90):
        if not Path(f"/tmp/.X11-unix/X{num}").exists():
            return num
    return 123


def _start_xvfb(display: int, timeout: float = 15.0):
    xvfb = shutil.which("Xvfb")
    if xvfb is None:
        return None, "Xvfb not found on PATH"
    proc = subprocess.Popen(
        [xvfb, f":{display}", "-screen", "0", "1280x900x24"],
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
    # Always use a private Xvfb (X11) and mask Wayland. Window-pixel capture
    # must be deterministic and must not grab the developer's live desktop;
    # this also exercises the portable `import -window <xid>` X11 path.
    # ImageMagick's X11 grab does not work under XWayland, so reusing an
    # ambient :0 (which is XWayland on a Wayland box) would be flaky.
    os.environ.pop("WAYLAND_DISPLAY", None)
    display = _free_display()
    proc, err = _start_xvfb(display)
    if proc is None:
        return None, err
    os.environ["DISPLAY"] = f":{display}"
    return proc, None


def _run() -> int:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import Kraken3DInspector

    failures: list[str] = []

    root = tk.Tk()
    root.geometry("300x200+40+40")
    try:
        # --- 1. Pure decision: which window does `s` screenshot? ---
        own_tl = tk.Toplevel(root)   # stands in for the inspector's own window
        own_tl.geometry("200x150+360+40")
        dialog = tk.Toplevel(root)   # stands in for the CAD/STL face editor
        dialog.geometry("200x150+580+40")
        in_dialog = ttk.Treeview(dialog)
        in_dialog.pack()
        in_own = ttk.Button(own_tl, text="x")
        in_own.pack()
        in_root = ttk.Button(root, text="y")
        in_root.pack()
        root.update_idletasks()
        root.update()

        classify = Kraken3DInspector._classify_dialog_toplevel
        if classify(None, own_tl, root) is not None:
            failures.append("classify(no focus) should be None -> 3D scene")
        if classify(in_dialog, own_tl, root) is not dialog:
            failures.append("classify(widget in popup) should return the popup toplevel")
        if classify(in_own, own_tl, root) is not None:
            failures.append("classify(widget in inspector window) should be None -> 3D scene")
        if classify(in_root, own_tl, root) is not None:
            failures.append("classify(widget in editor root) should be None -> 3D scene")

        # --- 2. Real capture: a solid-red Toplevel -> a mostly-red PNG. ---
        have_backend = bool(shutil.which("import") or shutil.which("grim"))
        try:
            from PIL import ImageGrab  # noqa: F401

            have_backend = True
        except Exception:
            pass
        if not have_backend:
            print("SKIP: no window-capture backend (import/grim/ImageGrab).", file=sys.stderr)
            return 2

        cap = tk.Toplevel(root)
        cap_w, cap_h = 480, 320
        cap.geometry(f"{cap_w}x{cap_h}+80+80")
        cap.title("capture-target")
        fill = tk.Frame(cap, bg="#ff0000", width=cap_w, height=cap_h)
        fill.pack(fill="both", expand=True)
        cap.update_idletasks()
        cap.deiconify()
        cap.lift()
        try:
            cap.wait_visibility(cap)
        except Exception:
            pass
        for _ in range(6):
            cap.update()
        time.sleep(0.2)

        # Stable path (overwritten each run) so the fixer can open it by eye.
        out_path = Path(tempfile.gettempdir()) / "krakenos_dialog_capture_test.png"
        try:
            ok = Kraken3DInspector._capture_toplevel_png(cap, out_path)
        except Exception as exc:
            failures.append(f"_capture_toplevel_png raised: {exc}")
            ok = False

        if not ok:
            failures.append("_capture_toplevel_png returned False where a backend exists")
        elif not out_path.exists():
            failures.append("_capture_toplevel_png returned True but no PNG on disk")
        else:
            try:
                import numpy as np
                from PIL import Image

                with Image.open(out_path) as img:
                    arr = np.asarray(img.convert("RGB"))
                    h, w = arr.shape[0], arr.shape[1]
                    if abs(w - cap_w) > 16 or abs(h - cap_h) > 16:
                        failures.append(f"captured size {w}x{h} far from dialog {cap_w}x{cap_h}")
                    red_mask = (arr[..., 0] > 200) & (arr[..., 1] < 80) & (arr[..., 2] < 80)
                    frac = float(red_mask.mean())
                    if frac < 0.5:
                        failures.append(
                            f"captured PNG only {frac:.0%} red; expected the red dialog (>50%)"
                        )
                    else:
                        print(f"  dialog capture: {w}x{h}, {frac:.0%} red -> {out_path}")
            except Exception as exc:
                failures.append(f"could not analyze captured PNG: {exc}")

        if failures:
            for msg in failures:
                print(f"FAIL: {msg}", file=sys.stderr)
            return 1
        print(
            "PASS: `s` flag captures the focused dialog "
            "(classify routes popups to a dialog grab; solid-red Toplevel -> mostly-red PNG)."
        )
        return 0
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def main() -> int:
    xvfb, err = _ensure_display()
    if err:
        print(f"SKIP: {err}", file=sys.stderr)
        return 2
    try:
        return _run()
    finally:
        if xvfb is not None:
            try:
                xvfb.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
