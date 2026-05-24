"""Optical CAD/STL utility dialogs."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Mapping

import numpy as np

from KrakenOS.UI.stl_geometry import (
    StlMeshDiagnostics,
    format_stl_mesh_diagnostics,
    inspect_stl_mesh,
    rotated_stl_bounds,
    short_stl_mesh_diagnostics,
)


class MainOpticalSolidDialogs:
    """Own optical CAD/STL diagnostics and numeric placement dialogs."""

    def __init__(
        self,
        editor: Any,
        *,
        short_error_message: Callable[[BaseException], str],
        axis_to_layout_z_tilts: Mapping[str, tuple[float, float, float]],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "short_error_message", short_error_message)
        object.__setattr__(self, "axis_to_layout_z_tilts", dict(axis_to_layout_z_tilts))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "short_error_message", "axis_to_layout_z_tilts"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _optical_stl_diagnostics_text(self) -> str:
        sections: list[str] = []
        for index, row in enumerate(self.rows):
            advanced = row.advanced or {}
            if not isinstance(advanced, dict) or not self._scene_graph_value_present(advanced.get("Solid_3d_stl")):
                continue
            header = f"S{index}: {row.name or row.surface}"
            path = self._stl_path_from_row(row)
            if path is None:
                sections.append(
                    "\n".join(
                        [
                            header,
                            "Status: CHECK",
                            "This row uses an in-memory/non-file Solid_3d_stl object. File topology diagnostics are unavailable.",
                        ]
                    )
                )
                continue
            report = inspect_stl_mesh(path)
            text = header + "\n" + format_stl_mesh_diagnostics(report)
            source_path = str(advanced.get("OpticalSolidSourcePath", "") or "").strip()
            if source_path:
                source_format = str(advanced.get("OpticalSolidSourceFormat", "") or "").strip()
                source_label = f" ({source_format})" if source_format else ""
                text += f"\n\nOriginal CAD source{source_label}: {source_path}"
            sections.append(text)
        if not sections:
            return ""
        return "\n\n".join(sections)

    def open_optical_stl_diagnostics(self) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror(
                "Inspect Optical CAD/STL Solids",
                f"Could not read the surface table:\n\n{exc}",
                parent=self.editor,
            )
            return
        report_text = self._optical_stl_diagnostics_text()
        if not report_text:
            messagebox.showinfo(
                "Inspect Optical CAD/STL Solids",
                "No rows contain Solid_3d_stl.",
                parent=self.editor,
            )
            return

        window = tk.Toplevel(self.editor)
        window.title("Optical CAD/STL Solid Diagnostics")
        window.geometry("920x620")
        window.minsize(720, 420)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        frame = ttk.Frame(window, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        text = tk.Text(frame, wrap="word", height=24, width=110)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        text.insert("1.0", report_text.strip() + "\n")
        text.configure(state="disabled")

        footer = ttk.Frame(frame)
        footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        def copy_report() -> None:
            ok, backend = self._copy_text_to_clipboard(report_text.strip() + "\n")
            if ok:
                self.status_var.set(f"Optical CAD/STL diagnostics copied to clipboard ({backend}).")
            else:
                self.status_var.set("Optical CAD/STL diagnostics written to Debug; clipboard unavailable.")
            self.append_debug(report_text.strip())

        ttk.Button(footer, text="Copy Report", command=copy_report).pack(side="left")
        ttk.Button(footer, text="Close", command=window.destroy).pack(side="right")
        self.append_debug(report_text.strip())

    def _open_optical_stl_numeric_placement_assistant(
        self,
        row_index: int,
        row: Any,
        path: Path,
        diagnostics: StlMeshDiagnostics,
    ) -> None:
        window = tk.Toplevel(self.editor)
        window.title(f"Place/Orient CAD/STL Solid - S{row_index}")
        window.geometry("760x520")
        window.minsize(680, 440)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        frame = ttk.Frame(window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(9, weight=1)

        summary = (
            f"S{row_index}: {row.name or row.surface}\n"
            f"{Path(diagnostics.path).name} | {short_stl_mesh_diagnostics(diagnostics)}\n"
            "Placement rule: choose the STL local axis that should point along layout +Z. "
            "The helper writes TiltX/Y/Z and optional DespX/Y/Z; the previous row Thickness controls the row Z station."
        )
        ttk.Label(frame, text=summary, justify="left", wraplength=700).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(frame, text="STL axis -> layout +Z").grid(row=1, column=0, sticky="w", pady=4)
        axis_var = tk.StringVar(value="+Z")
        axis_menu = ttk.Combobox(
            frame,
            textvariable=axis_var,
            state="readonly",
            values=tuple(self.axis_to_layout_z_tilts.keys()),
            width=12,
        )
        axis_menu.grid(row=1, column=1, sticky="w", pady=4)

        center_xy_var = tk.BooleanVar(value=True)
        front_z_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Center rotated STL X/Y on layout axis", variable=center_xy_var).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(8, 2)
        )
        ttk.Checkbutton(frame, text="Place rotated STL minimum Z on this row plane", variable=front_z_var).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=2
        )

        ttk.Label(frame, text="Extra X [mm]").grid(row=4, column=0, sticky="w", pady=(10, 2))
        extra_x_var = tk.StringVar(value="0.0")
        extra_x_entry = ttk.Entry(frame, textvariable=extra_x_var, width=12)
        extra_x_entry.grid(row=4, column=1, sticky="w", pady=(10, 2))

        ttk.Label(frame, text="Extra Y [mm]").grid(row=5, column=0, sticky="w", pady=2)
        extra_y_var = tk.StringVar(value="0.0")
        extra_y_entry = ttk.Entry(frame, textvariable=extra_y_var, width=12)
        extra_y_entry.grid(row=5, column=1, sticky="w", pady=2)

        ttk.Label(frame, text="Extra Z [mm]").grid(row=6, column=0, sticky="w", pady=2)
        extra_z_var = tk.StringVar(value="0.0")
        extra_z_entry = ttk.Entry(frame, textvariable=extra_z_var, width=12)
        extra_z_entry.grid(row=6, column=1, sticky="w", pady=2)

        result_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=result_var, justify="left", wraplength=700).grid(
            row=7, column=0, columnspan=3, sticky="ew", pady=(10, 6)
        )

        text = tk.Text(frame, wrap="word", height=8, width=86)
        text.grid(row=9, column=0, columnspan=3, sticky="nsew", pady=(8, 0))

        def computed_pose() -> tuple[tuple[float, float, float], tuple[float, float, float], str]:
            axis = axis_var.get().strip()
            tilts = self.axis_to_layout_z_tilts.get(axis, self.axis_to_layout_z_tilts["+Z"])
            bounds_min, bounds_max, center = rotated_stl_bounds(path, tilts)
            try:
                extra_x = float(extra_x_var.get().strip() or "0.0")
                extra_y = float(extra_y_var.get().strip() or "0.0")
                extra_z = float(extra_z_var.get().strip() or "0.0")
            except Exception as exc:
                raise ValueError(f"Extra offsets must be numeric: {exc}") from exc
            desp_x = (-float(center[0]) if center_xy_var.get() else float(row.desp_x)) + extra_x
            desp_y = (-float(center[1]) if center_xy_var.get() else float(row.desp_y)) + extra_y
            desp_z = (-float(bounds_min[2]) if front_z_var.get() else float(row.desp_z)) + extra_z
            summary_text = (
                "Rotated bounds [mm]\n"
                "  min=({:.6g}, {:.6g}, {:.6g})\n"
                "  max=({:.6g}, {:.6g}, {:.6g})\n"
                "New row pose\n"
                "  TiltX={:.6g}, TiltY={:.6g}, TiltZ={:.6g}\n"
                "  DespX={:.6g}, DespY={:.6g}, DespZ={:.6g}".format(
                    *bounds_min,
                    *bounds_max,
                    tilts[0],
                    tilts[1],
                    tilts[2],
                    desp_x,
                    desp_y,
                    desp_z,
                )
            )
            return tilts, (desp_x, desp_y, desp_z), summary_text

        def refresh_preview(*_args) -> None:
            try:
                _tilts, _desp, summary_text = computed_pose()
                result_var.set("Computed pose is ready. Apply writes table values; click Update to trace.")
                text.configure(state="normal")
                text.delete("1.0", "end")
                text.insert("1.0", summary_text + "\n")
                text.configure(state="disabled")
            except Exception as exc:
                result_var.set(f"Placement preview failed: {self.short_error_message(exc)}")

        def apply_pose() -> None:
            try:
                tilts, desp, summary_text = computed_pose()
            except Exception as exc:
                messagebox.showerror("Place/Orient Selected CAD/STL Solid", str(exc), parent=window)
                return
            self._begin_history_capture()
            target = self.rows[row_index]
            target.tilt_x, target.tilt_y, target.tilt_z = (float(value) for value in tilts)
            target.desp_x, target.desp_y, target.desp_z = (float(value) for value in desp)
            self._sync_table()
            self._select_table_row(row_index)
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Placed/oriented STL solid S{row_index}. Click Update to trace.")
            self.append_debug(f"CAD/STL placement S{row_index}:\n{summary_text}")
            window.destroy()

        for var in (axis_var, center_xy_var, front_z_var, extra_x_var, extra_y_var, extra_z_var):
            try:
                var.trace_add("write", refresh_preview)
            except Exception:
                pass

        footer = ttk.Frame(frame)
        footer.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(footer, text="Apply Pose", command=apply_pose).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        refresh_preview()
