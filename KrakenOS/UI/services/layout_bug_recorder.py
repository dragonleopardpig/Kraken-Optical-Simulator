"""One-click bug flagging for the 2D layout editor.

The Open 3D inspector already has a ``flag_bug`` (screenshot + scene state +
description) that writes a reproduction bundle under
``attachment/recorded_bug_repros/flag_<timestamp>/``. The 2D editor is pure
Tk + matplotlib (no VTK render window), so this mixin provides the same
one-click flow with three captures suited to that surface:

* a **full-screen** PNG (``screenshot.png``) -- the whole monitor, so a popup
  dialog that is taller/wider than the screen (and has no scrollbar) is
  documented even though it spills past the editor window. This is the
  capture the user explicitly asked for: "snapshot as bugs of the entire
  screen".
* a clean render of the matplotlib layout canvas (``layout_2d.png``), so the
  optical layout itself stays legible regardless of window chrome.
* ``state.json`` -- the prescription rows + settings (reusing the editor's
  own ``_capture_saved_layout_state``) plus the geometry of every open
  Toplevel and a flag for any that exceed the screen bounds, which pins the
  oversized-dialog class of bug with numbers.

A non-modal description prompt then lets the user type what went wrong without
blocking; the bundle is written first so the screenshot is safe even if they
never finish typing.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from KrakenOS.UI.services.cad_cache_paths import PROJECT_ROOT

_ATTACHMENT_DIR = PROJECT_ROOT / "attachment"


class LayoutBugRecorderMixin:
    """Adds ``flag_bug_2d`` to the 2D ``KrakenLayoutEditor``."""

    @staticmethod
    def _toplevel_exceeds_screen(
        rx: int, ry: int, width: int, height: int, screen_w: int, screen_h: int
    ) -> bool:
        """True when a window is larger than, or spills past, the screen.

        Pure so it can be unit-tested without a display. Covers both a
        dialog that is simply bigger than the monitor and one whose
        bottom/right edge falls off-screen (the "no scrollbar, can't reach
        the OK button" case).
        """
        if width <= 0 or height <= 0 or screen_w <= 0 or screen_h <= 0:
            return False
        if width > screen_w or height > screen_h:
            return True
        if rx < 0 or ry < 0:
            return True
        if rx + width > screen_w or ry + height > screen_h:
            return True
        return False

    def _collect_open_toplevels(self) -> list[dict[str, object]]:
        """Geometry of every open Toplevel, flagged if it exceeds the screen.

        Walks the widget tree from the root so nested dialogs are included.
        Failures on any single window are swallowed -- a bug flag must never
        itself raise.
        """
        try:
            screen_w = int(self.winfo_screenwidth())
            screen_h = int(self.winfo_screenheight())
        except Exception:
            screen_w = screen_h = 0

        found: list[dict[str, object]] = []
        seen: set[str] = set()

        def _visit(widget) -> None:
            try:
                children = list(widget.winfo_children())
            except Exception:
                children = []
            for child in children:
                if isinstance(child, tk.Toplevel):
                    try:
                        key = str(child)
                    except Exception:
                        key = ""
                    if key and key not in seen:
                        seen.add(key)
                        try:
                            child.update_idletasks()
                        except Exception:
                            pass
                        try:
                            rx = int(child.winfo_rootx())
                            ry = int(child.winfo_rooty())
                            width = int(child.winfo_width())
                            height = int(child.winfo_height())
                        except Exception:
                            rx = ry = width = height = 0
                        try:
                            title = child.title()
                        except Exception:
                            title = ""
                        found.append(
                            {
                                "title": title,
                                "x": rx,
                                "y": ry,
                                "width": width,
                                "height": height,
                                "exceeds_screen": self._toplevel_exceeds_screen(
                                    rx, ry, width, height, screen_w, screen_h
                                ),
                            }
                        )
                _visit(child)

        try:
            _visit(self)
        except Exception:
            pass
        return found

    @staticmethod
    def _capture_fullscreen_png(out_path) -> bool:
        """Best-effort capture of the *entire screen* to ``out_path``.

        Cross-platform so the 2D flag grabs the whole monitor on any
        KrakenOS install -- this is what documents a dialog that runs off
        the edge of the screen. Strategies, first success wins:

          1. Wayland: ``grim`` (captures the composited output the user
             actually sees, including XWayland Tk windows).
          2. Linux X11 / XWayland: ImageMagick ``import -window root``.
          3. ``PIL.ImageGrab.grab()`` -- native on macOS / Windows, and on
             Linux when a backend is present.

        Returns True only if a non-empty PNG was written.
        """
        out_path = str(out_path)
        system = platform.system()

        def _wrote_image() -> bool:
            try:
                if not os.path.exists(out_path) or os.path.getsize(out_path) <= 0:
                    return False
            except Exception:
                return False
            try:
                from PIL import Image  # type: ignore

                with Image.open(out_path) as img:
                    img.verify()
            except Exception:
                return True
            return True

        if system not in {"Darwin", "Windows"}:
            # 1. Wayland whole-output grab.
            if os.environ.get("WAYLAND_DISPLAY"):
                grim = shutil.which("grim")
                if grim:
                    try:
                        subprocess.run(
                            [grim, out_path],
                            check=True,
                            timeout=20,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        if _wrote_image():
                            return True
                    except Exception:
                        pass
            # 2. X11 / XWayland root-window grab.
            if os.environ.get("DISPLAY"):
                magick = shutil.which("import")
                if magick:
                    try:
                        subprocess.run(
                            [magick, "-window", "root", out_path],
                            check=True,
                            timeout=20,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        if _wrote_image():
                            return True
                    except Exception:
                        pass

        # 3. Native full-screen grab (macOS / Windows; Linux with a backend).
        try:
            from PIL import ImageGrab  # type: ignore

            image = ImageGrab.grab()
            image.save(out_path)
            if _wrote_image():
                return True
        except Exception:
            pass

        return False

    def _save_layout_canvas_png(self, out_path) -> bool:
        """Render the matplotlib layout figure to ``out_path``."""
        figure = getattr(self, "figure", None)
        if figure is None:
            return False
        try:
            figure.savefig(str(out_path), dpi=150)
            return bool(os.path.exists(out_path) and os.path.getsize(out_path) > 0)
        except Exception as exc:
            self._bug_recorder_debug(f"2D flag canvas render failed: {exc}")
            return False

    def _bug_recorder_debug(self, message: str) -> None:
        try:
            self.append_debug(message)
        except Exception:
            pass

    def _flag_bug_2d_event(self, _event=None) -> str:
        """Ctrl+Shift+B accelerator: flag a bug, then stop the event."""
        try:
            self.flag_bug_2d()
        except Exception as exc:
            self._bug_recorder_debug(f"2D flag (keyboard) failed: {exc}")
        return "break"

    def flag_bug_2d(self) -> "Path | None":
        """One-click 2D bug flag: full-screen shot + state + description.

        Captures the whole screen and the layout canvas, snapshots the
        prescription + open-dialog geometry, then opens a non-modal prompt
        for the description. The bundle is written before the prompt so the
        screenshot survives even if the user dismisses it.
        """
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        bundle_dir = _ATTACHMENT_DIR / "recorded_bug_repros" / f"flag_{stamp}"
        try:
            bundle_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self._set_bug_status(f"Flag bug failed: could not create bundle ({exc}).")
            return None

        try:
            self._set_bug_status("Flag bug: capturing full screen, please describe in the dialog...")
            self.update_idletasks()
        except Exception:
            pass

        screenshot_path = bundle_dir / "screenshot.png"
        screenshot_ok = False
        try:
            screenshot_ok = self._capture_fullscreen_png(screenshot_path)
        except Exception as exc:
            self._bug_recorder_debug(f"2D flag screenshot failed: {exc}")
        if not screenshot_ok:
            self._bug_recorder_debug(
                "2D flag: full-screen capture unavailable on this platform "
                "(need grim on Wayland, ImageMagick 'import' on X11, or PIL ImageGrab)."
            )

        canvas_path = bundle_dir / "layout_2d.png"
        canvas_ok = self._save_layout_canvas_png(canvas_path)

        try:
            toplevels = self._collect_open_toplevels()
        except Exception:
            toplevels = []
        try:
            screen_block = {
                "width": int(self.winfo_screenwidth()),
                "height": int(self.winfo_screenheight()),
            }
        except Exception:
            screen_block = {}
        try:
            editor_block = {
                "x": int(self.winfo_rootx()),
                "y": int(self.winfo_rooty()),
                "width": int(self.winfo_width()),
                "height": int(self.winfo_height()),
            }
        except Exception:
            editor_block = {}

        saved_state: dict[str, object] = {}
        capture_state = getattr(self, "_capture_saved_layout_state", None)
        if callable(capture_state):
            try:
                saved_state = capture_state()
            except Exception as exc:
                self._bug_recorder_debug(f"2D flag state snapshot failed: {exc}")

        try:
            (bundle_dir / "description.txt").write_text("", encoding="utf-8")
        except Exception:
            pass

        state_path = bundle_dir / "state.json"
        payload = {
            "version": 1,
            "captured_at_iso": datetime.now().isoformat(timespec="seconds"),
            "source": "layout_editor_2d",
            "description": "",
            "screenshot": "screenshot.png" if screenshot_ok else None,
            "screenshot_kind": "fullscreen",
            "layout_2d_png": "layout_2d.png" if canvas_ok else None,
            "screen": screen_block,
            "editor_window": editor_block,
            "open_toplevels": toplevels,
            "oversized_dialogs": [t for t in toplevels if t.get("exceeds_screen")],
            "layout_state": saved_state,
        }
        try:
            state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            self._bug_recorder_debug(f"2D flag state write failed: {exc}")

        oversized = payload["oversized_dialogs"]
        if oversized:
            self._set_bug_status(
                f"Flagged bug: {bundle_dir.name} "
                f"({len(oversized)} dialog(s) exceed the screen). Describe it in the popup."
            )
        else:
            self._set_bug_status(
                f"Flagged bug: {bundle_dir.name}. Type a description in the popup."
            )
        try:
            self.append_progress(f"Flagged 2D bug: {bundle_dir}")
        except Exception:
            pass

        if not getattr(self, "headless", False):
            self._open_2d_flag_description_dialog(bundle_dir=bundle_dir, state_path=state_path)
        return bundle_dir

    def _set_bug_status(self, message: str) -> None:
        status_var = getattr(self, "status_var", None)
        if status_var is not None:
            try:
                status_var.set(message)
                return
            except Exception:
                pass
        self._bug_recorder_debug(message)

    def _open_2d_flag_description_dialog(self, *, bundle_dir: Path, state_path: Path) -> None:
        """Non-modal description prompt; Save writes the text into the bundle."""
        try:
            popup = tk.Toplevel(self)
            popup.title(f"Flag: {bundle_dir.name}")
            popup.transient(self)
            popup.attributes("-topmost", True)
            try:
                popup.geometry("+%d+%d" % (self.winfo_rootx() + 32, self.winfo_rooty() + 32))
            except Exception:
                pass
            frame = ttk.Frame(popup, padding=10)
            frame.pack(fill="both", expand=True)
            ttk.Label(
                frame,
                text=(
                    "Describe the 2D bug (the editor stays usable while this is open).\n"
                    "Save persists description.txt; Close keeps just the screenshot + state."
                ),
                justify="left",
            ).pack(anchor="w")
            entry = tk.Text(frame, height=4, width=60, wrap="word")
            entry.pack(fill="both", expand=True, pady=(8, 8))
            try:
                entry.focus_set()
            except Exception:
                pass
            buttons = ttk.Frame(frame)
            buttons.pack(fill="x")

            def _do_save(*_args) -> None:
                text = entry.get("1.0", "end").strip()
                if text:
                    try:
                        (bundle_dir / "description.txt").write_text(text + "\n", encoding="utf-8")
                    except Exception as exc:
                        self._bug_recorder_debug(f"2D flag description save failed: {exc}")
                    try:
                        if state_path.exists():
                            data = json.loads(state_path.read_text(encoding="utf-8"))
                            data["description"] = text
                            state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    except Exception as exc:
                        self._bug_recorder_debug(f"2D flag state update failed: {exc}")
                    self._set_bug_status(f"Flag description saved: {bundle_dir.name}")
                else:
                    self._set_bug_status(f"Flag kept without description: {bundle_dir.name}")
                try:
                    popup.destroy()
                except Exception:
                    pass

            def _do_close(*_args) -> None:
                self._set_bug_status(f"Flag kept without description: {bundle_dir.name}")
                try:
                    popup.destroy()
                except Exception:
                    pass

            ttk.Button(buttons, text="Save", command=_do_save).pack(side="right")
            ttk.Button(buttons, text="Close", command=_do_close).pack(side="right", padx=(0, 6))
            entry.bind("<Control-Return>", _do_save)
            popup.protocol("WM_DELETE_WINDOW", _do_close)
        except Exception as exc:
            self._bug_recorder_debug(f"2D flag description dialog failed: {exc}")
