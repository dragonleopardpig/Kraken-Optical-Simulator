"""The Tk window that edits one thickness, opened on a dimension in the 3D view (bugs/0978).

A small window: the row's label, one entry, OK. It is placed and grabbed by hand -- centred on the
screen so that it lands there under Wayland, and holding the input so that the 3D canvas cannot
take the focus while the user types (bugs/0053, which is what made it vanish). It lived inside
`services/open3d_thickness_dimensions.py`, which is why that service imported tkinter.

The service decides WHAT is edited and what the value does (`edit_dimension`: the prefill, the
shell's own prompt when another shell draws the inspector, `apply_dimension_value`). This module
only draws the Tk window and hands the typed value back.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import numpy as np


def position_inline_editor(service, window: tk.Toplevel) -> None:
    # Reuse the proven LED-import centering helper: withdraw -> set geometry
    # -> deiconify -> re-apply geometry after_idle + after(80ms). The re-apply
    # after the window is mapped is what makes it land on screen centre
    # reliably under Wayland / layer-shell (a one-shot geometry() is ignored).
    try:
        service.editor._show_centered_dialog(window)
        return
    except Exception:
        pass
    try:
        window.update_idletasks()
        width = max(int(window.winfo_reqwidth()), 260)
        height = max(int(window.winfo_reqheight()), 80)
        screen_w = max(int(window.winfo_screenwidth()), width)
        screen_h = max(int(window.winfo_screenheight()), height)
        x = max((screen_w - width) // 2, 0)
        y = max((screen_h - height) // 2, 0)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.deiconify()
        window.lift()
    except Exception:
        pass


def open_thickness_inline_editor(service, row_index: int, current: float) -> None:
    """Open the window on ``row_index`` prefilled with ``current``. Enter or OK applies the typed
    value through the service; Esc or closing the window cancels."""
    value_var = tk.StringVar(value=f"{current:.6g}")
    window = tk.Toplevel(service.inspector)
    service._inline_editor_window = window
    service._inline_editor_row_index = row_index
    try:
        window.withdraw()  # appear directly centred (no top-left flicker)
        window.title("Edit Thickness")
        window.transient(service.inspector)
        window.resizable(False, False)
    except Exception:
        pass
    frame = ttk.Frame(window, padding=8)
    frame.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(1, weight=1)
    ttk.Label(frame, text=service._row_label(row_index)).grid(row=0, column=0, columnspan=3, sticky="w")
    ttk.Label(frame, text="Thickness [mm]").grid(row=1, column=0, sticky="w", pady=(6, 0))
    entry = ttk.Entry(frame, textvariable=value_var, width=16)
    entry.grid(row=1, column=1, sticky="ew", padx=(8, 6), pady=(6, 0))

    def commit(_event=None):
        if service._inline_editor_committing:
            return "break"
        service._inline_editor_committing = True
        try:
            next_value = float(value_var.get())
        except Exception:
            service._inline_editor_committing = False
            service.inspector.status_var.set("Thickness must be a finite number.")
            try:
                entry.focus_set()
                entry.selection_range(0, "end")
            except Exception:
                pass
            return "break"
        if not np.isfinite(next_value):
            service._inline_editor_committing = False
            service.inspector.status_var.set("Thickness must be a finite number.")
            try:
                entry.focus_set()
                entry.selection_range(0, "end")
            except Exception:
                pass
            return "break"
        service._destroy_inline_editor()
        service.apply_dimension_value(row_index, next_value)
        return "break"

    def cancel(_event=None):
        service.cancel_inline_editor()
        return "break"

    def keep_focus_in_window(_event=None):
        # bugs/0053 #5: moving the mouse over the embedded VTK canvas used to
        # steal keyboard focus (focus-follows-mouse), which fired <FocusOut>
        # and committed/closed the editor mid-type -- "the window disappears if
        # the mouse moves a little." Don't commit on focus loss; pull focus
        # back to the entry so the user can keep typing. Committing is now
        # Enter / OK only (Esc / window-close cancels). If focus moved to a
        # child of this window (e.g. the OK button) leave it alone.
        try:
            if not window.winfo_exists():
                return None
            focus = window.focus_get()
            if focus is not None and focus.winfo_toplevel() is window:
                return None
            entry.focus_set()
        except Exception:
            pass
        return None

    ttk.Button(frame, text="OK", command=commit, width=6).grid(row=1, column=2, sticky="e", pady=(6, 0))
    window.bind("<Return>", commit, add="+")
    window.bind("<KP_Enter>", commit, add="+")
    window.bind("<Escape>", cancel, add="+")
    entry.bind("<FocusOut>", keep_focus_in_window, add="+")
    try:
        window.protocol("WM_DELETE_WINDOW", cancel)
    except Exception:
        pass
    position_inline_editor(service, window)
    # Grab input so the embedded VTK canvas can't take focus-follows-mouse
    # focus while the user is typing (the root cause of the vanishing editor).
    try:
        window.grab_set()
    except Exception:
        pass
    try:
        entry.focus_set()
        entry.selection_range(0, "end")
    except Exception:
        pass
    service.inspector.status_var.set(f"Editing {service._row_label(row_index)} Thickness. Press Enter to apply or Esc to cancel.")
