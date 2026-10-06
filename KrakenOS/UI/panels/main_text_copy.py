"""The Tk view of "copy this text" (bugs/0976).

The copy shortcuts and the right-click menu on the main window's text boxes (the debug log, the
progress log, a report's detail text), and the window-wide Ctrl+C / Ctrl+V that follow the focus.
Until bugs/0976 these lived in `services/analysis_compute_workflow.py`, which is why that service
imported tkinter. What a text box has selected is the view's to know; copying it to the system
clipboard and saying so on the status line is the model's (`copy_selected_text`, `copy_all_text`),
and the Qt shell's text panels can ask for the same.
"""
from __future__ import annotations

import tkinter as tk
from typing import Any


class MainTextCopy:
    """Bind copy and paste on the main window's Tk widgets while delegating state."""

    COPY_SEQUENCES = ("<Control-c>", "<Control-C>", "<Control-Insert>", "<<Copy>>", "<Control-KeyPress-c>", "<Control-KeyPress-C>")

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _bind_text_copy_shortcuts(self, widget: tk.Text) -> None:
        for sequence in self.COPY_SEQUENCES:
            widget.bind(sequence, lambda _e, w=widget: self._copy_selection_from_text_widget(w), add="+")

    def _bind_text_context_menu(self, widget: tk.Text) -> None:
        widget.bind("<Button-3>", lambda e, w=widget: self._show_text_context_menu(e, w), add="+")

    def _bind_global_copy_shortcuts(self) -> None:
        for sequence in ("<Control-c>", "<Control-C>", "<Control-Insert>"):
            self.bind_all(sequence, self._copy_selection_from_focus, add="+")
        for sequence in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
            self.bind_all(sequence, self._paste_rows_from_focus, add="+")

    def _show_text_context_menu(self, event, widget: tk.Text):
        if self._text_popup_menu is None:
            menu = tk.Menu(self.editor, tearoff=0)
            menu.add_command(label="Copy Selected", command=lambda: self._copy_selection_from_text_widget(widget))
            menu.add_command(label="Copy All", command=lambda: self._copy_all_from_text_widget(widget))
            self._text_popup_menu = menu
        else:
            self._text_popup_menu.entryconfigure(0, command=lambda: self._copy_selection_from_text_widget(widget))
            self._text_popup_menu.entryconfigure(1, command=lambda: self._copy_all_from_text_widget(widget))
        self._text_popup_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _safe_focus_get(self):
        # a transient dialog's widget can be the focus and already be gone from Tk's name table
        try:
            return self.focus_get()
        except (KeyError, tk.TclError):
            return None

    @staticmethod
    def _selected_text(widget: tk.Text) -> str:
        """What the text box has selected; "" when nothing is."""
        try:
            return widget.get("sel.first", "sel.last")
        except tk.TclError:
            return ""

    def _copy_selection_from_focus(self, _event=None):
        candidates = []
        focused = self._safe_focus_get()
        if focused is getattr(self, "table", None):
            return self.copy_selected_rows_to_clipboard(_event)
        if isinstance(focused, tk.Text):
            candidates.append(focused)
        for widget in (getattr(self, "debug_text", None), getattr(self, "progress_text", None)):
            if isinstance(widget, tk.Text) and widget not in candidates:
                candidates.append(widget)
        for widget in candidates:
            text = self._selected_text(widget)
            if not text:
                continue
            self.copy_selected_text(text)
            return "break"
        return None

    def _paste_rows_from_focus(self, _event=None):
        focused = self._safe_focus_get()
        if focused is getattr(self, "table", None):
            return self.paste_rows_from_clipboard(_event)
        return None

    def _copy_selection_from_text_widget(self, widget: tk.Text) -> str:
        self.copy_selected_text(self._selected_text(widget))
        return "break"

    def _copy_all_from_text_widget(self, widget: tk.Text) -> str:
        self.copy_all_text(widget.get("1.0", "end-1c"))
        return "break"
