"""Tolerance report actions and preset dialogs."""

from __future__ import annotations

import csv
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import traceback
from typing import Any


class MainToleranceReportDialogs:
    """Own tolerance report dialogs/exports while delegating tolerance calculations to the editor."""

    def __init__(self, editor: Any, *, tolerance_compare_view_values: tuple[str, ...]) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "tolerance_compare_view_values", tolerance_compare_view_values)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"editor", "tolerance_compare_view_values"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_tolerance_monte_carlo_report(self) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Tolerance Monte Carlo", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return
        preset = self._active_tolerance_solve_preset()
        sample_count = simpledialog.askinteger(
            "Tolerance Monte Carlo",
            "Monte Carlo sample count",
            initialvalue=self._tolerance_preset_int(preset.get("sample_count", 25), 25, 1, 1000),
            minvalue=1,
            maxvalue=1000,
            parent=self.editor,
        )
        if sample_count is None:
            return
        seed = simpledialog.askinteger(
            "Tolerance Monte Carlo",
            "Random seed",
            initialvalue=self._tolerance_preset_int(preset.get("seed", 12345), 12345, 0, 2**31 - 1),
            minvalue=0,
            maxvalue=2**31 - 1,
            parent=self.editor,
        )
        if seed is None:
            return
        self._begin_analysis_progress("Tolerance Monte Carlo")
        try:
            summary = self.run_tolerance_monte_carlo(sample_count=int(sample_count), seed=int(seed))
            report = self.tolerance_monte_carlo_report_text(summary)
            self.append_debug(report)
            ok, backend = self._copy_text_to_clipboard(report)
            if ok:
                self.status_var.set(f"Tolerance Monte Carlo report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Tolerance Monte Carlo report written to Debug; clipboard unavailable.")
            self._finish_analysis_progress("Tolerance Monte Carlo", success=True)
        except Exception as exc:
            self._finish_analysis_progress("Tolerance Monte Carlo", success=False)
            self.append_debug(f"Tolerance Monte Carlo failed: {traceback.format_exc()}")
            messagebox.showerror("Tolerance Monte Carlo", str(exc), parent=self.editor)

    def export_tolerance_monte_carlo_csv(self) -> None:
        records = list(getattr(self, "_last_tolerance_monte_carlo_records", []) or [])
        if not records:
            messagebox.showinfo("Export Tolerance Monte Carlo", "Run Tolerance Monte Carlo Report first.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Tolerance Monte Carlo CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        columns: list[str] = []
        for preferred in ("sample", "kind", "valid", "total_merit", "message"):
            if any(preferred in record for record in records):
                columns.append(preferred)
        for record in records:
            for key in record:
                if key not in columns:
                    columns.append(str(key))
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        self.status_var.set(f"Tolerance Monte Carlo CSV exported: {Path(path).name}")

    def open_save_tolerance_solve_preset_dialog(self) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Save Tolerance Solve Preset", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return
        active = self._active_tolerance_solve_preset()
        default_name = str(active.get("name", "") or "Nominal tolerance solve")
        dialog = tk.Toplevel(self.editor)
        dialog.withdraw()
        dialog.title("Save Tolerance Solve Preset")
        dialog.transient(self.editor)
        dialog.grab_set()
        dialog.resizable(False, False)

        vars_by_key = {
            "name": tk.StringVar(master=dialog, value=default_name),
            "sample_count": tk.StringVar(master=dialog, value=str(active.get("sample_count", 25))),
            "seed": tk.StringVar(master=dialog, value=str(active.get("seed", 12345))),
            "compensator_steps": tk.StringVar(master=dialog, value=str(active.get("compensator_steps", 9))),
            "multi_steps": tk.StringVar(master=dialog, value=str(active.get("multi_steps", 5))),
            "multi_passes": tk.StringVar(master=dialog, value=str(active.get("multi_passes", 2))),
            "tolerance_compare_view": tk.StringVar(
                master=dialog,
                value=str(active.get("tolerance_compare_view", self._current_tolerance_compare_view())),
            ),
        }
        fields = (
            ("Preset name", "name"),
            ("Monte Carlo samples", "sample_count"),
            ("Random seed", "seed"),
            ("Single-compensator steps", "compensator_steps"),
            ("Multi-compensator steps", "multi_steps"),
            ("Multi-compensator passes", "multi_passes"),
        )
        for row_index, (label, key) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=row_index, column=0, sticky="w", padx=12, pady=(10 if row_index == 0 else 4, 2))
            ttk.Entry(dialog, textvariable=vars_by_key[key], width=30).grid(
                row=row_index,
                column=1,
                sticky="ew",
                padx=12,
                pady=(10 if row_index == 0 else 4, 2),
            )
        compare_row = len(fields)
        ttk.Label(dialog, text="Tolerance compare view").grid(row=compare_row, column=0, sticky="w", padx=12, pady=(4, 2))
        ttk.Combobox(
            dialog,
            textvariable=vars_by_key["tolerance_compare_view"],
            values=self.tolerance_compare_view_values,
            state="readonly",
            width=28,
        ).grid(row=compare_row, column=1, sticky="ew", padx=12, pady=(4, 2))
        role_count = len(self._current_tolerance_compensator_preset_payload())
        ttk.Label(
            dialog,
            text=f"Saves merit operands and {role_count} tolerance variable role(s).",
        ).grid(row=compare_row + 1, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 4))

        buttons = ttk.Frame(dialog)
        buttons.grid(row=compare_row + 2, column=0, columnspan=2, sticky="e", padx=12, pady=(8, 12))

        def accept() -> None:
            try:
                self._begin_history_capture()
                preset = self.save_tolerance_solve_preset(
                    vars_by_key["name"].get(),
                    sample_count=int(vars_by_key["sample_count"].get()),
                    seed=int(vars_by_key["seed"].get()),
                    compensator_steps=int(vars_by_key["compensator_steps"].get()),
                    multi_steps=int(vars_by_key["multi_steps"].get()),
                    multi_passes=int(vars_by_key["multi_passes"].get()),
                    tolerance_compare_view=vars_by_key["tolerance_compare_view"].get(),
                )
                self._commit_history_capture()
            except Exception as exc:
                self._history_pending_state = None
                messagebox.showerror("Save Tolerance Solve Preset", str(exc), parent=dialog)
                return
            self.append_debug(self.tolerance_solve_preset_report_text(preset))
            self.status_var.set(f"Saved tolerance solve preset '{preset.get('name')}'. Save layout to persist it.")
            dialog.destroy()

        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="Save Preset", command=accept).pack(side="right")
        dialog.columnconfigure(1, weight=1)
        dialog.update_idletasks()
        self._show_centered_dialog(dialog)
        dialog.wait_window()

    def open_apply_tolerance_solve_preset_dialog(self) -> None:
        presets = self._normalize_tolerance_solve_presets(getattr(self, "tolerance_solve_presets", []))
        if not presets:
            messagebox.showinfo("Apply Tolerance Solve Preset", "No saved tolerance solve presets are available in this layout.", parent=self.editor)
            return
        active = str(getattr(self, "active_tolerance_solve_preset_name", "") or "")
        names = [str(preset.get("name", "")) for preset in presets]
        selected_name = active if active in names else names[0]
        if len(names) == 1:
            try:
                self._begin_history_capture()
                preset = self.apply_tolerance_solve_preset(selected_name)
                self._sync_table()
                self._commit_history_capture()
            except Exception as exc:
                self._history_pending_state = None
                messagebox.showerror("Apply Tolerance Solve Preset", str(exc), parent=self.editor)
                return
            self.append_debug(self.tolerance_solve_preset_report_text(preset))
            self.status_var.set(f"Applied tolerance solve preset '{selected_name}'. Click Update when ready.")
            return

        dialog = tk.Toplevel(self.editor)
        dialog.withdraw()
        dialog.title("Apply Tolerance Solve Preset")
        dialog.transient(self.editor)
        dialog.grab_set()
        dialog.resizable(False, False)
        preset_var = tk.StringVar(master=dialog, value=selected_name)
        ttk.Label(dialog, text="Preset").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        ttk.Combobox(dialog, textvariable=preset_var, values=names, state="readonly", width=36).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 8),
        )
        ttk.Label(
            dialog,
            text="Applies defaults, merit operands, tolerance compare view, and compensator roles without tracing.",
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 8))
        buttons = ttk.Frame(dialog)
        buttons.grid(row=3, column=0, sticky="e", padx=12, pady=(4, 12))

        def accept() -> None:
            selected = preset_var.get().strip()
            try:
                self._begin_history_capture()
                preset = self.apply_tolerance_solve_preset(selected)
                self._sync_table()
                self._commit_history_capture()
            except Exception as exc:
                self._history_pending_state = None
                messagebox.showerror("Apply Tolerance Solve Preset", str(exc), parent=dialog)
                return
            self.append_debug(self.tolerance_solve_preset_report_text(preset))
            self.status_var.set(f"Applied tolerance solve preset '{selected}'. Click Update when ready.")
            dialog.destroy()

        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="Apply Preset", command=accept).pack(side="right")
        dialog.columnconfigure(0, weight=1)
        dialog.update_idletasks()
        self._show_centered_dialog(dialog)
        dialog.wait_window()

    def open_tolerance_worst_sample_comparison_report(self) -> None:
        try:
            comparison = self.tolerance_worst_sample_comparison()
            report = self.tolerance_worst_sample_comparison_report_text(comparison)
            self.append_debug(report)
            ok, backend = self._copy_text_to_clipboard(report)
            if ok:
                self.status_var.set(f"Tolerance comparison report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Tolerance comparison report written to Debug; clipboard unavailable.")
        except Exception as exc:
            messagebox.showerror("Tolerance Worst-Sample Comparison", str(exc), parent=self.editor)

    def export_tolerance_comparison_csv(self) -> None:
        records = list(getattr(self, "_last_tolerance_comparison_records", []) or [])
        if not records:
            messagebox.showinfo("Export Tolerance Comparison", "Run Tolerance Worst-Sample Comparison first.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Tolerance Comparison CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        columns = (
            "category",
            "name",
            "metric",
            "nominal",
            "perturbed",
            "delta",
            "relative_delta",
            "nominal_sample",
            "perturbed_sample",
            "lower",
            "upper",
            "coupling_group",
            "coupling_sign",
            "manufacturing_source_type",
            "manufacturing_source_id",
            "manufacturing_tags",
            "manufacturing_note",
        )
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        self.status_var.set(f"Tolerance comparison CSV exported: {Path(path).name}")

    def open_tolerance_stackup_dashboard_report(self) -> None:
        if not getattr(self, "_last_tolerance_monte_carlo_summary", None):
            messagebox.showinfo("Tolerance Stack-Up Dashboard", "Run Tolerance Monte Carlo Report first.", parent=self.editor)
            return
        try:
            dashboard = self.tolerance_stackup_dashboard()
            report = self.tolerance_stackup_dashboard_report_text(dashboard)
            self.append_debug(report)
            ok, backend = self._copy_text_to_clipboard(report)
            if ok:
                self.status_var.set(f"Tolerance stack-up dashboard copied to clipboard ({backend}).")
            else:
                self.status_var.set("Tolerance stack-up dashboard written to Debug; clipboard unavailable.")
        except Exception as exc:
            messagebox.showerror("Tolerance Stack-Up Dashboard", str(exc), parent=self.editor)

    def export_tolerance_stackup_csv(self) -> None:
        if not getattr(self, "_last_tolerance_monte_carlo_summary", None):
            messagebox.showinfo("Export Tolerance Stack-Up", "Run Tolerance Monte Carlo Report first.", parent=self.editor)
            return
        try:
            dashboard = self.tolerance_stackup_dashboard()
        except Exception as exc:
            messagebox.showerror("Export Tolerance Stack-Up", str(exc), parent=self.editor)
            return
        columns, rows = self.tolerance_stackup_csv_rows(dashboard)
        if not rows:
            messagebox.showinfo("Export Tolerance Stack-Up", "No stack-up rows are available.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Tolerance Stack-Up CSV",
            defaultextension=".csv",
            initialfile="tolerance_stackup_dashboard.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        self.status_var.set(f"Tolerance stack-up CSV exported: {Path(path).name}")

    def open_tolerance_compensator_sweep_report(self) -> None:
        if not getattr(self, "_last_tolerance_monte_carlo_summary", None):
            messagebox.showinfo("Tolerance Compensator Sweep", "Run Tolerance Monte Carlo Report first.", parent=self.editor)
            return
        preset = self._active_tolerance_solve_preset()
        steps = simpledialog.askinteger(
            "Tolerance Compensator Sweep",
            "Sweep steps per compensator",
            initialvalue=self._tolerance_preset_int(preset.get("compensator_steps", 9), 9, 3, 101),
            minvalue=3,
            maxvalue=101,
            parent=self.editor,
        )
        if steps is None:
            return
        self._begin_analysis_progress("Tolerance compensator sweep")
        try:
            summary = self.run_tolerance_compensator_sweep(steps=int(steps))
            report = self.tolerance_compensator_sweep_report_text(summary)
            self.append_debug(report)
            ok, backend = self._copy_text_to_clipboard(report)
            if ok:
                self.status_var.set(f"Tolerance compensator sweep copied to clipboard ({backend}).")
            else:
                self.status_var.set("Tolerance compensator sweep written to Debug; clipboard unavailable.")
            self._finish_analysis_progress("Tolerance compensator sweep", success=True)
        except Exception as exc:
            self._finish_analysis_progress("Tolerance compensator sweep", success=False)
            self.append_debug(f"Tolerance compensator sweep failed: {traceback.format_exc()}")
            messagebox.showerror("Tolerance Compensator Sweep", str(exc), parent=self.editor)

    def export_tolerance_compensator_csv(self) -> None:
        records = list(getattr(self, "_last_tolerance_compensator_records", []) or [])
        if not records:
            messagebox.showinfo("Export Tolerance Compensator", "Run Tolerance Compensator Sweep first.", parent=self.editor)
            return
        columns, rows = self.tolerance_compensator_csv_rows()
        if not rows:
            messagebox.showinfo("Export Tolerance Compensator", "No compensator sweep rows are available.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Tolerance Compensator CSV",
            defaultextension=".csv",
            initialfile="tolerance_compensator_sweep.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        self.status_var.set(f"Tolerance compensator CSV exported: {Path(path).name}")

    def open_tolerance_multi_compensator_report(self) -> None:
        if not getattr(self, "_last_tolerance_monte_carlo_summary", None):
            messagebox.showinfo("Tolerance Multi-Compensator Solve", "Run Tolerance Monte Carlo Report first.", parent=self.editor)
            return
        preset = self._active_tolerance_solve_preset()
        steps = simpledialog.askinteger(
            "Tolerance Multi-Compensator Solve",
            "Sweep steps per variable",
            initialvalue=self._tolerance_preset_int(preset.get("multi_steps", 5), 5, 3, 51),
            minvalue=3,
            maxvalue=51,
            parent=self.editor,
        )
        if steps is None:
            return
        passes = simpledialog.askinteger(
            "Tolerance Multi-Compensator Solve",
            "Coordinate passes",
            initialvalue=self._tolerance_preset_int(preset.get("multi_passes", 2), 2, 1, 20),
            minvalue=1,
            maxvalue=20,
            parent=self.editor,
        )
        if passes is None:
            return
        self._begin_analysis_progress("Tolerance multi-compensator solve")
        try:
            summary = self.run_tolerance_multi_compensator_solve(steps=int(steps), passes=int(passes))
            report = self.tolerance_multi_compensator_report_text(summary)
            self.append_debug(report)
            ok, backend = self._copy_text_to_clipboard(report)
            if ok:
                self.status_var.set(f"Tolerance multi-compensator solve copied to clipboard ({backend}).")
            else:
                self.status_var.set("Tolerance multi-compensator solve written to Debug; clipboard unavailable.")
            self._finish_analysis_progress("Tolerance multi-compensator solve", success=True)
        except Exception as exc:
            self._finish_analysis_progress("Tolerance multi-compensator solve", success=False)
            self.append_debug(f"Tolerance multi-compensator solve failed: {traceback.format_exc()}")
            messagebox.showerror("Tolerance Multi-Compensator Solve", str(exc), parent=self.editor)

    def export_tolerance_multi_compensator_csv(self) -> None:
        records = list(getattr(self, "_last_tolerance_multi_compensator_records", []) or [])
        if not records:
            messagebox.showinfo("Export Tolerance Multi-Compensator", "Run Tolerance Multi-Compensator Solve first.", parent=self.editor)
            return
        columns, rows = self.tolerance_multi_compensator_csv_rows()
        if not rows:
            messagebox.showinfo("Export Tolerance Multi-Compensator", "No multi-compensator rows are available.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Tolerance Multi-Compensator CSV",
            defaultextension=".csv",
            initialfile="tolerance_multi_compensator_solve.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        self.status_var.set(f"Tolerance multi-compensator CSV exported: {Path(path).name}")

    def export_tolerance_overlay_csv(self) -> None:
        if not getattr(self, "_last_tolerance_monte_carlo_summary", None):
            messagebox.showinfo("Export Tolerance Overlay", "Run Tolerance Monte Carlo Report first.", parent=self.editor)
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
            view = self._current_tolerance_compare_view()
            columns, rows = self.tolerance_overlay_csv_rows(view)
        except Exception as exc:
            messagebox.showerror("Export Tolerance Overlay", str(exc), parent=self.editor)
            return
        if not rows:
            messagebox.showinfo("Export Tolerance Overlay", "No tolerance overlay rows are available.", parent=self.editor)
            return
        safe_view = re.sub(r"[^a-z0-9]+", "_", str(view).strip().lower()).strip("_") or "overlay"
        path = filedialog.asksaveasfilename(
            title="Export Tolerance Overlay CSV",
            defaultextension=".csv",
            initialfile=f"tolerance_{safe_view}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        self.status_var.set(f"Tolerance {view} CSV exported: {Path(path).name}")
        self.append_debug(f"Tolerance {view} CSV exported: {path} rows={len(rows)}")

