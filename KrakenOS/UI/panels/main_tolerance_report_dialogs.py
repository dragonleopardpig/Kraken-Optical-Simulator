"""Tolerance report actions and preset dialogs."""

from __future__ import annotations

import csv
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import traceback
from typing import Any
from KrakenOS.UI.panels.row_form_view import render_row_form
from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.presets import (apply_preset as apply_tolerance_preset,
                                           build_apply_tolerance_preset_form,
                                           build_save_tolerance_preset_form)


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
        # docs/design_qt_migration.md phase 3 (bugs/0891): the fields, the validation and what
        # Save writes live in KrakenOS/UI/row_forms/presets.py, which the Qt dialog uses too.
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Save Tolerance Solve Preset",
                                 f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return
        try:
            form = build_save_tolerance_preset_form(self)
        except FormRefused as exc:
            messagebox.showinfo("Save Tolerance Solve Preset", str(exc), parent=self.editor)
            return
        render_row_form(self, form, wraplength=460, modal=True)

    def open_apply_tolerance_solve_preset_dialog(self) -> None:
        # docs/design_qt_migration.md phase 3 (bugs/0892): the preset list and what Apply does
        # live in KrakenOS/UI/row_forms/presets.py, which the Qt dialog uses too. The
        # one-preset shortcut stays here -- with a single preset there is nothing to choose,
        # so it applies through the SAME apply_preset() the dialog calls.
        try:
            form = build_apply_tolerance_preset_form(self)
        except FormRefused as exc:
            messagebox.showinfo("Apply Tolerance Solve Preset", str(exc), parent=self.editor)
            return
        names = list(form.state["names"])
        if len(names) == 1:
            try:
                apply_tolerance_preset(self, names[0])
            except FormRefused as exc:
                messagebox.showerror("Apply Tolerance Solve Preset", str(exc),
                                     parent=self.editor)
            return
        render_row_form(self, form, wraplength=380, modal=True)

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

