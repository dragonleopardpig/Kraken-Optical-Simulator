"""Diffuse / BRDF scatter settings dialog for the main layout editor."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable


class MainDiffuseScatterDialog:
    """Build the Diffuse / BRDF dialog while keeping row state on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        diffuse_object_surface: str,
        diffuse_scatter_advanced_attr: str,
        diffuse_scatter_default_settings: dict[str, object],
        normalize_diffuse_scatter_settings: Callable[[object], dict[str, object]],
        validate_diffuse_scatter_settings: Callable[[dict[str, object]], list[str]],
        pyscatmech_status: Callable[[], dict[str, object]],
        format_pyscatmech_parameters: Callable[[object], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "diffuse_object_surface", diffuse_object_surface)
        object.__setattr__(self, "diffuse_scatter_advanced_attr", diffuse_scatter_advanced_attr)
        object.__setattr__(self, "diffuse_scatter_default_settings", dict(diffuse_scatter_default_settings))
        object.__setattr__(self, "normalize_diffuse_scatter_settings", normalize_diffuse_scatter_settings)
        object.__setattr__(self, "validate_diffuse_scatter_settings", validate_diffuse_scatter_settings)
        object.__setattr__(self, "pyscatmech_status", pyscatmech_status)
        object.__setattr__(self, "format_pyscatmech_parameters", format_pyscatmech_parameters)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "diffuse_object_surface",
            "diffuse_scatter_advanced_attr",
            "diffuse_scatter_default_settings",
            "normalize_diffuse_scatter_settings",
            "validate_diffuse_scatter_settings",
            "pyscatmech_status",
            "format_pyscatmech_parameters",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open(self, row_index: int | None = None) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Diffuse / BRDF", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return

        if row_index is None:
            row_index = self._selected_surface_row_index()
        if row_index is None or row_index < 0 or row_index >= len(self.rows):
            messagebox.showinfo("Diffuse / BRDF", "Select a Diffuse Object row first.", parent=self.editor)
            return

        row = self.rows[row_index]
        if row.surface != self.diffuse_object_surface:
            messagebox.showinfo("Diffuse / BRDF", "Diffuse scatter settings apply only to Diffuse Object rows.", parent=self.editor)
            return

        advanced = dict(row.advanced or {})
        settings = self.normalize_diffuse_scatter_settings(advanced.get(self.diffuse_scatter_advanced_attr))
        backend_status = self.pyscatmech_status()
        backend_available = bool(backend_status.get("available"))
        backend_reason = str(backend_status.get("reason", "") or "").strip()
        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Diffuse / BRDF - S{row_index}: {row.name}")
        window.geometry("860x680")
        window.minsize(760, 600)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)

        body = ttk.Frame(window, padding=(12, 10, 12, 8))
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        ttk.Label(
            body,
            text=(
                "Built-in Lambertian, Oren-Nayar, and Cosine Lobe scattering spawn deterministic non-sequential child rays. "
                "pySCATMECH BRDF keeps the same deterministic branch layout but uses SCATMECH BRDF weights when the optional "
                "SCATPY extension is installed."
            ),
            foreground="#5f6b7a",
            wraplength=720,
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        backend_message = (
            "pySCATMECH backend is available."
            if backend_available
            else f"pySCATMECH backend is unavailable in this environment. {backend_reason}"
        )
        ttk.Label(
            body,
            text=backend_message,
            foreground=("#166534" if backend_available else "#92400e"),
            wraplength=720,
        ).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        model_var = tk.StringVar(master=window, value=str(settings["model"]))
        backend_var = tk.StringVar(master=window, value=str(settings["backend"]))
        backend_model_var = tk.StringVar(master=window, value=str(settings["backend_model"]))
        reflectance_var = tk.StringVar(master=window, value=str(settings["reflectance"]))
        sample_count_var = tk.StringVar(master=window, value=str(settings["sample_count"]))
        max_angle_var = tk.StringVar(master=window, value=str(settings["max_scatter_angle_deg"]))
        min_power_var = tk.StringVar(master=window, value=str(settings["min_branch_power"]))
        max_depth_var = tk.StringVar(master=window, value=str(settings["max_branch_depth"]))
        lobe_exponent_var = tk.StringVar(master=window, value=str(settings["lobe_exponent"]))
        roughness_var = tk.StringVar(master=window, value=str(settings["roughness_deg"]))
        backend_params_text = self.format_pyscatmech_parameters(settings.get("backend_parameters"))
        target_options = ["None"]
        for index, candidate_row in enumerate(self.rows):
            if index == row_index:
                continue
            target_options.append(f"{index}: {candidate_row.name or candidate_row.surface}")
        target_value = "None"
        if settings.get("target_surface") is not None:
            target_prefix = f"{int(settings['target_surface'])}:"
            target_value = next((option for option in target_options if option.startswith(target_prefix)), target_prefix.rstrip(":"))
        target_var = tk.StringVar(master=window, value=target_value)
        target_radius_var = tk.StringVar(master=window, value=str(settings["target_radius_scale"]))
        row_offset = 2

        rows = (
            ("Model", model_var, "Lambertian", "Lambertian is matte, Oren-Nayar is rough diffuse, and Cosine Lobe is glossy/specular-lobe scatter."),
            ("Backend", backend_var, "Built-in", "Use Built-in for dependency-free scatter, or pySCATMECH for an optional BRDF backend."),
            ("Backend model", backend_model_var, "Microroughness_BRDF_Model", "pySCATMECH only: BRDF model class name."),
            ("Reflectance", reflectance_var, "0.8", "Diffuse albedo in [0, 1]."),
            ("Scatter samples", sample_count_var, "9", "Number of deterministic child rays per hit."),
            ("Max scatter angle [deg]", max_angle_var, "90", "90 deg is the physical Lambertian hemisphere; lower values are preview cones."),
            ("Lobe exponent", lobe_exponent_var, "20", "Cosine Lobe only: higher values make a narrower glossy lobe."),
            ("Roughness [deg]", roughness_var, "20", "Oren-Nayar only: sigma roughness angle in degrees."),
            ("Min branch power", min_power_var, "1e-4", "Branches below this total power are not spawned."),
            ("Max scatter depth", max_depth_var, "2", "Maximum recursive diffuse hits per launched ray."),
            ("Guided target surface", target_var, "None", "Optional surface to importance-sample, such as a pupil, lens, detector, or Image."),
            ("Target radius scale", target_radius_var, "1.0", "Scales the selected target surface clear radius for guided sampling."),
        )
        for grid_row, (label, variable, default, hint) in enumerate(rows, start=1 + row_offset):
            ttk.Label(body, text=label).grid(row=grid_row, column=0, sticky="w", padx=(0, 8), pady=4)
            if label == "Model":
                ttk.Combobox(body, textvariable=variable, values=("Lambertian", "Oren-Nayar", "Cosine Lobe", "pySCATMECH BRDF"), state="readonly", width=28).grid(row=grid_row, column=1, sticky="w", pady=4)
            elif label == "Backend":
                ttk.Combobox(body, textvariable=variable, values=("Built-in", "pySCATMECH"), state="readonly", width=28).grid(row=grid_row, column=1, sticky="w", pady=4)
            elif label == "Guided target surface":
                ttk.Combobox(body, textvariable=variable, values=target_options, state="readonly", width=34).grid(row=grid_row, column=1, sticky="w", pady=4)
            else:
                ttk.Entry(body, textvariable=variable, width=18).grid(row=grid_row, column=1, sticky="w", pady=4)
            ttk.Label(body, text=f"Default: {default}. {hint}", foreground="#6b7280").grid(row=grid_row, column=2, sticky="w", pady=4)

        backend_params_row = len(rows) + 1 + row_offset
        ttk.Label(body, text="Backend parameters").grid(row=backend_params_row, column=0, sticky="nw", padx=(0, 8), pady=(8, 4))
        backend_params_widget = tk.Text(body, width=52, height=8, wrap="word")
        backend_params_widget.grid(row=backend_params_row, column=1, sticky="ew", pady=(8, 4))
        backend_params_widget.insert("1.0", backend_params_text)
        ttk.Label(
            body,
            text=(
                "Default: {}. pySCATMECH only: JSON or Python dict. Use __model__ for nested SCATMECH model names, "
                "for example {\"psd\": {\"__model__\": \"Gaussian_PSD_Function\", \"sigma\": 0.05, \"length\": 1.0}}."
            ),
            foreground="#6b7280",
            wraplength=320,
            justify="left",
        ).grid(row=backend_params_row, column=2, sticky="nw", pady=(8, 4))

        footer = ttk.Frame(window, padding=(12, 0, 12, 10))
        footer.grid(row=1, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        validation_var = tk.StringVar(master=window, value="Validation has not been run.")
        ttk.Label(footer, textvariable=validation_var, foreground="#5f6b7a").pack(side="left", fill="x", expand=True)

        def collect_values() -> dict[str, object]:
            candidate = {
                "model": model_var.get().strip() or "Lambertian",
                "backend": backend_var.get().strip() or "Built-in",
                "backend_model": backend_model_var.get().strip() or self.diffuse_scatter_default_settings["backend_model"],
                "backend_parameters": backend_params_widget.get("1.0", "end-1c").strip(),
                "reflectance": reflectance_var.get().strip(),
                "sample_count": sample_count_var.get().strip(),
                "max_scatter_angle_deg": max_angle_var.get().strip(),
                "min_branch_power": min_power_var.get().strip(),
                "max_branch_depth": max_depth_var.get().strip(),
                "lobe_exponent": lobe_exponent_var.get().strip(),
                "roughness_deg": roughness_var.get().strip(),
                "target_surface": target_var.get().strip(),
                "target_radius_scale": target_radius_var.get().strip(),
                "polarization": self.diffuse_scatter_default_settings["polarization"],
            }
            return self.normalize_diffuse_scatter_settings(candidate)

        def validate_values(*, show_success: bool = True) -> list[str]:
            try:
                candidate = collect_values()
            except Exception as exc:
                errors = [str(exc)]
                validation_var.set(f"Validation failed: {errors[0]}")
                return errors
            errors = self.validate_diffuse_scatter_settings(candidate)
            if errors:
                validation_var.set(f"Validation failed: {errors[0]}")
            elif show_success:
                validation_var.set("Validation passed.")
            return errors

        def apply_values() -> None:
            errors = validate_values(show_success=False)
            if errors:
                messagebox.showerror(
                    "Diffuse / BRDF Validation",
                    "Fix these values before applying:\n\n" + "\n".join(f"- {error}" for error in errors),
                    parent=window,
                )
                return
            candidate = collect_values()
            self._begin_history_capture()
            row = self.rows[row_index]
            row.surface = self.diffuse_object_surface
            row.glass = "MIRROR"
            advanced = dict(row.advanced or {})
            advanced[self.diffuse_scatter_advanced_attr] = candidate
            row.advanced = advanced
            self._sync_table()
            self._select_table_row(row_index)
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Updated Diffuse Object settings on S{row_index}. Click Update to trace.")
            window.destroy()

        ttk.Button(footer, text="Validate", command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
