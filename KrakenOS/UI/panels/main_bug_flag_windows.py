"""The Tk editor's own windows around a 2D bug flag (bugs/0979).

Two pieces of Tk that lived in `services/layout_bug_recorder.py`, which is why that service
imported tkinter:

- the scan of the Tk windows that are open when a flag is taken -- each one's geometry, and whether
  it spills past the screen (the oversized-dialog class of bug, in numbers);
- the small window that asks for the flag's description without taking the editor away.

What a flag captures and what Save and Close DO stay in the service (`flag_bug_2d`,
`_save_2d_flag_description`, `_keep_2d_flag_without_description`). The Qt shell flags its whole
window itself (bugs/0959) and never opens this.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any


class MainBugFlagWindows:
    """The 2D flag's Tk windows, delegating state to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

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
            _visit(self.editor)          # the panel is not a widget
        except Exception:
            pass
        return found

    def _open_2d_flag_description_dialog(self, *, bundle_dir: Path, state_path: Path) -> None:
        """Non-modal description prompt; Save writes the text into the bundle."""
        try:
            popup = tk.Toplevel(self.editor)      # the panel is not a widget (bugs/0955)
            popup.title(f"Flag: {bundle_dir.name}")
            popup.transient(self.editor)
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
                self._save_2d_flag_description(bundle_dir, state_path, entry.get("1.0", "end"))
                try:
                    popup.destroy()
                except Exception:
                    pass

            def _do_close(*_args) -> None:
                self._keep_2d_flag_without_description(bundle_dir)
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
