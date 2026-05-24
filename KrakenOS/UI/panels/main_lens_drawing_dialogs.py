"""Lens drawing surface-property and PDF export dialogs."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any
import webbrowser

import numpy as np

from KrakenOS.UI.lens_drawing_export import export_lens_drawing, identify_elements
from KrakenOS.UI.lens_drawing_properties import (
    DRAWING_PROPERTIES_ATTR as DRAWING_PROPERTIES_ADVANCED_ATTR,
    DRAWING_PROPERTY_FIELDS,
    apply_surface_properties_payload,
    drawing_properties,
    format_property_value,
    normalize_drawing_properties,
    surface_properties_payload,
    validate_drawing_properties,
)
from KrakenOS.UI.surface_table_model import SurfaceRow
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
        groups, _info = identify_elements(self.rows)
        if not groups:
            messagebox.showinfo("Lens Drawing Properties", "No lens elements found in the surface table.", parent=self.editor)
            return False

        surface_indices: list[int] = []
        for group in groups:
            for element in group.elements:
                for index in (getattr(element, "left_row_index", -1), getattr(element, "right_row_index", -1)):
                    if 0 <= index < len(self.rows) and index not in surface_indices:
                        surface_indices.append(index)
        if not surface_indices:
            return True

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Lens Drawing Surface Properties")
        window.geometry("1360x700")
        window.minsize(980, 520)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            header,
            text=(
                "Enter ISO-style fabrication drawing properties for each optical surface. Blank fields keep drawing "
                "placeholders. Values are saved in each row's DrawingProperties advanced metadata and can also be "
                "saved/loaded as an editable JSON sidecar before PDF export."
            ),
            wraplength=1080,
            justify="left",
        ).pack(side="left", fill="x", expand=True)

        canvas = tk.Canvas(window, highlightthickness=0)
        scroll_y = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
        scroll_x = ttk.Scrollbar(window, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        canvas.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=6)
        scroll_y.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=6)
        scroll_x.grid(row=2, column=0, sticky="ew", padx=(10, 0), pady=(0, 6))

        frame = ttk.Frame(canvas, padding=(0, 0, 8, 0))
        for column in range(0, 7 + len(DRAWING_PROPERTY_FIELDS)):
            frame.columnconfigure(column, weight=0)
        canvas_window = canvas.create_window((0, 0), window=frame, anchor="nw")

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

        headings = ["Surface", "Name", "Type", "Material", "Rc", "Dia", "CT"]
        headings.extend(field.label for field in DRAWING_PROPERTY_FIELDS)
        for column, heading in enumerate(headings):
            ttk.Label(frame, text=heading, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=column, sticky="w", padx=4, pady=(0, 6))

        entries: dict[int, dict[str, ttk.Entry]] = {}
        for grid_row, row_index in enumerate(surface_indices, start=1):
            row = self.rows[row_index]
            props = drawing_properties(row)
            ttk.Label(frame, text=f"S{row_index}").grid(row=grid_row, column=0, sticky="w", padx=4, pady=3)
            ttk.Label(frame, text=str(row.name or row.surface)).grid(row=grid_row, column=1, sticky="w", padx=4, pady=3)
            ttk.Label(frame, text=str(row.surface)).grid(row=grid_row, column=2, sticky="w", padx=4, pady=3)
            ttk.Label(frame, text=str(row.glass)).grid(row=grid_row, column=3, sticky="w", padx=4, pady=3)
            ttk.Label(frame, text=self._format_table_float(float(row.rc))).grid(row=grid_row, column=4, sticky="w", padx=4, pady=3)
            ttk.Label(frame, text=self._format_table_float(float(row.diameter))).grid(row=grid_row, column=5, sticky="w", padx=4, pady=3)
            ttk.Label(frame, text=self._format_table_float(float(row.thickness))).grid(row=grid_row, column=6, sticky="w", padx=4, pady=3)
            row_entries: dict[str, ttk.Entry] = {}
            for offset, field in enumerate(DRAWING_PROPERTY_FIELDS, start=7):
                value_frame = ttk.Frame(frame)
                value_frame.grid(row=grid_row, column=offset, sticky="new", padx=4, pady=3)
                value_frame.columnconfigure(0, weight=1)
                entry = ttk.Entry(value_frame, width=field.width)
                value = props.get(field.key, "")
                entry.insert(0, format_property_value(value))
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

        status_var = tk.StringVar(master=window, value="Blank fields are allowed and become drawing placeholders.")
        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Label(footer, textvariable=status_var, foreground="#5f6b7a").pack(side="left", fill="x", expand=True)

        result = {"ok": False}

        def collect_updates() -> dict[int, dict[str, object]]:
            updates: dict[int, dict[str, object]] = {}
            for row_index, row_entries in entries.items():
                raw_props: dict[str, object] = {}
                for field_key, entry in row_entries.items():
                    text = entry.get().strip()
                    if text:
                        raw_props[field_key] = text
                props = normalize_drawing_properties(raw_props)
                errors = validate_drawing_properties(props)
                if errors:
                    raise ValueError(f"S{row_index}: " + " ".join(errors))
                updates[row_index] = props
            return updates

        def apply_updates(updates: dict[int, dict[str, object]], *, close: bool) -> None:
            self._begin_history_capture()
            for row_index, props in updates.items():
                row = self.rows[row_index]
                row.advanced = dict(row.advanced or {})
                if props:
                    row.advanced[DRAWING_PROPERTIES_ADVANCED_ATTR] = props
                else:
                    row.advanced.pop(DRAWING_PROPERTIES_ADVANCED_ATTR, None)
            self._sync_table()
            self._commit_history_capture()
            result["ok"] = True
            if close:
                window.destroy()
            else:
                status_var.set("Applied drawing properties to the surface table.")

        def apply_and_continue() -> None:
            try:
                apply_updates(collect_updates(), close=True)
            except Exception as exc:
                status_var.set(str(exc))
                messagebox.showerror("Lens Drawing Properties", str(exc), parent=window)

        def continue_without_changes() -> None:
            result["ok"] = True
            window.destroy()

        def apply_only() -> None:
            try:
                apply_updates(collect_updates(), close=False)
            except Exception as exc:
                status_var.set(str(exc))
                messagebox.showerror("Lens Drawing Properties", str(exc), parent=window)

        def clear_all() -> None:
            for row_entries in entries.values():
                for entry in row_entries.values():
                    entry.delete(0, tk.END)
            status_var.set("Cleared dialog fields. Click Apply to remove saved DrawingProperties.")

        def save_json() -> None:
            try:
                updates = collect_updates()
            except Exception as exc:
                status_var.set(str(exc))
                messagebox.showerror("Lens Drawing Properties", str(exc), parent=window)
                return
            payload = surface_properties_payload(self.rows, surface_indices)
            for record in payload.get("surfaces", []):
                if not isinstance(record, dict):
                    continue
                row_index = int(record.get("surface_index", -1))
                record["properties"] = updates.get(row_index, {})
            path = filedialog.asksaveasfilename(
                title="Save Lens Drawing Surface Properties",
                initialdir=str(self.screenshot_dir),
                initialfile="lens_drawing_properties.json",
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("All files", "*")],
                parent=window,
            )
            if not path:
                return
            try:
                Path(path).write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
            except Exception as exc:
                status_var.set(str(exc))
                messagebox.showerror("Lens Drawing Properties", f"Could not save JSON:\n\n{exc}", parent=window)
                return
            status_var.set(f"Saved editable surface properties: {Path(path).name}")

        def load_json() -> None:
            path = filedialog.askopenfilename(
                title="Load Lens Drawing Surface Properties",
                initialdir=str(self.screenshot_dir),
                filetypes=[("JSON", "*.json"), ("All files", "*")],
                parent=window,
            )
            if not path:
                return
            try:
                payload = json.loads(Path(path).read_text(encoding="utf-8"))
                temp_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
                apply_surface_properties_payload(temp_rows, payload)
            except Exception as exc:
                status_var.set(str(exc))
                messagebox.showerror("Lens Drawing Properties", f"Could not load JSON:\n\n{exc}", parent=window)
                return
            loaded = 0
            for row_index, row_entries in entries.items():
                props = drawing_properties(temp_rows[row_index])
                for field_key, entry in row_entries.items():
                    entry.delete(0, tk.END)
                    entry.insert(0, format_property_value(props.get(field_key, "")))
                loaded += 1
            status_var.set(f"Loaded editable surface properties from {Path(path).name}; click Apply to save them in the layout.")

        ttk.Button(footer, text="Load JSON...", command=load_json).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Save JSON...", command=save_json).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Clear", command=clear_all).pack(side="right", padx=(0, 8))
        if for_export:
            ttk.Button(footer, text="Continue Without Changes", command=continue_without_changes).pack(side="right", padx=(0, 8))
            ttk.Button(footer, text="Apply && Continue", command=apply_and_continue).pack(side="right", padx=(0, 8))
            ttk.Button(footer, text="Cancel Export", command=window.destroy).pack(side="right", padx=(0, 8))
        else:
            ttk.Button(footer, text="Apply && Close", command=apply_and_continue).pack(side="right", padx=(0, 8))
            ttk.Button(footer, text="Apply", command=apply_only).pack(side="right", padx=(0, 8))
            ttk.Button(footer, text="Close", command=continue_without_changes).pack(side="right", padx=(0, 8))

        self._show_centered_dialog(window)
        self.wait_window(window)
        return bool(result["ok"])

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
        path = filedialog.asksaveasfilename(
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
            messagebox.showwarning("Export", str(exc), parent=self.editor)
        except Exception as exc:
            messagebox.showerror("Export Error",
                                 f"Failed to export lens drawing:\n{exc}",
                                 parent=self.editor)
