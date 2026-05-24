"""Main paraxial and Gaussian analysis dialogs."""

from __future__ import annotations

import csv
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import numpy as np

import KrakenOS as Kos


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

        object_default = float(self.rows[0].thickness) if self.rows else 0.0
        image_row = max(0, len(self.rows) - 2)
        image_default = float(self.rows[image_row].thickness) if self.rows else 0.0
        object_mode_default = self._current_object_mode()

        effl_var = tk.StringVar(value=f"{self._current_effl_estimate():.6g}")
        ppa_var = tk.StringVar(value="0")
        ppp_var = tk.StringVar(value="0")
        ep_z_var = tk.StringVar(value="n/a")
        xp_z_var = tk.StringVar(value="n/a")
        magnification_var = tk.StringVar(value="0")
        solve_for_var = tk.StringVar(value="Image distance")
        object_mode_var = tk.StringVar(value=object_mode_default)
        object_distance_var = tk.StringVar(value=f"{object_default:.6g}")
        image_distance_var = tk.StringVar(value=f"{image_default:.6g}")
        load_note_var = tk.StringVar(value="Set known values, then click Solve.")
        result_var = tk.StringVar(value="Set known values, then click Solve.")
        detail_var = tk.StringVar(value="")
        solved_payload: dict[str, object] = {}
        loaded_paraxial_solution: dict[str, float] | None = None

        def _format_calc(value: float) -> str:
            if not np.isfinite(value):
                return "Infinity"
            return f"{float(value):.6g}"

        def _loaded_solution_matches_ui() -> bool:
            if loaded_paraxial_solution is None:
                return False
            try:
                return (
                    abs(_read_float(effl_var, "EFL") - float(loaded_paraxial_solution["effl_display"])) <= 1e-6
                    and abs(_read_float(ppa_var, "H1 offset") - float(loaded_paraxial_solution["ppa"])) <= 1e-6
                    and abs(_read_float(ppp_var, "H2 offset") - float(loaded_paraxial_solution["ppp"])) <= 1e-6
                )
            except Exception:
                return False

        def _try_load_from_layout() -> None:
            note_parts: list[str] = []
            nonlocal loaded_paraxial_solution
            loaded_paraxial_solution = None
            try:
                a, b, c, d, effl_display, ppa, ppp = self._exact_paraxial_solution_for_rows(self.rows)
                effl_var.set(f"{effl_display:.6g}")
                ppa_var.set(f"{float(ppa):.6g}")
                ppp_var.set(f"{float(ppp):.6g}")
                loaded_paraxial_solution = {
                    "a": float(a),
                    "b": float(b),
                    "c": float(c),
                    "d": float(d),
                    "effl_display": float(effl_display),
                    "ppa": float(ppa),
                    "ppp": float(ppp),
                }
                note_parts.append("Loaded EFL/H1/H2 from layout.")
            except Exception as exc:
                note_parts.append(f"Cardinal extraction unavailable ({self.short_error_message(exc)}).")
            try:
                system = self.build_system()
                pupil = Kos.PupilCalc(
                    system,
                    self._analysis_surface_index(),
                    self._current_wavelength(),
                    self._current_aperture_type(),
                    self._current_aperture_value(),
                )
                ep_z_var.set(_format_calc(float(pupil.PosPupInp[2])))
                xp_z_var.set(_format_calc(float(pupil.PosPupOut[2])))
                note_parts.append("Loaded EP/XP from current aperture settings.")
            except Exception:
                ep_z_var.set("n/a")
                xp_z_var.set("n/a")
            load_note_var.set(" ".join(note_parts) if note_parts else "Using manual values.")

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

        def _read_float(var: tk.StringVar, label: str) -> float:
            text = var.get().strip()
            if not text:
                raise RuntimeError(f"{label} is required")
            try:
                value = float(text)
            except ValueError as exc:
                raise RuntimeError(f"{label} must be numeric") from exc
            if not np.isfinite(value):
                raise RuntimeError(f"{label} must be finite")
            return float(value)

        def _refresh_mode_state(_event=None) -> None:
            target = solve_for_var.get().strip()
            mode = object_mode_var.get().strip()
            if target == "Image distance":
                if mode == "Infinity":
                    object_distance_entry.configure(state="disabled")
                else:
                    object_distance_entry.configure(state="normal")
                image_distance_entry.configure(state="disabled")
                magnification_entry.configure(state="readonly")
            elif target == "Object distance":
                object_distance_entry.configure(state="disabled")
                image_distance_entry.configure(state="normal")
                magnification_entry.configure(state="readonly")
            elif target == "Magnification":
                if mode == "Infinity":
                    object_distance_entry.configure(state="disabled")
                else:
                    object_distance_entry.configure(state="normal")
                image_distance_entry.configure(state="normal")
                magnification_entry.configure(state="disabled")
            else:
                object_distance_entry.configure(state="disabled")
                image_distance_entry.configure(state="disabled")
                magnification_entry.configure(state="normal")
            solved_payload.clear()

        def _solve(_event=None) -> None:
            try:
                f = _read_float(effl_var, "EFL")
                if abs(f) <= 1e-12:
                    raise RuntimeError("EFL must be non-zero")
                h1 = _read_float(ppa_var, "H1 offset")
                h2 = _read_float(ppp_var, "H2 offset")
                target = solve_for_var.get().strip()
                mode = object_mode_var.get().strip()
                solved_payload.clear()
                use_matrix_solution = _loaded_solution_matches_ui()
                matrix_solution = loaded_paraxial_solution if use_matrix_solution else None

                if target == "Image distance":
                    if matrix_solution is not None:
                        object_distance = 0.0 if mode == "Infinity" else _read_float(object_distance_var, "Object distance")
                        image_distance = self._compute_image_gap_from_paraxial_solution(
                            float(matrix_solution["a"]),
                            float(matrix_solution["b"]),
                            float(matrix_solution["c"]),
                            float(matrix_solution["d"]),
                            object_distance,
                            mode,
                        )
                        object_principal = float("inf") if mode == "Infinity" else object_distance + h1
                        image_principal = image_distance - h2
                        magnification = 0.0 if mode == "Infinity" else (
                            float(image_principal / object_principal)
                            if np.isfinite(object_principal) and abs(object_principal) > 1e-12
                            else float("inf")
                        )
                    else:
                        if mode == "Infinity":
                            image_distance = f + h2
                            object_principal = float("inf")
                            image_principal = float(f)
                            magnification = 0.0
                        else:
                            object_distance = _read_float(object_distance_var, "Object distance")
                            object_principal = object_distance + h1
                            if abs(object_principal) <= 1e-12:
                                raise RuntimeError("Object is on H1; cannot solve image distance")
                            balance = (1.0 / f) - (1.0 / object_principal)
                            if abs(balance) <= 1e-12:
                                image_distance = float("inf")
                                image_principal = float("inf")
                                magnification = float("inf")
                            else:
                                image_principal = 1.0 / balance
                                image_distance = image_principal + h2
                                magnification = image_principal / object_principal
                    solved_payload.update(
                        {
                            "target": "image",
                            "value": image_distance,
                            "object_mode_after": mode,
                        }
                    )
                    magnification_var.set(_format_calc(magnification))
                    result_var.set(f"Image distance = {self._format_paraxial_value(image_distance)} mm")
                    detail_var.set(
                        "s={obj}, s'={img}, m={mag}".format(
                            obj=self._format_paraxial_value(object_principal),
                            img=self._format_paraxial_value(image_principal),
                            mag=self._format_paraxial_value(magnification),
                        )
                    )
                elif target == "Object distance":
                    image_distance = _read_float(image_distance_var, "Image distance")
                    if matrix_solution is not None:
                        object_distance = self._compute_object_gap_from_paraxial_solution(
                            float(matrix_solution["a"]),
                            float(matrix_solution["b"]),
                            float(matrix_solution["c"]),
                            float(matrix_solution["d"]),
                            image_distance,
                        )
                        if not np.isfinite(object_distance) or abs(object_distance) > 1e9:
                            object_principal = float("inf")
                            object_distance = float("inf")
                            mode_after = "Infinity"
                        else:
                            object_principal = object_distance + h1
                            mode_after = "Finite"
                        image_principal = image_distance - h2
                    else:
                        image_principal = image_distance - h2
                        if abs(image_principal) <= 1e-12:
                            raise RuntimeError("Image is on H2; cannot solve object distance")
                        balance = (1.0 / f) - (1.0 / image_principal)
                        if abs(balance) <= 1e-12:
                            object_principal = float("inf")
                            object_distance = float("inf")
                            mode_after = "Infinity"
                        else:
                            object_principal = 1.0 / balance
                            object_distance = object_principal - h1
                            mode_after = "Infinity" if (not np.isfinite(object_distance) or abs(object_distance) > 1e9) else "Finite"
                    magnification = image_principal / object_principal if np.isfinite(object_principal) and abs(object_principal) > 1e-12 else float("inf")
                    solved_payload.update(
                        {
                            "target": "object",
                            "value": object_distance,
                            "object_mode_after": mode_after,
                        }
                    )
                    magnification_var.set(_format_calc(magnification))
                    result_var.set(f"Object distance = {self._format_paraxial_value(object_distance)} mm")
                    detail_var.set(
                        "s={obj}, s'={img}, m={mag}".format(
                            obj=self._format_paraxial_value(object_principal),
                            img=self._format_paraxial_value(image_principal),
                            mag=self._format_paraxial_value(magnification),
                        )
                    )
                elif target == "Magnification":
                    if mode == "Infinity":
                        object_principal = float("inf")
                        image_principal = _read_float(image_distance_var, "Image distance") - h2
                        magnification = 0.0
                    else:
                        object_distance = _read_float(object_distance_var, "Object distance")
                        image_distance = _read_float(image_distance_var, "Image distance")
                        object_principal = object_distance + h1
                        image_principal = image_distance - h2
                        if abs(object_principal) <= 1e-12:
                            raise RuntimeError("Object is on H1; cannot solve magnification")
                        magnification = image_principal / object_principal
                    solved_payload.update({"target": "magnification", "value": magnification, "object_mode_after": mode})
                    magnification_var.set(_format_calc(magnification))
                    result_var.set(f"Magnification = {self._format_paraxial_value(magnification)}")
                    detail_var.set(
                        "s={obj}, s'={img} from H1/H2".format(
                            obj=self._format_paraxial_value(object_principal),
                            img=self._format_paraxial_value(image_principal),
                        )
                    )
                else:
                    magnification = _read_float(magnification_var, "Magnification")
                    if abs(magnification) <= 1e-12:
                        raise RuntimeError("Magnification too close to zero; object distance goes to infinity")
                    if abs(1.0 + magnification) <= 1e-12:
                        raise RuntimeError("Magnification of -1 makes object/image distance singular")
                    object_principal = f * (1.0 + (1.0 / magnification))
                    image_principal = f * (1.0 + magnification)
                    object_distance = object_principal - h1
                    image_distance = image_principal + h2
                    mode_after = "Infinity" if (not np.isfinite(object_distance) or abs(object_distance) > 1e9) else "Finite"
                    object_distance_var.set(_format_calc(object_distance))
                    image_distance_var.set(_format_calc(image_distance))
                    solved_payload.update(
                        {
                            "target": "pair",
                            "object_value": object_distance,
                            "image_value": image_distance,
                            "object_mode_after": mode_after,
                        }
                    )
                    result_var.set(
                        f"Object={self._format_paraxial_value(object_distance)} mm, Image={self._format_paraxial_value(image_distance)} mm"
                    )
                    detail_var.set(
                        "From m={mag}: s={obj}, s'={img}".format(
                            mag=self._format_paraxial_value(magnification),
                            obj=self._format_paraxial_value(object_principal),
                            img=self._format_paraxial_value(image_principal),
                        )
                    )
            except Exception as exc:
                solved_payload.clear()
                result_var.set(f"Solve failed: {self.short_error_message(exc)}")
                detail_var.set("")

        def _apply_to_layout() -> bool:
            try:
                if not solved_payload:
                    _solve()
                    if not solved_payload:
                        return False
                target = str(solved_payload.get("target", ""))
                solved_value = float(solved_payload.get("value", 0.0))
                mode_after = str(solved_payload.get("object_mode_after", self._current_object_mode()))

                if target == "image":
                    if not np.isfinite(solved_value):
                        raise RuntimeError("Solved image distance is infinity and cannot be applied")
                    row_index = max(0, len(self.rows) - 2)
                    self.rows[row_index].thickness = solved_value
                    self._select_table_row(row_index)
                elif target == "object":
                    self.object_mode_var.set(mode_after)
                    if mode_after == "Finite":
                        if not np.isfinite(solved_value):
                            raise RuntimeError("Solved object distance is infinity and cannot be applied in Finite mode")
                        self.rows[0].thickness = solved_value
                    self._select_table_row(0)
                elif target == "pair":
                    object_value = float(solved_payload.get("object_value", float("nan")))
                    image_value = float(solved_payload.get("image_value", float("nan")))
                    self.object_mode_var.set(mode_after)
                    if mode_after == "Finite":
                        if not np.isfinite(object_value):
                            raise RuntimeError("Solved object distance is infinity and cannot be applied in Finite mode")
                        self.rows[0].thickness = object_value
                    if not np.isfinite(image_value):
                        raise RuntimeError("Solved image distance is infinity and cannot be applied")
                    row_index = max(0, len(self.rows) - 2)
                    self.rows[row_index].thickness = image_value
                    self._select_table_row(row_index)
                elif target == "magnification":
                    self.status_var.set("Magnification computed. No layout cell to apply.")
                    return False
                else:
                    raise RuntimeError("No solved target to apply")

                self._normalize_special_rows()
                self._sync_table()
                self._sync_object_controls()
                self._mark_plot_update_pending()
                self.append_progress(f"Paraxial calculator applied: {result_var.get()}")
                self.status_var.set(f"{result_var.get()}  |  Click Update.")
                return True
            except Exception as exc:
                message = self.short_error_message(exc)
                self.append_debug(f"Paraxial calculator apply failed: {exc}")
                messagebox.showerror("Paraxial Calculator", message)
                self.status_var.set(f"Paraxial calculator apply failed: {message}")
                return False

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
        try:
            system = self.build_system(force_rebuild=True)
            trace = system.ParaxMatrices(self._current_wavelength())
        except Exception as exc:
            message = self.short_error_message(exc)
            messagebox.showerror("Paraxial Matrix Report", f"Could not build paraxial matrix report:\n\n{message}", parent=self.editor)
            self.status_var.set(f"Paraxial matrix report failed: {message}")
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Paraxial Matrix Report")
        window.geometry("1180x620")
        window.minsize(860, 420)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        summary = (
            f"Wavelength {float(trace.wavelength):.6g} um | "
            f"EFFL {float(trace.effl):.6g} mm | "
            f"PPA {float(trace.ppa):.6g} mm | PPP {float(trace.ppp):.6g} mm | "
            f"ABCD=[{self._matrix_cell(trace.system_matrix_abcd, 0, 0):.6g}, "
            f"{self._matrix_cell(trace.system_matrix_abcd, 0, 1):.6g}; "
            f"{self._matrix_cell(trace.system_matrix_abcd, 1, 0):.6g}, "
            f"{self._matrix_cell(trace.system_matrix_abcd, 1, 1):.6g}]"
        )
        ttk.Label(window, text=summary, padding=(8, 8, 8, 4), anchor="w").grid(row=0, column=0, sticky="ew")

        toolbar = ttk.Frame(window, padding=(8, 0, 8, 4))
        toolbar.grid(row=1, column=0, sticky="ew")

        columns = (
            "surface",
            "name",
            "glass",
            "n_before",
            "n_after",
            "radius",
            "curvature",
            "thickness",
            "kind",
            "A",
            "B",
            "C",
            "D",
            "K00",
            "K01",
            "K10",
            "K11",
        )
        frame = ttk.Frame(window, padding=8)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        headings = {
            "surface": "Surf",
            "name": "Name",
            "glass": "Glass",
            "n_before": "n0",
            "n_after": "n1",
            "radius": "R [mm]",
            "curvature": "C [1/mm]",
            "thickness": "T [mm]",
            "kind": "Kind",
            "A": "A",
            "B": "B",
            "C": "C",
            "D": "D",
            "K00": "K00",
            "K01": "K01",
            "K10": "K10",
            "K11": "K11",
        }
        for column in columns:
            tree.heading(column, text=headings[column])
            width = 70 if column not in {"name", "kind"} else 150
            tree.column(column, width=width, anchor=("w" if column in {"name", "glass", "kind"} else "e"), stretch=column in {"name", "kind"})
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        def _fmt(value) -> str:
            try:
                return f"{float(value):.8g}"
            except Exception:
                return str(value)

        export_rows: list[dict[str, object]] = []
        for surface in trace.surfaces:
            row = {
                "surface": int(surface.surface_index),
                "name": str(surface.surface_name or ""),
                "glass": str(surface.glass),
                "n_before": float(surface.n_before),
                "n_after": float(surface.n_after),
                "radius": float(surface.radius),
                "curvature": float(surface.curvature),
                "thickness": float(surface.thickness),
                "kind": "mirror" if surface.is_mirror else ("thin_lens" if surface.is_thin_lens else "surface"),
                "A": self._matrix_cell(surface.abcd_matrix, 0, 0),
                "B": self._matrix_cell(surface.abcd_matrix, 0, 1),
                "C": self._matrix_cell(surface.abcd_matrix, 1, 0),
                "D": self._matrix_cell(surface.abcd_matrix, 1, 1),
                "K00": self._matrix_cell(surface.kraken_matrix, 0, 0),
                "K01": self._matrix_cell(surface.kraken_matrix, 0, 1),
                "K10": self._matrix_cell(surface.kraken_matrix, 1, 0),
                "K11": self._matrix_cell(surface.kraken_matrix, 1, 1),
            }
            export_rows.append(row)
            tree.insert("", "end", values=tuple(_fmt(row[column]) if column not in {"name", "glass", "kind"} else row[column] for column in columns))

        def export_csv() -> None:
            path = filedialog.asksaveasfilename(
                title="Export Paraxial Matrix CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*")],
                parent=window,
            )
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(columns))
                writer.writeheader()
                writer.writerows(export_rows)
            self.status_var.set(f"Paraxial matrix CSV exported: {Path(path).name}")

        ttk.Button(toolbar, text="Export CSV", command=export_csv).pack(side="left")
        ttk.Button(toolbar, text="Close", command=window.destroy).pack(side="left", padx=(6, 0))

        self._show_centered_dialog(window)


    def open_gaussian_beam_report(self) -> None:
        try:
            system = self.build_system(force_rebuild=True)
            wavelength = self._current_wavelength()
            paraxial_trace = system.ParaxMatrices(wavelength)
            source_beam = self._current_gaussian_beam_input(wavelength) if self._current_source_model() == "Gaussian beam" else None
        except Exception as exc:
            message = self.short_error_message(exc)
            messagebox.showerror("Gaussian Beam Report", f"Could not build Gaussian beam report:\n\n{message}", parent=self.editor)
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
        ttk.Label(window, textvariable=summary_var, padding=(8, 8, 8, 4), anchor="w").grid(row=0, column=0, sticky="ew")

        controls = ttk.LabelFrame(window, text="Input beam", padding=8)
        controls.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        for column in range(10):
            controls.columnconfigure(column, weight=1 if column % 2 else 0)

        wavelength_var = tk.StringVar(master=window, value=f"{float(wavelength):.6g}")
        waist_var = tk.StringVar(master=window, value=f"{float(source_beam.waist_radius_mm):.6g}" if source_beam is not None else "1.0")
        offset_var = tk.StringVar(master=window, value=f"{float(source_beam.waist_offset_mm):.6g}" if source_beam is not None else "0.0")
        m2_var = tk.StringVar(master=window, value=f"{float(source_beam.m2):.6g}" if source_beam is not None else "1.0")

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

        columns = (
            "step",
            "surface",
            "name",
            "kind",
            "n",
            "A",
            "B",
            "C",
            "D",
            "q_real",
            "q_imag",
            "w_radius",
            "w_diameter",
            "R",
            "waist_radius",
            "waist_offset",
            "z_rayleigh",
            "divergence_mrad",
            "gouy_rad",
            "stable",
        )
        frame = ttk.Frame(window, padding=8)
        frame.grid(row=3, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        headings = {
            "step": "Step",
            "surface": "Surf",
            "name": "Name",
            "kind": "Kind",
            "n": "n",
            "A": "A",
            "B": "B",
            "C": "C",
            "D": "D",
            "q_real": "Re(q) [mm]",
            "q_imag": "Im(q) [mm]",
            "w_radius": "w [mm]",
            "w_diameter": "2w [mm]",
            "R": "Rwf [mm]",
            "waist_radius": "w0 [mm]",
            "waist_offset": "Waist offset [mm]",
            "z_rayleigh": "zR [mm]",
            "divergence_mrad": "Div [mrad]",
            "gouy_rad": "Gouy [rad]",
            "stable": "Stable",
        }
        for column in columns:
            tree.heading(column, text=headings[column])
            width = 76
            if column in {"name"}:
                width = 150
            elif column in {"kind"}:
                width = 105
            elif column in {"q_real", "q_imag", "waist_offset", "divergence_mrad"}:
                width = 110
            tree.column(column, width=width, anchor=("w" if column in {"name", "kind"} else "e"), stretch=column in {"name", "kind"})
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        export_rows: list[dict[str, object]] = []

        def _fmt(value) -> str:
            try:
                numeric = float(value)
            except Exception:
                return str(value)
            if np.isposinf(numeric):
                return "inf"
            if np.isneginf(numeric):
                return "-inf"
            if not np.isfinite(numeric):
                return "-"
            return f"{numeric:.8g}"

        def recompute() -> None:
            nonlocal paraxial_trace
            try:
                input_beam = Kos.GaussianBeamInput(
                    wavelength_um=float(wavelength_var.get()),
                    waist_radius_mm=float(waist_var.get()),
                    waist_offset_mm=float(offset_var.get()),
                    m2=float(m2_var.get()),
                )
                if abs(float(input_beam.wavelength_um) - float(paraxial_trace.wavelength)) > 1e-15:
                    paraxial_trace = system.ParaxMatrices(float(input_beam.wavelength_um))
                beam_trace = Kos.propagate_gaussian_beam(paraxial_trace, input_beam)
            except Exception as exc:
                message = self.short_error_message(exc)
                summary_var.set(f"Gaussian beam report failed: {message}")
                self.status_var.set(f"Gaussian beam report failed: {message}")
                return

            children = tree.get_children()
            if children:
                tree.delete(*children)
            export_rows.clear()
            for step in beam_trace.steps:
                row = {
                    "step": step.step_index,
                    "surface": step.surface_index,
                    "name": step.surface_name,
                    "kind": step.kind,
                    "n": step.n_after,
                    "A": step.A,
                    "B": step.B,
                    "C": step.C,
                    "D": step.D,
                    "q_real": step.q_real_mm,
                    "q_imag": step.q_imag_mm,
                    "w_radius": step.beam_radius_mm,
                    "w_diameter": step.beam_diameter_mm,
                    "R": step.wavefront_radius_mm,
                    "waist_radius": step.waist_radius_mm,
                    "waist_offset": step.waist_offset_mm,
                    "z_rayleigh": step.rayleigh_range_mm,
                    "divergence_mrad": step.divergence_mrad,
                    "gouy_rad": step.gouy_phase_rad,
                    "stable": step.stable,
                }
                export_rows.append(row)
                tree.insert(
                    "",
                    "end",
                    values=tuple(row[column] if column in {"name", "kind", "stable"} else _fmt(row[column]) for column in columns),
                )
            final = beam_trace.final
            if final is None:
                summary_var.set("No paraxial steps available.")
            else:
                summary_var.set(
                    "Gaussian beam | lambda={wl:.6g} um | input w0={w0:.6g} mm | M2={m2:.6g} | "
                    "final w={wf} mm | final waist offset={offset} mm | final zR={zr} mm".format(
                        wl=float(input_beam.wavelength_um),
                        w0=float(input_beam.waist_radius_mm),
                        m2=float(input_beam.m2),
                        wf=_fmt(final.beam_radius_mm),
                        offset=_fmt(final.waist_offset_mm),
                        zr=_fmt(final.rayleigh_range_mm),
                    )
                )
            self.status_var.set("Gaussian beam report refreshed.")

        def export_csv() -> None:
            if not export_rows:
                recompute()
            if not export_rows:
                return
            path = filedialog.asksaveasfilename(
                title="Export Gaussian Beam CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*")],
                parent=window,
            )
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(columns))
                writer.writeheader()
                writer.writerows(export_rows)
            self.status_var.set(f"Gaussian beam CSV exported: {Path(path).name}")

        def apply_cavity_eigenmode() -> None:
            nonlocal paraxial_trace
            try:
                wavelength_value = float(wavelength_var.get())
                if abs(wavelength_value - float(paraxial_trace.wavelength)) > 1e-15:
                    paraxial_trace = system.ParaxMatrices(wavelength_value)
                eigenmode = Kos.solve_gaussian_cavity_eigenmode(
                    paraxial_trace,
                    wavelength_um=wavelength_value,
                    m2=float(m2_var.get()),
                )
                if not eigenmode.stable:
                    message = (
                        f"Cavity eigenmode unavailable: {eigenmode.message}; "
                        f"g={_fmt(eigenmode.stability_parameter)}"
                    )
                    cavity_status_var.set(message)
                    self.status_var.set(message)
                    return
                waist_var.set(_fmt(eigenmode.waist_radius_mm))
                offset_var.set(_fmt(eigenmode.q_real_mm))
                cavity_status_var.set(
                    "Cavity eigenmode applied: "
                    f"q={_fmt(eigenmode.q_real_mm)}+i{_fmt(eigenmode.q_imag_mm)} mm, "
                    f"w0={_fmt(eigenmode.waist_radius_mm)} mm, "
                    f"g={_fmt(eigenmode.stability_parameter)}, "
                    f"Gouy/RT={_fmt(eigenmode.round_trip_gouy_rad)} rad."
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
