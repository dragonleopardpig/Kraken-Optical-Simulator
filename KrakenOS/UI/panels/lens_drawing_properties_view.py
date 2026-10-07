"""The Tk window over a lens-drawing properties session (bugs/0945).

What the dialog holds and does is `lens_drawing_session`; this is only how Tk lays it out -- one
row of entries per lens surface, the session's buttons, its status line. A module of its own since
bugs/0986: it was a method of `panels/main_lens_drawing_dialogs.py`, so the panel -- which also
shows the session in another shell's dialog and exports the PDF -- loaded tkinter with it, and
through the panel `services/layout_import_export.py` did. The panel imports this when Tk draws.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from KrakenOS.UI.lens_drawing_session import FIXED_COLUMNS, NOTE, TITLE, LensDrawingPropertiesSession
from KrakenOS.UI.widgets.tooltips import WidgetTooltip


def show_tk_lens_drawing_properties(panel: Any, session: LensDrawingPropertiesSession) -> None:
    """The Tk window over `session`, laid out as it always was; waits until it closes.

    `panel` is the lens-drawing panel, which forwards to the editor: the window's parent, the
    centring and the wait are the editor's.
    """
    window = tk.Toplevel(panel.editor)
    window.withdraw()
    window.title(TITLE)
    window.geometry("1360x700")
    window.minsize(980, 520)
    window.transient(panel.editor)
    window.columnconfigure(0, weight=1)
    window.rowconfigure(1, weight=1)

    header = ttk.Frame(window, padding=(10, 10, 10, 4))
    header.grid(row=0, column=0, sticky="ew")
    ttk.Label(header, text=NOTE, wraplength=1080, justify="left").pack(side="left", fill="x", expand=True)

    canvas = tk.Canvas(window, highlightthickness=0)
    scroll_y = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
    scroll_x = ttk.Scrollbar(window, orient="horizontal", command=canvas.xview)
    canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
    canvas.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=6)
    scroll_y.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=6)
    scroll_x.grid(row=2, column=0, sticky="ew", padx=(10, 0), pady=(0, 6))

    fields = session.fields()
    frame = ttk.Frame(canvas, padding=(0, 0, 8, 0))
    for column in range(0, len(FIXED_COLUMNS) + len(fields)):
        frame.columnconfigure(column, weight=0)
    canvas.create_window((0, 0), window=frame, anchor="nw")

    def _sync_canvas(_event=None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame.bind("<Configure>", _sync_canvas, add="+")
    canvas.bind("<Configure>", _sync_canvas, add="+")

    def _wheel(event) -> str:
        delta = int(getattr(event, "delta", 0))
        if delta:
            canvas.yview_scroll(-1 if delta > 0 else 1, "units")
        return "break"

    def _shift_wheel(event) -> str:
        delta = int(getattr(event, "delta", 0))
        if delta:
            canvas.xview_scroll(-1 if delta > 0 else 1, "units")
        return "break"

    canvas.bind("<MouseWheel>", _wheel, add="+")
    canvas.bind("<Shift-MouseWheel>", _shift_wheel, add="+")

    for column, heading in enumerate(session.headings()):
        ttk.Label(frame, text=heading, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=column, sticky="w", padx=4, pady=(0, 6))

    entries: dict[int, dict[str, ttk.Entry]] = {}
    for grid_row, row_index in enumerate(session.surface_indices, start=1):
        for column, text in enumerate(session.fixed_cells(row_index)):
            ttk.Label(frame, text=text).grid(row=grid_row, column=column, sticky="w", padx=4, pady=3)
        row_entries: dict[str, ttk.Entry] = {}
        for offset, field in enumerate(fields, start=len(FIXED_COLUMNS)):
            value_frame = ttk.Frame(frame)
            value_frame.grid(row=grid_row, column=offset, sticky="new", padx=4, pady=3)
            value_frame.columnconfigure(0, weight=1)
            entry = ttk.Entry(value_frame, width=field.width)
            entry.insert(0, session.values[row_index][field.key])
            entry.grid(row=0, column=0, sticky="ew")
            if field.hint:
                ttk.Label(
                    value_frame,
                    text=field.hint,
                    foreground="#6b7280",
                    wraplength=max(120, field.width * 8),
                    justify="left",
                ).grid(row=1, column=0, sticky="w", pady=(2, 0))
            if field.help:
                WidgetTooltip(entry, field.help)
            row_entries[field.key] = entry
        entries[row_index] = row_entries

    status_var = tk.StringVar(master=window, value=session.status)
    footer = ttk.Frame(window, padding=(10, 0, 10, 10))
    footer.grid(row=3, column=0, columnspan=2, sticky="ew")
    ttk.Label(footer, textvariable=status_var, foreground="#5f6b7a").pack(side="left", fill="x", expand=True)

    def push() -> None:
        for row_index, row_entries in entries.items():
            for key, entry in row_entries.items():
                session.set_value(row_index, key, entry.get())

    def sync() -> None:
        for row_index, row_entries in entries.items():
            for key, entry in row_entries.items():
                value = session.values[row_index][key]
                if entry.get() != value:
                    entry.delete(0, tk.END)
                    entry.insert(0, value)
        status_var.set(session.status)
        if session.closed and window.winfo_exists():
            window.destroy()

    def run(method: str) -> None:
        push()
        getattr(session, method)(parent=window)

    session.listeners.append(sync)
    for label, method in session.buttons():
        ttk.Button(footer, text=label, command=lambda m=method: run(m)).pack(side="right", padx=(0, 8))

    panel._show_centered_dialog(window)
    panel.wait_window(window)
    if sync in session.listeners:
        session.listeners.remove(sync)
