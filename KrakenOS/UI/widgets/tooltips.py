"""Small reusable Tk tooltip widget."""

from __future__ import annotations

import tkinter as tk


class WidgetTooltip:
    """Small Tk tooltip for compact toolbar controls."""

    def __init__(self, widget: tk.Widget, text: str, *, delay_ms: int = 650, wraplength: int = 360) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.wraplength = wraplength
        self._show_after_id: str | None = None
        self._hide_after_id: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._schedule_hide, add="+")
        widget.bind("<ButtonPress>", self._hide_now, add="+")
        widget.bind("<Destroy>", self._hide_now, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel_hide()
        if self._window is not None:
            return
        self._cancel_show()
        self._show_after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel_show(self) -> None:
        if self._show_after_id is None:
            return
        try:
            self.widget.after_cancel(self._show_after_id)
        except Exception:
            pass
        self._show_after_id = None

    def _cancel_hide(self) -> None:
        if self._hide_after_id is None:
            return
        try:
            self.widget.after_cancel(self._hide_after_id)
        except Exception:
            pass
        self._hide_after_id = None

    def _show(self) -> None:
        self._show_after_id = None
        if self._window is not None or not self.text:
            return
        try:
            pointer_x, pointer_y = self.widget.winfo_pointerxy()
        except Exception:
            return
        window = tk.Toplevel(self.widget)
        window.withdraw()
        window.wm_overrideredirect(True)
        try:
            window.wm_attributes("-type", "tooltip")
        except Exception:
            pass
        label = tk.Label(
            window,
            text=self.text,
            justify="left",
            wraplength=self.wraplength,
            background="#111827",
            foreground="#f8fafc",
            borderwidth=1,
            relief="solid",
            padx=8,
            pady=5,
        )
        label.pack()
        window.update_idletasks()
        try:
            screen_width = self.widget.winfo_screenwidth()
            screen_height = self.widget.winfo_screenheight()
            width = window.winfo_width()
            height = window.winfo_height()
            x = pointer_x + 14
            y = pointer_y + 20
            x = min(max(0, x), max(0, screen_width - width - 8))
            if y + height > screen_height - 8:
                y = pointer_y - height - 12
            y = min(max(0, y), max(0, screen_height - height - 8))
        except Exception:
            x = pointer_x + 14
            y = pointer_y + 20
        window.wm_geometry(f"+{x}+{y}")
        self._window = window
        try:
            window.deiconify()
        except Exception:
            pass

    def _schedule_hide(self, _event=None) -> None:
        self._cancel_show()
        self._cancel_hide()
        self._hide_after_id = self.widget.after(120, self._hide_if_pointer_outside)

    def _hide_if_pointer_outside(self) -> None:
        self._hide_after_id = None
        if self._pointer_inside_widget_or_tip():
            return
        self._hide_now()

    def _pointer_inside_widget_or_tip(self) -> bool:
        try:
            pointer_x, pointer_y = self.widget.winfo_pointerxy()
        except Exception:
            return False
        widgets = [self.widget]
        if self._window is not None:
            widgets.append(self._window)
        for widget in widgets:
            try:
                x0 = widget.winfo_rootx()
                y0 = widget.winfo_rooty()
                x1 = x0 + widget.winfo_width()
                y1 = y0 + widget.winfo_height()
            except Exception:
                continue
            if x0 <= pointer_x <= x1 and y0 <= pointer_y <= y1:
                return True
        return False

    def _hide_now(self, _event=None) -> None:
        self._cancel_show()
        self._cancel_hide()
        if self._window is None:
            return
        try:
            self._window.destroy()
        except Exception:
            pass
        self._window = None
