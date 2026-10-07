"""Tk helpers of the main window: dismissing the table's popup menu, centring a dialog (bugs/0981).

Four small pieces of Tk that lived in `services/paraxial_tools.py`, the last service to import
tkinter for view code:

- a click elsewhere, or Escape, dismisses the popup menu the surface table posted -- unless the
  click is on the menu itself;
- a dialog centred over the main window, or on the screen (re-applied once the window is mapped,
  which is what makes it land under Wayland).

WHAT is cleaned up when a popup menu goes (`_cleanup_current_popup_menu`) stays in the service.
"""
from __future__ import annotations

import tkinter as tk
from typing import Any


class MainPopupHelpers:
    """Popup-menu dismissal and dialog centring for the Tk main window, delegating state."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    @staticmethod
    def _event_inside_widget_root_bounds(event: tk.Event, widget: tk.Widget) -> bool:
        try:
            x_root = int(event.x_root)
            y_root = int(event.y_root)
            widget.update_idletasks()
            widget_x = int(widget.winfo_rootx())
            widget_y = int(widget.winfo_rooty())
            widget_w = max(int(widget.winfo_width()), 1)
            widget_h = max(int(widget.winfo_height()), 1)
        except Exception:
            return False
        return widget_x <= x_root < widget_x + widget_w and widget_y <= y_root < widget_y + widget_h

    def _dismiss_popup_menu_event(self, event: tk.Event | None = None) -> None:
        if self.popup_menu is None:
            return
        if event is not None:
            widget = getattr(event, "widget", None)
            if isinstance(widget, tk.Menu) and self._event_inside_widget_root_bounds(event, widget):
                return
        self._cleanup_current_popup_menu()

    def _center_dialog_over_main_window(self, dialog: tk.Toplevel) -> None:
        dialog.update_idletasks()
        parent_x = self.winfo_rootx()
        parent_y = self.winfo_rooty()
        parent_w = max(self.winfo_width(), 1)
        parent_h = max(self.winfo_height(), 1)
        dialog_w = max(dialog.winfo_width(), 1)
        dialog_h = max(dialog.winfo_height(), 1)
        pos_x = parent_x + max((parent_w - dialog_w) // 2, 0)
        pos_y = parent_y + max((parent_h - dialog_h) // 2, 0)
        dialog.geometry(f"+{pos_x}+{pos_y}")

    @staticmethod
    def _center_dialog_on_screen(dialog: tk.Toplevel) -> None:
        def place_dialog() -> None:
            if not dialog.winfo_exists():
                return
            dialog.update_idletasks()
            dialog_w = max(dialog.winfo_width(), dialog.winfo_reqwidth(), 1)
            dialog_h = max(dialog.winfo_height(), dialog.winfo_reqheight(), 1)
            screen_w = max(dialog.winfo_screenwidth(), 1)
            screen_h = max(dialog.winfo_screenheight(), 1)
            pos_x = max((screen_w - dialog_w) // 2, 0)
            pos_y = max((screen_h - dialog_h) // 2, 0)
            dialog.geometry(f"+{pos_x}+{pos_y}")

        place_dialog()
        dialog.after_idle(place_dialog)
        dialog.after(80, place_dialog)
