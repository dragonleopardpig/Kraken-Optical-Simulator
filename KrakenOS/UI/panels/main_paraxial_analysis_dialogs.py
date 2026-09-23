"""Main paraxial and Gaussian analysis dialogs."""

from __future__ import annotations

import csv
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.paraxial_calculator import (
    CalculatorFailed, CalculatorInputs, NothingToApply,
    apply_solution as apply_paraxial_solution,
    PROMPT as PARAXIAL_PROMPT, field_states as paraxial_field_states, format_calc,
    initial_inputs as paraxial_initial_inputs,
    load_from_layout as load_paraxial_from_layout, solve as solve_paraxial)
from KrakenOS.UI.reports import ReportFailed
from KrakenOS.UI.reports.gaussian_beam import COLUMNS as GAUSSIAN_BEAM_COLUMNS
from KrakenOS.UI.reports.paraxial_matrix import build_paraxial_matrix_report

GAUSSIAN_BEAM_COLUMN_KEYS = tuple(column.key for column in GAUSSIAN_BEAM_COLUMNS)


class MainParaxialAnalysisDialogs:
    """Own paraxial/Gaussian report windows while delegating optical calculations to the editor."""

    def __init__(self, editor: Any, *, short_error_message: Callable[[BaseException], str]) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "short_error_message", short_error_message)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "short_error_message"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_paraxial_calculator(self) -> None:
        dialog = tk.Toplevel(self.editor)
        dialog.withdraw()
        dialog.title("Paraxial Calculator")
        dialog.transient(self.editor)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.columnconfigure(1, weight=1)

        # docs/design_qt_migration.md phase 3: the opening values come from the shared model, so
        # the Qt form starts on exactly the same ones.
        opening = paraxial_initial_inputs(self)

        # master=dialog on purpose: an unmastered tk.StringVar attaches to the DEFAULT root, which
        # is a different interpreter as soon as a second one exists (a guard building its own
        # editor) -- the variable then lives where its widgets do not.
        effl_var = tk.StringVar(master=dialog, value=opening.effl)
        ppa_var = tk.StringVar(master=dialog, value=opening.ppa)
        ppp_var = tk.StringVar(master=dialog, value=opening.ppp)
        ep_z_var = tk.StringVar(master=dialog, value="n/a")
        xp_z_var = tk.StringVar(master=dialog, value="n/a")
        magnification_var = tk.StringVar(master=dialog, value=opening.magnification)
        solve_for_var = tk.StringVar(master=dialog, value=opening.solve_for)
        object_mode_var = tk.StringVar(master=dialog, value=opening.object_mode)
        object_distance_var = tk.StringVar(master=dialog, value=opening.object_distance)
        image_distance_var = tk.StringVar(master=dialog, value=opening.image_distance)
        load_note_var = tk.StringVar(master=dialog, value=PARAXIAL_PROMPT)
        result_var = tk.StringVar(master=dialog, value=PARAXIAL_PROMPT)
        detail_var = tk.StringVar(master=dialog, value="")
        solved_payload: dict[str, object] = {}
        loaded_paraxial_solution: dict[str, float] | None = None

        def _calculator_inputs() -> CalculatorInputs:
            return CalculatorInputs(
                solve_for=solve_for_var.get(), effl=effl_var.get(), ppa=ppa_var.get(),
                ppp=ppp_var.get(), object_mode=object_mode_var.get(),
                object_distance=object_distance_var.get(),
                image_distance=image_distance_var.get(),
                magnification=magnification_var.get())

        def _try_load_from_layout() -> None:
            nonlocal loaded_paraxial_solution
            values, note, loaded_paraxial_solution = load_paraxial_from_layout(self)
            if "effl" in values:
                effl_var.set(values["effl"])
                ppa_var.set(values["ppa"])
                ppp_var.set(values["ppp"])
            ep_z_var.set(values.get("ep_z", "n/a"))
            xp_z_var.set(values.get("xp_z", "n/a"))
            load_note_var.set(note)

        ttk.Label(dialog, text="Solve for").grid(row=0, column=0, padx=(12, 8), pady=(12, 4), sticky="w")
        solve_for_menu = ttk.Combobox(
            dialog,
            textvariable=solve_for_var,
            state="readonly",
            width=26,
            values=[
                "Image distance",
                "Object distance",
                "Magnification",
                "Distances from magnification",
            ],
        )
        solve_for_menu.grid(row=0, column=1, padx=(0, 12), pady=(12, 4), sticky="ew")

        ttk.Label(dialog, text="EFL / EFFL [mm]").grid(row=1, column=0, padx=(12, 8), pady=2, sticky="w")
        effl_entry = ttk.Entry(dialog, textvariable=effl_var, width=22)
        effl_entry.grid(row=1, column=1, padx=(0, 12), pady=2, sticky="ew")

        ttk.Label(dialog, text="H1 offset PPA [mm]").grid(row=2, column=0, padx=(12, 8), pady=2, sticky="w")
        ppa_entry = ttk.Entry(dialog, textvariable=ppa_var, width=22)
        ppa_entry.grid(row=2, column=1, padx=(0, 12), pady=2, sticky="ew")

        ttk.Label(dialog, text="H2 offset PPP [mm]").grid(row=3, column=0, padx=(12, 8), pady=2, sticky="w")
        ppp_entry = ttk.Entry(dialog, textvariable=ppp_var, width=22)
        ppp_entry.grid(row=3, column=1, padx=(0, 12), pady=2, sticky="ew")

        ttk.Label(dialog, text="Object mode").grid(row=4, column=0, padx=(12, 8), pady=(8, 2), sticky="w")
        object_mode_menu = ttk.Combobox(
            dialog,
            textvariable=object_mode_var,
            state="readonly",
            width=22,
            values=["Finite", "Infinity"],
        )
        object_mode_menu.grid(row=4, column=1, padx=(0, 12), pady=(8, 2), sticky="ew")

        ttk.Label(dialog, text="Object distance [mm]").grid(row=5, column=0, padx=(12, 8), pady=2, sticky="w")
        object_distance_entry = ttk.Entry(dialog, textvariable=object_distance_var, width=22)
        object_distance_entry.grid(row=5, column=1, padx=(0, 12), pady=2, sticky="ew")

        ttk.Label(dialog, text="Image distance [mm]").grid(row=6, column=0, padx=(12, 8), pady=2, sticky="w")
        image_distance_entry = ttk.Entry(dialog, textvariable=image_distance_var, width=22)
        image_distance_entry.grid(row=6, column=1, padx=(0, 12), pady=2, sticky="ew")

        ttk.Label(dialog, text="Magnification m").grid(row=7, column=0, padx=(12, 8), pady=2, sticky="w")
        magnification_entry = ttk.Entry(dialog, textvariable=magnification_var, width=22)
        magnification_entry.grid(row=7, column=1, padx=(0, 12), pady=2, sticky="ew")

        ttk.Label(dialog, text="EP z [mm]").grid(row=8, column=0, padx=(12, 8), pady=2, sticky="w")
        ep_z_entry = ttk.Entry(dialog, textvariable=ep_z_var, width=22, state="readonly")
        ep_z_entry.grid(row=8, column=1, padx=(0, 12), pady=2, sticky="ew")

        ttk.Label(dialog, text="XP z [mm]").grid(row=9, column=0, padx=(12, 8), pady=2, sticky="w")
        xp_z_entry = ttk.Entry(dialog, textvariable=xp_z_var, width=22, state="readonly")
        xp_z_entry.grid(row=9, column=1, padx=(0, 12), pady=2, sticky="ew")

        note_label = ttk.Label(dialog, textvariable=load_note_var, foreground="#475569", wraplength=500, justify="left")
        note_label.grid(row=10, column=0, columnspan=2, padx=12, pady=(8, 2), sticky="w")

        ttk.Label(dialog, textvariable=result_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=11, column=0, columnspan=2, padx=12, pady=(4, 0), sticky="w"
        )
        ttk.Label(dialog, textvariable=detail_var, foreground="#475569", wraplength=500, justify="left").grid(
            row=12, column=0, columnspan=2, padx=12, pady=(2, 0), sticky="w"
        )

        def _refresh_mode_state(_event=None) -> None:
            states = paraxial_field_states(solve_for_var.get(), object_mode_var.get())
            object_distance_entry.configure(state=states["object_distance"])
            image_distance_entry.configure(state=states["image_distance"])
            magnification_entry.configure(state=states["magnification"])
            solved_payload.clear()

        def _solve(_event=None) -> None:
            solved_payload.clear()
            try:
                solution = solve_paraxial(self, _calculator_inputs(), loaded_paraxial_solution)
            except Exception as exc:
                message = (str(exc) if isinstance(exc, CalculatorFailed)
                           else self.short_error_message(exc))
                result_var.set(f"Solve failed: {message}")
                detail_var.set("")
                return
            solved_payload.update(solution.payload)
            if solution.magnification is not None:
                magnification_var.set(format_calc(solution.magnification))
            if solution.object_distance is not None:
                object_distance_var.set(format_calc(solution.object_distance))
            if solution.image_distance is not None:
                image_distance_var.set(format_calc(solution.image_distance))
            result_var.set(solution.result)
            detail_var.set(solution.detail)

        def _apply_to_layout() -> bool:
            if not solved_payload:
                _solve()
                if not solved_payload:
                    return False
            try:
                status = apply_paraxial_solution(self, dict(solved_payload), result_var.get())
            except NothingToApply as exc:
                self.status_var.set(str(exc))
                return False
            except Exception as exc:
                message = (str(exc) if isinstance(exc, CalculatorFailed)
                           else self.short_error_message(exc))
                self.append_debug(f"Paraxial calculator apply failed: {exc}")
                messagebox.showerror("Paraxial Calculator", message)
                self.status_var.set(f"Paraxial calculator apply failed: {message}")
                return False
            self.status_var.set(status)
            return True

        def _apply_and_close() -> None:
            if _apply_to_layout():
                dialog.destroy()

        buttons = ttk.Frame(dialog)
        buttons.grid(row=13, column=0, columnspan=2, padx=12, pady=(10, 12), sticky="e")
        ttk.Button(buttons, text="Use Current Layout", command=lambda: (
            object_mode_var.set(self._current_object_mode()),
            object_distance_var.set(f"{(float(self.rows[0].thickness) if self.rows else 0.0):.6g}"),
            image_distance_var.set(f"{(float(self.rows[max(0, len(self.rows) - 2)].thickness) if self.rows else 0.0):.6g}"),
            _try_load_from_layout(),
            _refresh_mode_state(),
            _solve(),
        )).pack(side="left")
        ttk.Button(buttons, text="Solve", command=_solve).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Apply to Layout", command=_apply_and_close).pack(side="left", padx=(8, 0))
        ttk.Button(
            buttons,
            text="Rules of Thumb…",
            command=self.show_rules_of_thumb,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            buttons,
            text="Formula Sheet…",
            command=self.show_formula_help,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Close", command=dialog.destroy).pack(side="left", padx=(8, 0))

        solve_for_menu.bind("<<ComboboxSelected>>", lambda _e: (_refresh_mode_state(), _solve()))
        object_mode_menu.bind("<<ComboboxSelected>>", lambda _e: (_refresh_mode_state(), _solve()))
        for entry in (effl_entry, ppa_entry, ppp_entry, object_distance_entry, image_distance_entry, magnification_entry):
            entry.bind("<Return>", _solve)

        _try_load_from_layout()
        _refresh_mode_state()
        _solve()
        self._center_dialog_on_screen(dialog)
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()

    def _show_paraxial_solve_dialog(self, result: dict[str, float | str]) -> bool:
        dialog = tk.Toplevel(self)
        dialog.title("Paraxial Solve")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        target = str(result["target"])
        if target == "image":
            intro = "Review the paraxial solve before applying it."
        elif target == "object":
            intro = "Review the paraxial object-distance solve before applying it."
        else:
            intro = "Solve the selected thickness while keeping the other thickness values fixed."
        ttk.Label(dialog, text=intro, padding=(12, 12, 12, 4)).grid(row=0, column=0, columnspan=2, sticky="w")

        rows = [
            ("EFFL [mm]", self._format_paraxial_value(result["effl"])),
            ("Front principal plane PPA [mm]", self._format_paraxial_value(result["ppa"])),
            ("Back principal plane PPP [mm]", self._format_paraxial_value(result["ppp"])),
            ("Object mode", str(result["object_mode_before"])),
            ("Object distance before [mm]", self._format_paraxial_value(result["object_distance_before"])),
            ("Image distance before [mm]", self._format_paraxial_value(result["image_distance_before"])),
            ("Object distance from H1 [mm]", self._format_paraxial_value(result["object_principal"])),
            ("Image distance from H2 [mm]", self._format_paraxial_value(result["image_principal"])),
        ]
        if target == "image":
            rows.append(("Solved image gap [mm]", self._format_paraxial_value(result["solved_distance"])))
            rows.append(("Apply to row", str(int(result["selected_row"]))))
        elif target == "object":
            rows.append(("Solved object gap [mm]", self._format_paraxial_value(result["solved_distance"])))
            rows.append(("Object mode after", str(result["object_mode_after"])))
        else:
            rows.extend(
                [
                    ("Solve row", f"{int(result['selected_row'])} ({str(result['target_label'])})"),
                    ("Start thickness [mm]", self._format_paraxial_value(result["start_value"])),
                    ("Solved thickness [mm]", self._format_paraxial_value(result["solved_distance"])),
                    ("Predicted image gap [mm]", self._format_paraxial_value(result["predicted_image_gap"])),
                    ("Residual [mm]", self._format_paraxial_value(result["residual"])),
                    ("Samples", str(int(result["sample_count"]))),
                ]
            )

        for row_idx, (label, value) in enumerate(rows, start=1):
            ttk.Label(dialog, text=label).grid(row=row_idx, column=0, padx=(12, 12), pady=2, sticky="w")
            ttk.Label(dialog, text=value, font=("TkDefaultFont", 10, "bold")).grid(
                row=row_idx,
                column=1,
                padx=(0, 12),
                pady=2,
                sticky="e",
            )

        formula = (
            "Thickness solve holds the other gaps fixed and re-evaluates the paraxial cardinal points."
            if target == "thickness"
            else "Thin-lens with principal planes: 1/f = 1/s + 1/s'"
        )
        ttk.Label(dialog, text=formula, foreground="#4b5563", padding=(12, 8, 12, 4)).grid(
            row=len(rows) + 1,
            column=0,
            columnspan=2,
            sticky="w",
        )

        decision = {"apply": False}

        def accept() -> None:
            decision["apply"] = True
            dialog.destroy()

        def cancel() -> None:
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        buttons = ttk.Frame(dialog, padding=(12, 4, 12, 12))
        buttons.grid(row=len(rows) + 2, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Apply", command=accept).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=cancel).pack(side="left", padx=(8, 0))
        self._center_dialog_over_main_window(dialog)
        self.wait_window(dialog)
        return bool(decision["apply"])

    def _show_folded_mirror_solve_dialog(self, result: dict[str, float | str]) -> bool:
        dialog = tk.Toplevel(self)
        dialog.title("Folded Mirror Solve")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(
            dialog,
            text="Estimate the mirror-to-image gap from the straight-through paraxial image distance.",
            padding=(12, 12, 12, 4),
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        rows = [
            ("EFFL [mm]", self._format_paraxial_value(result["effl"])),
            ("Front principal plane PPA [mm]", self._format_paraxial_value(result["ppa"])),
            ("Back principal plane PPP [mm]", self._format_paraxial_value(result["ppp"])),
            ("Object distance before [mm]", self._format_paraxial_value(result["object_distance_before"])),
            ("Object distance from H1 [mm]", self._format_paraxial_value(result["object_principal"])),
            ("Image distance from H2 [mm]", self._format_paraxial_value(result["image_principal"])),
            ("Straight image gap [mm]", self._format_paraxial_value(result["straight_image_gap"])),
            ("Gap before mirror [mm]", self._format_paraxial_value(result["upstream_gap"])),
            ("Solved mirror thickness [mm]", self._format_paraxial_value(result["solved_distance"])),
            ("Apply to row", str(int(result["selected_row"]))),
        ]
        for row_index, (label, value) in enumerate(rows, start=1):
            ttk.Label(dialog, text=label).grid(row=row_index, column=0, padx=(12, 12), pady=2, sticky="w")
            ttk.Label(dialog, text=value, font=("TkDefaultFont", 10, "bold")).grid(
                row=row_index,
                column=1,
                padx=(0, 12),
                pady=2,
                sticky="e",
            )

        ttk.Label(
            dialog,
            text="Rule used: mirror thickness = straight-through image gap - gap before mirror",
            foreground="#4b5563",
            padding=(12, 8, 12, 4),
        ).grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w")

        decision = {"apply": False}

        def accept() -> None:
            decision["apply"] = True
            dialog.destroy()

        def cancel() -> None:
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        buttons = ttk.Frame(dialog, padding=(12, 4, 12, 12))
        buttons.grid(row=len(rows) + 2, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Apply", command=accept).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=cancel).pack(side="left", padx=(8, 0))
        self._center_dialog_over_main_window(dialog)
        self.wait_window(dialog)
        return bool(decision["apply"])

    def _show_best_focus_dialog(self, result: dict[str, float | str]) -> bool:
        dialog = tk.Toplevel(self)
        dialog.title("Best Image Solve")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(
            dialog,
            text="Refine the selected thickness by minimizing traced image-plane spot RMS.",
            padding=(12, 12, 12, 4),
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        rows = [
            ("Apply to row", str(int(result["selected_row"]))),
            ("Target", str(result["target_label"])),
            ("Start value [mm]", self._format_paraxial_value(result["start_value"])),
            ("Search lower [mm]", self._format_paraxial_value(result["lower"])),
            ("Search upper [mm]", self._format_paraxial_value(result["upper"])),
            ("Solved value [mm]", self._format_paraxial_value(result["solved_distance"])),
            ("Best spot RMS [mm]", self._format_paraxial_value(result["best_rms"])),
            ("Metric", str(result.get("metric_label", "Image-plane RMS"))),
            ("Samples", str(int(result["sample_count"]))),
        ]
        filter_text = str(result.get("filter_text", "") or "").strip()
        if filter_text:
            rows.insert(7, ("Target path", filter_text))
        for row_index, (label, value) in enumerate(rows, start=1):
            ttk.Label(dialog, text=label).grid(row=row_index, column=0, padx=(12, 12), pady=2, sticky="w")
            ttk.Label(dialog, text=value, font=("TkDefaultFont", 10, "bold")).grid(
                row=row_index,
                column=1,
                padx=(0, 12),
                pady=2,
                sticky="e",
            )

        ttk.Label(
            dialog,
            text="This is a traced image solve, not a paraxial estimate.",
            foreground="#4b5563",
            padding=(12, 8, 12, 4),
        ).grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w")

        decision = {"apply": False}

        def accept() -> None:
            decision["apply"] = True
            dialog.destroy()

        def cancel() -> None:
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        buttons = ttk.Frame(dialog, padding=(12, 4, 12, 12))
        buttons.grid(row=len(rows) + 2, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Apply", command=accept).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=cancel).pack(side="left", padx=(8, 0))
        self._center_dialog_over_main_window(dialog)
        self.wait_window(dialog)
        return bool(decision["apply"])


    @staticmethod
    def _matrix_cell(matrix, row: int, column: int) -> float:
        arr = np.asarray(matrix, dtype=float)
        return float(arr[row, column])

    def open_paraxial_matrix_report(self) -> None:
        # docs/design_qt_migration.md phase 3: the NUMBERS come from the toolkit-free report
        # builder, which the Qt dialog renders too -- one source of truth, so a value can never
        # differ between the two views. This function is now layout only.
        try:
            report = build_paraxial_matrix_report(self)
        except ReportFailed as exc:
            messagebox.showerror(
                "Paraxial Matrix Report",
                f"Could not build paraxial matrix report:\n\n{exc}", parent=self.editor)
            self.status_var.set(f"Paraxial matrix report failed: {exc}")
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(report.title)
        window.geometry("1180x620")
        window.minsize(860, 420)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        ttk.Label(window, text=report.summary, padding=(8, 8, 8, 4), anchor="w").grid(
            row=0, column=0, sticky="ew")

        toolbar = ttk.Frame(window, padding=(8, 0, 8, 4))
        toolbar.grid(row=1, column=0, sticky="ew")

        frame = ttk.Frame(window, padding=8)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=report.keys, show="headings")
        for column in report.columns:
            tree.heading(column.key, text=column.heading)
            tree.column(column.key, width=column.width,
                        anchor=("e" if column.numeric else "w"), stretch=column.stretch)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        for index in range(len(report.rows)):
            tree.insert("", "end", values=tuple(
                report.cell(index, column_index) for column_index in range(len(report.columns))))

        def export_csv() -> None:
            path = filedialog.asksaveasfilename(
                title="Export Paraxial Matrix CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*")],
                parent=window,
            )
            if not path:
                return
            report.write_csv(path)
            self.status_var.set(f"Paraxial matrix CSV exported: {Path(path).name}")

        ttk.Button(toolbar, text="Export CSV", command=export_csv).pack(side="left")
        ttk.Button(toolbar, text="Close", command=window.destroy).pack(side="left", padx=(6, 0))

        self._show_centered_dialog(window)


    def open_gaussian_beam_report(self) -> None:
        # docs/design_qt_migration.md phase 3: the beam propagation, the columns, the formatting
        # and the cavity eigenmode live in KrakenOS/UI/reports/gaussian_beam.py, which the Qt
        # dialog renders too. This function is layout and input plumbing.
        from KrakenOS.UI.reports.gaussian_beam import (
            build_gaussian_beam_report, default_inputs, format_value, gaussian_cavity_eigenmode)

        try:
            defaults = default_inputs(self)
        except Exception as exc:
            message = self.short_error_message(exc)
            messagebox.showerror("Gaussian Beam Report",
                                 f"Could not build Gaussian beam report:\n\n{message}",
                                 parent=self.editor)
            self.status_var.set(f"Gaussian beam report failed: {message}")
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Gaussian Beam Report")
        window.geometry("1240x660")
        window.minsize(900, 460)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(3, weight=1)

        summary_var = tk.StringVar(master=window, value="")
        ttk.Label(window, textvariable=summary_var, padding=(8, 8, 8, 4), anchor="w").grid(
            row=0, column=0, sticky="ew")

        controls = ttk.LabelFrame(window, text="Input beam", padding=8)
        controls.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        for column in range(10):
            controls.columnconfigure(column, weight=1 if column % 2 else 0)

        wavelength_var = tk.StringVar(master=window, value=f"{defaults['wavelength']:.6g}")
        waist_var = tk.StringVar(master=window, value=f"{defaults['waist']:.6g}")
        offset_var = tk.StringVar(master=window, value=f"{defaults['offset']:.6g}")
        m2_var = tk.StringVar(master=window, value=f"{defaults['m2']:.6g}")

        for col, (label, var, width) in enumerate(
            (
                ("Wavelength [um]", wavelength_var, 10),
                ("Waist radius [mm]", waist_var, 10),
                ("Waist offset [mm]", offset_var, 10),
                ("M2", m2_var, 8),
            )
        ):
            ttk.Label(controls, text=label).grid(row=0, column=2 * col, sticky="w", padx=(0 if col == 0 else 10, 4))
            ttk.Entry(controls, textvariable=var, width=width).grid(row=0, column=2 * col + 1, sticky="ew")

        toolbar = ttk.Frame(window, padding=(8, 0, 8, 4))
        toolbar.grid(row=2, column=0, sticky="ew")
        cavity_status_var = tk.StringVar(master=window, value="")

        frame = ttk.Frame(window, padding=8)
        frame.grid(row=3, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=GAUSSIAN_BEAM_COLUMN_KEYS, show="headings")
        for column in GAUSSIAN_BEAM_COLUMNS:
            tree.heading(column.key, text=column.heading)
            tree.column(column.key, width=column.width,
                        anchor=("e" if column.numeric else "w"), stretch=column.stretch)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        held: dict[str, object] = {}

        def recompute() -> None:
            try:
                report = build_gaussian_beam_report(
                    self,
                    wavelength=wavelength_var.get(), waist=waist_var.get(),
                    offset=offset_var.get(), m2=m2_var.get())
            except ReportFailed as exc:
                summary_var.set(f"Gaussian beam report failed: {exc}")
                self.status_var.set(f"Gaussian beam report failed: {exc}")
                return
            held["report"] = report
            children = tree.get_children()
            if children:
                tree.delete(*children)
            for index in range(len(report.rows)):
                tree.insert("", "end", values=tuple(
                    report.cell(index, column_index)
                    for column_index in range(len(report.columns))))
            summary_var.set(report.summary)
            self.status_var.set(report.status)

        def export_csv() -> None:
            report = held.get("report")
            if report is None:
                recompute()
                report = held.get("report")
            if report is None or not report.rows:
                return
            path = filedialog.asksaveasfilename(
                title="Export Gaussian Beam CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*")],
                parent=window,
            )
            if not path:
                return
            report.write_csv(path)
            self.status_var.set(f"Gaussian beam CSV exported: {Path(path).name}")

        def apply_cavity_eigenmode() -> None:
            try:
                eigenmode = gaussian_cavity_eigenmode(self, wavelength_var.get(), m2_var.get())
                if not eigenmode.stable:
                    message = (
                        f"Cavity eigenmode unavailable: {eigenmode.message}; "
                        f"g={format_value(eigenmode.stability_parameter)}"
                    )
                    cavity_status_var.set(message)
                    self.status_var.set(message)
                    return
                waist_var.set(format_value(eigenmode.waist_radius_mm))
                offset_var.set(format_value(eigenmode.q_real_mm))
                cavity_status_var.set(
                    "Cavity eigenmode applied: "
                    f"q={format_value(eigenmode.q_real_mm)}+i{format_value(eigenmode.q_imag_mm)} mm, "
                    f"w0={format_value(eigenmode.waist_radius_mm)} mm, "
                    f"g={format_value(eigenmode.stability_parameter)}, "
                    f"Gouy/RT={format_value(eigenmode.round_trip_gouy_rad)} rad."
                )
                recompute()
            except Exception as exc:
                message = f"Cavity eigenmode failed: {self.short_error_message(exc)}"
                cavity_status_var.set(message)
                self.status_var.set(message)

        ttk.Button(toolbar, text="Recompute", command=recompute).pack(side="left")
        ttk.Button(toolbar, text="Use Cavity Eigenmode", command=apply_cavity_eigenmode).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export CSV", command=export_csv).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=window.destroy).pack(side="left", padx=(6, 0))
        ttk.Label(toolbar, textvariable=cavity_status_var, foreground="#5f6b7a").pack(side="left", padx=(12, 0), fill="x", expand=True)

        self._show_centered_dialog(window)
        recompute()
