"""Path component placement dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

import numpy as np


def _layout_constants():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class MainPathComponentPlacementDialog:
    """Own path-component placement dialogs while delegating geometry to the editor."""

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

    def open_arm_path_component_placement(
        self,
        splitter_index: int,
        arm_role: str,
        *,
        default_component: object | None = None,
        branch_path: str = "",
    ) -> None:
        le = _layout_constants()
        if default_component is None:
            default_component = le.PATH_COMPONENT_DETECTOR
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Path Component", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return
        path = str(branch_path or "").strip()
        traced_path_mode = bool(path)
        if traced_path_mode:
            try:
                self._branch_path_frame(path)
            except Exception as exc:
                messagebox.showinfo("Path Component", self.short_error_message(exc), parent=self.editor)
                return
            role = "Path"
            path_detail = self._branch_path_detail(path)
            title = "Add Traced Path Component"
            default_diameter = 25.0
            description = (
                f"Insert a component on traced path {self._branch_path_compact_detail(path)}. "
                "The editor derives the global Tilt/Decenter pose from the latest traced BRANCH_PATH segment "
                "and preserves exact branch_path metadata for nested splitter filtering."
            )
            initial_status = f"Distance is measured from the last splitter hit in: {path_detail}"
        else:
            if not (0 <= splitter_index < len(self.rows)) or self.rows[splitter_index].surface != le.BEAM_SPLITTER_SURFACE:
                messagebox.showinfo("Path Component", "Right-click a Beam Splitter row first.", parent=self.editor)
                return
            role = str(arm_role).strip()
            if role not in {"Transmit", "Reflect"}:
                messagebox.showerror("Path Component", f"Unsupported path: {arm_role}", parent=self.editor)
                return
            title = f"Add {role} Path Component"
            default_diameter = max(float(self.rows[splitter_index].diameter) * 2.0, 25.0)
            description = (
                f"Insert a component in the {role.lower()} path. The editor calculates the "
                "global Tilt/Decenter pose from the splitter path frame and preserves path metadata."
            )
            initial_status = "Distance is measured along the central transmitted/reflected path."

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(title)
        window.transient(self.editor)
        frame = ttk.Frame(window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        component_var = tk.StringVar(master=window, value=self._normalize_path_component_type(default_component))
        distance_var = tk.StringVar(master=window, value="60")
        diameter_var = tk.StringVar(
            master=window,
            value=self._format_table_float(default_diameter),
        )
        parameter_var = tk.StringVar(master=window, value="0")
        glass_var = tk.StringVar(master=window, value="BK7")
        local_decenter_x_var = tk.StringVar(master=window, value="0")
        local_decenter_y_var = tk.StringVar(master=window, value="0")
        local_tilt_x_var = tk.StringVar(master=window, value="0")
        local_tilt_y_var = tk.StringVar(master=window, value="0")
        local_tilt_z_var = tk.StringVar(master=window, value="0")
        parameter_label_var = tk.StringVar(master=window, value="")
        glass_label_var = tk.StringVar(master=window, value="Glass")
        ttk.Label(
            frame,
            text=description,
            wraplength=460,
            foreground="#475569",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(frame, text="Component").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=3)
        component_menu = ttk.Combobox(
            frame,
            textvariable=component_var,
            values=le.PATH_COMPONENT_TYPES,
            state="readonly",
            width=24,
        )
        component_menu.grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Label(frame, text="Distance from splitter [mm]").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(frame, textvariable=distance_var, width=16).grid(row=2, column=1, sticky="ew", pady=3)
        ttk.Label(frame, text="Clear diameter [mm]").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(frame, textvariable=diameter_var, width=16).grid(row=3, column=1, sticky="ew", pady=3)
        ttk.Label(frame, textvariable=parameter_label_var).grid(row=4, column=0, sticky="w", padx=(0, 10), pady=3)
        parameter_entry = ttk.Entry(frame, textvariable=parameter_var, width=16)
        parameter_entry.grid(row=4, column=1, sticky="ew", pady=3)
        ttk.Label(frame, textvariable=glass_label_var).grid(row=5, column=0, sticky="w", padx=(0, 10), pady=3)
        glass_entry = ttk.Entry(frame, textvariable=glass_var, width=16)
        glass_entry.grid(row=5, column=1, sticky="ew", pady=3)
        ttk.Label(frame, text="Local X offset [mm]").grid(row=6, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(frame, textvariable=local_decenter_x_var, width=16).grid(row=6, column=1, sticky="ew", pady=3)
        ttk.Label(frame, text="Local Y offset [mm]").grid(row=7, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(frame, textvariable=local_decenter_y_var, width=16).grid(row=7, column=1, sticky="ew", pady=3)
        ttk.Label(frame, text="Local tilt X [deg]").grid(row=8, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(frame, textvariable=local_tilt_x_var, width=16).grid(row=8, column=1, sticky="ew", pady=3)
        ttk.Label(frame, text="Local tilt Y [deg]").grid(row=9, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(frame, textvariable=local_tilt_y_var, width=16).grid(row=9, column=1, sticky="ew", pady=3)
        ttk.Label(frame, text="Local tilt Z [deg]").grid(row=10, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(frame, textvariable=local_tilt_z_var, width=16).grid(row=10, column=1, sticky="ew", pady=3)
        status_var = tk.StringVar(
            master=window,
            value=initial_status,
        )
        ttk.Label(frame, textvariable=status_var, foreground="#475569", wraplength=460).grid(
            row=11,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        def set_component_defaults(component: str) -> None:
            kind = self._normalize_path_component_type(component)
            if kind == le.PATH_COMPONENT_THIN_LENS:
                parameter_var.set("100")
            elif kind == le.PATH_COMPONENT_REFRACTIVE_SURFACE:
                parameter_var.set("100")
                glass_var.set(glass_var.get().strip() or "BK7")
            else:
                parameter_var.set("0")

        def update_component_fields(*_args, reset_defaults: bool = False) -> None:
            kind = self._normalize_path_component_type(component_var.get())
            if reset_defaults:
                set_component_defaults(kind)
            if kind == le.PATH_COMPONENT_THIN_LENS:
                parameter_label_var.set("Focal length [mm]")
                parameter_entry.configure(state="normal")
                glass_label_var.set("Glass (not used)")
                glass_entry.configure(state="disabled")
                status_var.set("Thin Lens stores focal length in the Rc table column, matching KrakenOS Thin_Lens.")
            elif kind == le.PATH_COMPONENT_REFRACTIVE_SURFACE:
                parameter_label_var.set("Radius of curvature [mm]")
                parameter_entry.configure(state="normal")
                glass_label_var.set("Glass")
                glass_entry.configure(state="normal")
                status_var.set("A refractive surface is a single native Standard surface; add a second surface for thickness.")
            elif kind in {le.PATH_COMPONENT_MIRROR, le.PATH_COMPONENT_OBJECT_TARGET}:
                parameter_label_var.set(f"{kind} radius [mm] (0 = flat)")
                parameter_entry.configure(state="normal")
                glass_label_var.set("Glass (MIRROR)")
                glass_entry.configure(state="disabled")
                if kind == le.PATH_COMPONENT_OBJECT_TARGET:
                    status_var.set("Object Target marks the object location but currently reflects specularly as a proxy.")
                else:
                    status_var.set("A flat normal mirror reflects back along the path; edit Tilt for a fold mirror.")
            else:
                parameter_label_var.set("Parameter (not used)")
                parameter_entry.configure(state="disabled")
                glass_label_var.set("Glass (AIR)")
                glass_entry.configure(state="disabled")
                if kind == le.PATH_COMPONENT_DETECTOR:
                    status_var.set("Detector planes are tagged as Detector path metadata for detector analyses.")
                else:
                    status_var.set("Aperture stops use the native Aperture row type and path metadata.")

        def parse_values() -> tuple[str, float, float, float | None, str, tuple[float, float, float, float, float]] | None:
            kind = self._normalize_path_component_type(component_var.get())
            try:
                distance = float(distance_var.get().strip())
                diameter = float(diameter_var.get().strip())
            except ValueError:
                status_var.set("Distance and diameter must be numbers.")
                return None
            if not np.isfinite(distance) or distance <= 0.0:
                status_var.set("Distance must be positive.")
                return None
            if not np.isfinite(diameter) or diameter <= 0.0:
                status_var.set("Diameter must be positive.")
                return None
            parameter: float | None = None
            if kind in {le.PATH_COMPONENT_THIN_LENS, le.PATH_COMPONENT_REFRACTIVE_SURFACE, le.PATH_COMPONENT_MIRROR, le.PATH_COMPONENT_OBJECT_TARGET}:
                try:
                    parameter = float(parameter_var.get().strip() or "0")
                except ValueError:
                    status_var.set("Component parameter must be numeric.")
                    return None
                if not np.isfinite(parameter):
                    status_var.set("Component parameter must be finite.")
                    return None
                if kind == le.PATH_COMPONENT_THIN_LENS and abs(parameter) <= 1e-12:
                    status_var.set("Thin lens focal length cannot be zero.")
                    return None
            try:
                local_values = (
                    float(local_decenter_x_var.get().strip() or "0"),
                    float(local_decenter_y_var.get().strip() or "0"),
                    float(local_tilt_x_var.get().strip() or "0"),
                    float(local_tilt_y_var.get().strip() or "0"),
                    float(local_tilt_z_var.get().strip() or "0"),
                )
            except ValueError:
                status_var.set("Local offset and tilt values must be numeric.")
                return None
            if not all(np.isfinite(value) for value in local_values):
                status_var.set("Local offset and tilt values must be finite.")
                return None
            status_var.set("Validation passed.")
            return kind, distance, diameter, parameter, glass_var.get().strip() or "BK7", local_values

        def apply_values() -> None:
            parsed = parse_values()
            if parsed is None:
                return
            kind, distance, diameter, parameter, glass, local_values = parsed
            local_dx, local_dy, local_tx, local_ty, local_tz = local_values
            try:
                if traced_path_mode:
                    insert_index = self._default_insert_index_for_arm_key(self._arm_key_from_branch_path(path))
                    component = self._path_component_row_for_branch_path(
                        path,
                        kind,
                        distance,
                        diameter,
                        parameter_mm=parameter,
                        glass=glass,
                        insert_at=insert_index,
                        local_decenter_x=local_dx,
                        local_decenter_y=local_dy,
                        local_tilt_x=local_tx,
                        local_tilt_y=local_ty,
                        local_tilt_z=local_tz,
                    )
                else:
                    insert_index = max(1, len(self.rows) - 1)
                    component = self._path_component_row_for_arm(
                        splitter_index,
                        role,
                        kind,
                        distance,
                        diameter,
                        parameter_mm=parameter,
                        glass=glass,
                        insert_at=insert_index,
                        local_decenter_x=local_dx,
                        local_decenter_y=local_dy,
                        local_tilt_x=local_tx,
                        local_tilt_y=local_ty,
                        local_tilt_z=local_tz,
                    )
            except Exception as exc:
                status_var.set(self.short_error_message(exc))
                return
            self._begin_history_capture()
            self.rows.insert(insert_index, component)
            self._normalize_special_rows()
            self._sync_table()
            self._select_table_indices([insert_index], focus_index=insert_index)
            self._commit_history_capture()
            self._mark_plot_update_pending()
            placement_label = (
                f"traced path {self._branch_path_compact_detail(path)}"
                if traced_path_mode
                else f"{role.lower()} path"
            )
            self.status_var.set(
                f"Inserted {component.name} at {distance:.6g} mm in the {placement_label}. Click Update."
            )
            window.destroy()
            self._cleanup_current_popup_menu()

        component_menu.bind("<<ComboboxSelected>>", lambda *_args: update_component_fields(reset_defaults=True))
        update_component_fields(reset_defaults=True)
        footer = ttk.Frame(frame)
        footer.grid(row=12, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(footer, text="Validate", command=parse_values).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Insert", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)

    def open_current_path_component_placement(self) -> None:
        le = _layout_constants()
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Path Component", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return
        self._refresh_arm_view_choices()
        label = str(self.arm_view_var.get() or le.ARM_VIEW_DEFAULT).strip()
        arm_key = self._arm_key_for_view_label(label)
        branch_path = self._branch_path_for_arm_key(arm_key)
        if not branch_path:
            messagebox.showinfo(
                "Path Component",
                "Choose a traced Path view first, then run Actions -> Add Component to Current Path View.",
                parent=self.editor,
            )
            return
        self.open_arm_path_component_placement(-1, "Path", branch_path=branch_path)
