"""Lens drawing surface-property and PDF export dialogs."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Any
import webbrowser

import numpy as np

from KrakenOS.UI.lens_drawing_export import export_lens_drawing
from KrakenOS.UI.lens_drawing_session import (FIXED_COLUMNS, MESSAGE_TITLE, NO_LENSES, NOTE, TITLE,
                                              LensDrawingPropertiesSession, has_lens_elements)
from KrakenOS.UI.uihost import host_of
from KrakenOS.UI.widgets.tooltips import WidgetTooltip


class MainLensDrawingDialogs:
    """Own lens fabrication drawing dialogs while delegating row state to the editor."""

    def __init__(self, editor: Any, *, screenshot_dir: Path) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "screenshot_dir", Path(screenshot_dir))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "screenshot_dir"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _open_lens_drawing_surface_properties_dialog(self, *, for_export: bool = False) -> bool:
        """The surface-properties dialog; True when the caller may go on (bugs/0945: the state and
        actions are `lens_drawing_session`, shown by the Qt shell's dialog or by Tk's window)."""
        if not has_lens_elements(self.rows):
            host_of(self).showinfo(MESSAGE_TITLE, NO_LENSES, parent=self.editor)
            return False
        session = LensDrawingPropertiesSession(self, for_export=for_export, screenshot_dir=self.screenshot_dir)
        if not session.surface_indices:
            return True
        shell = self.editor.__dict__.get("show_lens_drawing_properties")
        if callable(shell):
            shell(session)          # modal: returns once the session is closed
        else:
            self._show_tk_lens_drawing_properties(session)
        return bool(session.result_ok)

    def _show_tk_lens_drawing_properties(self, session: LensDrawingPropertiesSession) -> None:
        """The Tk window over `session`, laid out as it always was; waits until it closes."""
        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(TITLE)
        window.geometry("1360x700")
        window.minsize(980, 520)
        window.transient(self.editor)
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

        self._show_centered_dialog(window)
        self.wait_window(window)
        if sync in session.listeners:
            session.listeners.remove(sync)

    def export_lens_drawing(self) -> None:
        """Export an ISO 10110-style lens fabrication drawing as PDF."""
        self._commit_pending_table_edit()
        self._read_rows_from_table()
        if not self._open_lens_drawing_surface_properties_dialog(for_export=True):
            self.status_var.set("Lens drawing export cancelled.")
            return
        # Determine default filename from current layout
        stem = "lens_drawing"
        if self.current_layout_file:
            stem = self.current_layout_file.stem + "_drawing"
        try:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        # asks and reports through the UI host, so the Qt shell exports too (bugs/0945)
        path = host_of(self).asksaveasfilename(
            title="Export Lens Drawing (PDF)",
            initialdir=str(self.screenshot_dir),
            initialfile=f"{stem}.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            parent=self.editor,
        )
        if not path:
            return
        try:
            # Gather EFL/BFL from paraxial cardinals if computable
            efl = None
            bfl = None
            try:
                effl_val, ppa_val, ppp_val = self._exact_paraxial_cardinals()
                if np.isfinite(effl_val):
                    efl = float(effl_val)
                    # BFL = distance from last optical surface to rear focal point
                    # Approximate: effl + ppp (principal plane offset from last surface)
                    bfl_val = effl_val + ppp_val
                    if np.isfinite(bfl_val):
                        bfl = float(bfl_val)
            except Exception:
                pass
            title = ""
            if self.current_layout_file:
                title = self.current_layout_file.stem.replace("_", " ").title()
            elif hasattr(self, "layout_var"):
                sel = self.layout_var.get()
                if sel and sel != "Common Optical Layout":
                    title = sel
            if not title:
                title = "Lens Drawing"
            export_lens_drawing(
                self.rows, path, title=title,
                dwg_no=stem.upper(),
                efl=efl, bfl=bfl,
            )
            self.status_var.set(f"Lens drawing exported: {Path(path).name}")
            # Open the PDF
            webbrowser.open(str(Path(path).resolve()))
        except ValueError as exc:
            host_of(self).showwarning("Export", str(exc), parent=self.editor)
        except Exception as exc:
            host_of(self).showerror("Export Error",
                                    f"Failed to export lens drawing:\n{exc}",
                                    parent=self.editor)
