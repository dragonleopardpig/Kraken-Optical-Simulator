"""Surface shape, UDA, mask, and optical solid builder dialog."""

from __future__ import annotations

from pathlib import Path
from pprint import pformat
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle


class MainSurfaceShapeBuilderDialog:
    """Build the Surface Shape Builder while keeping row state on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        attachment_dir: Path,
        project_root: Path,
        optical_solid_filetypes: tuple[tuple[str, str], ...],
        encode_custom_surface_value: Callable[[object], object],
        parse_literal_editor_text: Callable[[str], object],
        validate_advanced_surface_inputs: Callable[[dict[str, object], object, object], tuple[list[str], list[str]]],
        optical_solid_mesh_path_from_source: Callable[[Path], tuple[Path, Path | None, str | None]],
        short_error_message: Callable[[BaseException], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "attachment_dir", Path(attachment_dir))
        object.__setattr__(self, "project_root", Path(project_root))
        object.__setattr__(self, "optical_solid_filetypes", tuple(optical_solid_filetypes))
        object.__setattr__(self, "encode_custom_surface_value", encode_custom_surface_value)
        object.__setattr__(self, "parse_literal_editor_text", parse_literal_editor_text)
        object.__setattr__(self, "validate_advanced_surface_inputs", validate_advanced_surface_inputs)
        object.__setattr__(self, "optical_solid_mesh_path_from_source", optical_solid_mesh_path_from_source)
        object.__setattr__(self, "short_error_message", short_error_message)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "attachment_dir",
            "project_root",
            "optical_solid_filetypes",
            "encode_custom_surface_value",
            "parse_literal_editor_text",
            "validate_advanced_surface_inputs",
            "optical_solid_mesh_path_from_source",
            "short_error_message",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open(self, row_index: int | None = None) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Surface Shape Builder", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return

        if row_index is None:
            row_index = self._selected_surface_row_index()
        if row_index is None or row_index < 0 or row_index >= len(self.rows):
            messagebox.showinfo("Surface Shape Builder", "Select a surface row first.", parent=self.editor)
            return
        row = self.rows[row_index]
        if row.surface in {"Object", "Image"}:
            messagebox.showinfo("Surface Shape Builder", "Shape builders apply to physical surfaces, not Object/Image rows.", parent=self.editor)
            return

        advanced = dict(row.advanced or {})
        candidate_extra = row.extra_data
        candidate_uda = row.uda
        candidate_advanced = dict(advanced)

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Surface Shape Builder - S{row_index}: {row.name}")
        window.geometry("1180x760")
        window.minsize(920, 620)
        window.transient(self.editor)
        window.columnconfigure(1, weight=1)
        window.rowconfigure(0, weight=1)

        controls = ttk.Frame(window, padding=10)
        controls.grid(row=0, column=0, sticky="nsw")
        controls.columnconfigure(1, weight=1)

        figure = Figure(figsize=(7.2, 5.4), dpi=100)
        sag_ax = figure.add_subplot(121)
        aperture_ax = figure.add_subplot(122)
        canvas = FigureCanvasTkAgg(figure, master=window)
        canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)

        row_cursor = 0
        ttk.Label(controls, text=f"S{row_index}: {row.name or row.surface}", font=("TkDefaultFont", 10, "bold")).grid(
            row=row_cursor, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        row_cursor += 1

        ttk.Label(controls, text="Asphere coeffs").grid(row=row_cursor, column=0, sticky="w", pady=3)
        aspher_var = tk.StringVar(master=window, value=self._short_numeric_list(candidate_advanced.get("AspherData", []), 12))
        ttk.Entry(controls, textvariable=aspher_var, width=34).grid(row=row_cursor, column=1, columnspan=2, sticky="ew", pady=3)
        row_cursor += 1

        ttk.Label(controls, text="Zernike coeffs").grid(row=row_cursor, column=0, sticky="w", pady=3)
        znk_var = tk.StringVar(master=window, value=self._short_numeric_list(candidate_advanced.get("ZNK", []), 12))
        ttk.Entry(controls, textvariable=znk_var, width=34).grid(row=row_cursor, column=1, columnspan=2, sticky="ew", pady=3)
        row_cursor += 1

        ttk.Separator(controls).grid(row=row_cursor, column=0, columnspan=3, sticky="ew", pady=8)
        row_cursor += 1

        ttk.Label(controls, text="ExtraData preset").grid(row=row_cursor, column=0, sticky="w", pady=3)
        extra_preset_var = tk.StringVar(master=window, value="None")
        extra_menu = ttk.Combobox(
            controls,
            textvariable=extra_preset_var,
            state="readonly",
            values=("None", "xy_cosines", "radial_sine", "micro_lens_array"),
            width=18,
        )
        extra_menu.grid(row=row_cursor, column=1, sticky="ew", pady=3)
        row_cursor += 1
        ttk.Label(controls, text="Extra params").grid(row=row_cursor, column=0, sticky="w", pady=3)
        extra_params_var = tk.StringVar(master=window, value="[8.0, 0.02]")
        ttk.Entry(controls, textvariable=extra_params_var, width=24).grid(row=row_cursor, column=1, columnspan=2, sticky="ew", pady=3)
        row_cursor += 1

        encoded_extra = self.encode_custom_surface_value(candidate_extra)
        if isinstance(encoded_extra, dict):
            preset = str(encoded_extra.get("preset", "")).strip()
            if preset:
                extra_preset_var.set(preset)
                extra_params_var.set(pformat(encoded_extra.get("params", []), width=80))

        ttk.Separator(controls).grid(row=row_cursor, column=0, columnspan=3, sticky="ew", pady=8)
        row_cursor += 1

        ttk.Label(controls, text="UDA preset").grid(row=row_cursor, column=0, sticky="w", pady=3)
        uda_preset_var = tk.StringVar(master=window, value="Current" if not self._is_default_uda(candidate_uda) else "None")
        ttk.Combobox(
            controls,
            textvariable=uda_preset_var,
            state="readonly",
            values=("Current", "None", "Circle", "Hexagon", "Square"),
            width=18,
        ).grid(row=row_cursor, column=1, sticky="ew", pady=3)
        row_cursor += 1
        ttk.Label(controls, text="UDA radius").grid(row=row_cursor, column=0, sticky="w", pady=3)
        uda_radius_var = tk.StringVar(master=window, value=f"{max(float(row.diameter) * 0.45, 1.0):.6g}")
        ttk.Entry(controls, textvariable=uda_radius_var, width=14).grid(row=row_cursor, column=1, sticky="ew", pady=3)
        row_cursor += 1
        ttk.Label(controls, text="UDA rotation").grid(row=row_cursor, column=0, sticky="w", pady=3)
        uda_rotation_var = tk.StringVar(master=window, value="0.0")
        ttk.Entry(controls, textvariable=uda_rotation_var, width=14).grid(row=row_cursor, column=1, sticky="ew", pady=3)
        row_cursor += 1

        ttk.Separator(controls).grid(row=row_cursor, column=0, columnspan=3, sticky="ew", pady=8)
        row_cursor += 1

        ttk.Label(controls, text="Mask preset").grid(row=row_cursor, column=0, sticky="w", pady=3)
        mask_summary = self._mask_preset_summary(candidate_advanced.get("Mask_Shape"))
        mask_preset_var = tk.StringVar(master=window, value=mask_summary if mask_summary in {"Ronchi mask", "Spider mask"} else "None")
        ttk.Combobox(
            controls,
            textvariable=mask_preset_var,
            state="readonly",
            values=("None", "Ronchi mask", "Spider mask"),
            width=18,
        ).grid(row=row_cursor, column=1, sticky="ew", pady=3)
        row_cursor += 1
        ttk.Label(controls, text="Mask pitch/width").grid(row=row_cursor, column=0, sticky="w", pady=3)
        mask_pitch_var = tk.StringVar(master=window, value=f"{max(float(row.diameter) / 20.0, 0.25):.6g}")
        ttk.Entry(controls, textvariable=mask_pitch_var, width=14).grid(row=row_cursor, column=1, sticky="ew", pady=3)
        row_cursor += 1
        ttk.Label(controls, text="Mask extent").grid(row=row_cursor, column=0, sticky="w", pady=3)
        mask_extent_var = tk.StringVar(master=window, value=f"{max(float(row.diameter) * 1.1, 1.0):.6g}")
        ttk.Entry(controls, textvariable=mask_extent_var, width=14).grid(row=row_cursor, column=1, sticky="ew", pady=3)
        row_cursor += 1

        ttk.Separator(controls).grid(row=row_cursor, column=0, columnspan=3, sticky="ew", pady=8)
        row_cursor += 1

        ttk.Label(controls, text="Optical CAD/STL").grid(row=row_cursor, column=0, sticky="w", pady=3)
        solid_display_value = candidate_advanced.get("OpticalSolidSourcePath") or candidate_advanced.get("Solid_3d_stl")
        stl_var = tk.StringVar(master=window, value=str(solid_display_value) if solid_display_value not in (None, "None") else "")
        ttk.Entry(controls, textvariable=stl_var, width=28).grid(row=row_cursor, column=1, sticky="ew", pady=3)

        def browse_stl() -> None:
            path = filedialog.askopenfilename(
                title="Import Optical CAD/STL",
                initialdir=str(self.attachment_dir if self.attachment_dir.exists() else self.project_root),
                filetypes=self.optical_solid_filetypes,
                parent=window,
            )
            if path:
                stl_var.set(path)
                status_var.set("Optical solid path staged. STEP/IGES will be meshed to cached STL on Apply.")
                refresh_preview()

        ttk.Button(controls, text="Browse", command=browse_stl).grid(row=row_cursor, column=2, sticky="ew", padx=(6, 0), pady=3)
        row_cursor += 1

        status_var = tk.StringVar(master=window, value="Preview shows sag/custom surface and aperture/UDA/mask footprint.")
        ttk.Label(controls, textvariable=status_var, foreground="#475569", wraplength=330, justify="left").grid(
            row=row_cursor, column=0, columnspan=3, sticky="ew", pady=(10, 0)
        )
        row_cursor += 1

        def parse_list(text: str, label: str) -> list[float] | None:
            stripped = text.strip()
            if not stripped:
                return None
            value = self.parse_literal_editor_text(stripped)
            try:
                arr = np.asarray(value, dtype=float).ravel()
            except Exception as exc:
                raise ValueError(f"{label} must be a numeric list: {exc}") from exc
            if arr.size == 0:
                return None
            if not np.all(np.isfinite(arr)):
                raise ValueError(f"{label} contains non-finite values")
            return arr.tolist()

        def collect_candidate() -> tuple[dict[str, object], object, object]:
            next_advanced = dict(candidate_advanced)
            aspher = parse_list(aspher_var.get(), "Asphere coefficients")
            znk = parse_list(znk_var.get(), "Zernike coefficients")
            if aspher:
                next_advanced["AspherData"] = aspher
            else:
                next_advanced.pop("AspherData", None)
            if znk:
                next_advanced["ZNK"] = znk
            else:
                next_advanced.pop("ZNK", None)

            preset = extra_preset_var.get().strip()
            if preset == "None":
                next_extra = 0.0
            else:
                params = self.parse_literal_editor_text(extra_params_var.get())
                next_extra = {"kind": "extra_surface", "preset": preset, "params": params}

            uda_preset = uda_preset_var.get().strip()
            if uda_preset == "Current":
                next_uda = candidate_uda
            elif uda_preset == "None":
                next_uda = "None"
            else:
                radius = float(uda_radius_var.get().strip() or "1.0")
                rotation = float(uda_rotation_var.get().strip() or "0.0")
                sides = {"Circle": 48, "Hexagon": 6, "Square": 4}[uda_preset]
                next_uda = {"kind": "regular_polygon", "radius": radius, "sides": sides, "rotation_deg": rotation}

            mask_preset = mask_preset_var.get().strip()
            if mask_preset == "None":
                next_advanced.pop("Mask_Shape", None)
                next_advanced.pop("Mask_Type", None)
            else:
                extent = float(mask_extent_var.get().strip() or max(float(row.diameter), 1.0))
                pitch = float(mask_pitch_var.get().strip() or max(float(row.diameter) / 20.0, 0.25))
                if mask_preset == "Ronchi mask":
                    next_advanced["Mask_Shape"] = {
                        "kind": "mask_shape",
                        "preset": "ronchi",
                        "period": pitch,
                        "duty_cycle": 0.5,
                        "extent": extent,
                    }
                else:
                    next_advanced["Mask_Shape"] = {
                        "kind": "mask_shape",
                        "preset": "spider",
                        "arms": 4,
                        "arm_width": pitch,
                        "hub_radius": max(pitch * 1.5, extent * 0.04),
                        "extent": extent,
                    }
                next_advanced["Mask_Type"] = 2

            stl_text = stl_var.get().strip()
            if stl_text:
                next_advanced["Solid_3d_stl"] = stl_text
                next_advanced.pop("OpticalSolidSourcePath", None)
                next_advanced.pop("OpticalSolidSourceFormat", None)
            else:
                next_advanced.pop("Solid_3d_stl", None)
                next_advanced.pop("OpticalSolidSourcePath", None)
                next_advanced.pop("OpticalSolidSourceFormat", None)
            return next_advanced, next_extra, next_uda

        def draw_aperture_overlay(axis, next_advanced: dict[str, object], next_uda) -> None:
            radius = max(float(row.diameter) * 0.5, 1.0)
            circle = np.linspace(0.0, 2.0 * np.pi, 240)
            axis.plot(radius * np.cos(circle), radius * np.sin(circle), color="#334155", lw=1.2, label="Diameter")
            polygon = self._decoded_uda_polygon(next_uda)
            if polygon is not None:
                px, py = polygon
                axis.plot(px, py, color="#0f766e", lw=2.0, label="UDA")
                axis.fill(px, py, color="#0f766e", alpha=0.12)
            mask_value = next_advanced.get("Mask_Shape")
            if isinstance(mask_value, dict):
                preset = str(mask_value.get("preset", "")).strip().lower()
                extent = max(float(mask_value.get("extent", row.diameter)), 1.0)
                if preset == "ronchi":
                    period = max(float(mask_value.get("period", extent / 20.0)), 1e-6)
                    width = period * float(mask_value.get("duty_cycle", 0.5))
                    for x_pos in np.arange(-0.5 * extent, 0.5 * extent + period, period):
                        axis.add_patch(Rectangle((x_pos - 0.5 * width, -0.5 * extent), width, extent, color="#dc2626", alpha=0.18))
                elif preset == "spider":
                    arms = max(int(mask_value.get("arms", 4)), 1)
                    width = max(float(mask_value.get("arm_width", extent * 0.035)), 1e-6)
                    for index in range(arms):
                        angle = float(index) * np.pi / max(float(arms), 1.0)
                        dx = np.cos(angle) * 0.5 * extent
                        dy = np.sin(angle) * 0.5 * extent
                        axis.plot([-dx, dx], [-dy, dy], color="#dc2626", lw=max(width, 1.0), alpha=0.45)
            axis.set_aspect("equal", adjustable="box")
            axis.set_title("Aperture / UDA / Mask")
            axis.set_xlabel("X [mm]")
            axis.set_ylabel("Y [mm]")
            axis.grid(True, alpha=0.2)
            axis.legend(loc="upper right", fontsize=8)

        def refresh_preview() -> None:
            try:
                next_advanced, next_extra, next_uda = collect_candidate()
                errors, warnings_out = self.validate_advanced_surface_inputs(next_advanced, next_extra, next_uda)
                for extra_axis in list(figure.axes):
                    if extra_axis not in {sag_ax, aperture_ax}:
                        figure.delaxes(extra_axis)
                sag_ax.clear()
                aperture_ax.clear()
                x_grid, y_grid, sag, inside = self._surface_preview_grid(row, next_advanced, next_extra)
                finite = sag[np.isfinite(sag) & inside]
                if finite.size:
                    image = sag_ax.imshow(
                        sag,
                        extent=[float(np.nanmin(x_grid)), float(np.nanmax(x_grid)), float(np.nanmin(y_grid)), float(np.nanmax(y_grid))],
                        origin="lower",
                        cmap="viridis",
                    )
                    figure.colorbar(image, ax=sag_ax, fraction=0.046, pad=0.04, label="Sag / departure [mm]")
                else:
                    sag_ax.text(0.5, 0.5, "No finite sag data", transform=sag_ax.transAxes, ha="center", va="center")
                sag_ax.set_title("Sag + Asphere/Zernike/ExtraData")
                sag_ax.set_xlabel("X [mm]")
                sag_ax.set_ylabel("Y [mm]")
                draw_aperture_overlay(aperture_ax, next_advanced, next_uda)
                if errors:
                    status_var.set(f"Validation failed: {errors[0]}")
                elif warnings_out:
                    status_var.set(f"Validation warning: {warnings_out[0]}")
                else:
                    stl_note = " Optical solid path staged." if next_advanced.get("Solid_3d_stl") else ""
                    status_var.set(f"Preview OK.{stl_note} Click Apply to store values on this surface.")
                canvas.draw_idle()
            except Exception as exc:
                status_var.set(f"Preview failed: {self.short_error_message(exc)}")

        def apply_values() -> None:
            try:
                next_advanced, next_extra, next_uda = collect_candidate()
                errors, warnings_out = self.validate_advanced_surface_inputs(next_advanced, next_extra, next_uda)
                stl_text = str(next_advanced.get("Solid_3d_stl", "") or "").strip()
                if stl_text:
                    try:
                        mesh_path, source_path, source_format = self.optical_solid_mesh_path_from_source(Path(stl_text))
                        next_advanced["Solid_3d_stl"] = str(mesh_path)
                        if source_path is not None:
                            next_advanced["OpticalSolidSourcePath"] = str(source_path)
                            next_advanced["OpticalSolidSourceFormat"] = source_format
                        else:
                            next_advanced.pop("OpticalSolidSourcePath", None)
                            next_advanced.pop("OpticalSolidSourceFormat", None)
                    except Exception as exc:
                        errors.append(f"Optical solid import failed: {self.short_error_message(exc)}")
            except Exception as exc:
                messagebox.showerror("Surface Shape Builder", str(exc), parent=window)
                return
            if errors:
                messagebox.showerror(
                    "Surface Shape Builder",
                    "Fix these values before applying:\n\n" + "\n".join(f"- {error}" for error in errors),
                    parent=window,
                )
                return
            if warnings_out:
                self.append_debug("Surface shape builder warnings: " + " | ".join(warnings_out))
            self._begin_history_capture()
            self.rows[row_index].advanced = next_advanced
            self.rows[row_index].extra_data = next_extra
            self.rows[row_index].uda = next_uda
            self._sync_table()
            self._select_table_row(row_index)
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Updated shape/custom/mask settings for S{row_index}: {self.rows[row_index].name}. Click Update.")
            window.destroy()

        button_frame = ttk.Frame(controls)
        button_frame.grid(row=row_cursor, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(button_frame, text="Refresh Preview", command=refresh_preview).pack(side="left")
        ttk.Button(button_frame, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(button_frame, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))

        for variable in (
            aspher_var,
            znk_var,
            extra_preset_var,
            extra_params_var,
            uda_preset_var,
            uda_radius_var,
            uda_rotation_var,
            mask_preset_var,
            mask_pitch_var,
            mask_extent_var,
            stl_var,
        ):
            try:
                variable.trace_add("write", lambda *_args: window.after_idle(refresh_preview))
            except Exception:
                pass
        refresh_preview()
        self._show_centered_dialog(window)
