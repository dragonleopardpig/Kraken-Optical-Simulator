"""Detector, scene target, path-pose, and element settings dialogs."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

import numpy as np


class MainSceneElementDialogs:
    """Own scene/element settings dialogs while delegating state to the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        normalize_detector_settings: Callable[[dict[str, object]], dict[str, object]],
        scene_target_editor_kind_labels: dict[str, str],
        scene_target_editor_kind_choices: tuple[str, ...],
        normalize_scene_target_editor_kind: Callable[[str], str],
        element_metadata_numeric_fields: tuple[str, ...],
        normalize_element_metadata: Callable[[dict[str, object]], dict[str, object]],
        element_metadata_summary: Callable[[dict[str, object]], str],
        short_error_message: Callable[[BaseException], str],
        element_arm_role_default: str,
        element_arm_role_values: tuple[str, ...],
        element_branch_selector_values: tuple[str, ...],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "normalize_detector_settings", normalize_detector_settings)
        object.__setattr__(self, "scene_target_editor_kind_labels", dict(scene_target_editor_kind_labels))
        object.__setattr__(self, "scene_target_editor_kind_choices", tuple(scene_target_editor_kind_choices))
        object.__setattr__(self, "normalize_scene_target_editor_kind", normalize_scene_target_editor_kind)
        object.__setattr__(self, "element_metadata_numeric_fields", tuple(element_metadata_numeric_fields))
        object.__setattr__(self, "normalize_element_metadata", normalize_element_metadata)
        object.__setattr__(self, "element_metadata_summary", element_metadata_summary)
        object.__setattr__(self, "short_error_message", short_error_message)
        object.__setattr__(self, "element_arm_role_default", element_arm_role_default)
        object.__setattr__(self, "element_arm_role_values", tuple(element_arm_role_values))
        object.__setattr__(self, "element_branch_selector_values", tuple(element_branch_selector_values))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "normalize_detector_settings",
            "scene_target_editor_kind_labels",
            "scene_target_editor_kind_choices",
            "normalize_scene_target_editor_kind",
            "element_metadata_numeric_fields",
            "normalize_element_metadata",
            "element_metadata_summary",
            "short_error_message",
            "element_arm_role_default",
            "element_arm_role_values",
            "element_branch_selector_values",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_detector_settings(self, row_index: int) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Detector Settings", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return
        if not (0 <= row_index < len(self.rows)):
            return
        row = self.rows[row_index]
        if row.surface == "Object":
            messagebox.showinfo("Detector Settings", "Object rows cannot be detector planes.", parent=self.editor)
            return
        settings = self._detector_settings(row)
        diameter = self._safe_positive_float(getattr(row, "diameter", 0.0), 0.0)
        width_default = float(settings.get("active_width_mm", 0.0)) or diameter
        height_default = float(settings.get("active_height_mm", 0.0)) or diameter

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Detector Settings - S{row_index}")
        window.transient(self.editor)
        frame = ttk.Frame(window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        width_var = tk.StringVar(master=window, value=self._format_table_float(width_default))
        height_var = tk.StringVar(master=window, value=self._format_table_float(height_default))
        bins_var = tk.StringVar(master=window, value=str(settings.get("bins", "") or ""))
        pitch_var = tk.StringVar(master=window, value=self._format_table_float(float(settings.get("pixel_pitch_um", 0.0))))
        ttk.Label(
            frame,
            text=(
                "Detector settings mark this row as a terminal detector for path analyses. "
                "Active size controls DetMap/CohDet extents in detector-local coordinates; "
                "Bins overrides the global Detector bins field when set."
            ),
            wraplength=520,
            foreground="#475569",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        field_specs = [
            ("Active width [mm]", width_var),
            ("Active height [mm]", height_var),
            ("Detector bins (blank = global)", bins_var),
            ("Pixel pitch [um] (metadata)", pitch_var),
        ]
        for grid_row, (label, var) in enumerate(field_specs, start=1):
            ttk.Label(frame, text=label).grid(row=grid_row, column=0, sticky="w", padx=(0, 10), pady=3)
            ttk.Entry(frame, textvariable=var, width=18).grid(row=grid_row, column=1, sticky="ew", pady=3)

        validation_var = tk.StringVar(value="Use blank bins for global Auto/manual Detector bins.")
        ttk.Label(frame, textvariable=validation_var, foreground="#475569", wraplength=520).grid(
            row=len(field_specs) + 1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        def collect_settings() -> dict[str, object] | None:
            try:
                active_width = float(width_var.get().strip() or "0")
                active_height = float(height_var.get().strip() or "0")
                pixel_pitch = float(pitch_var.get().strip() or "0")
            except ValueError:
                validation_var.set("Active size and pixel pitch must be numbers.")
                return None
            if active_width < 0.0 or active_height < 0.0 or pixel_pitch < 0.0:
                validation_var.set("Active size and pixel pitch must be non-negative.")
                return None
            bins = bins_var.get().strip()
            if bins and bins.lower() not in {"auto", "default"}:
                try:
                    bins_value = int(float(bins))
                except ValueError:
                    validation_var.set("Detector bins must be blank, Auto, or an integer from 4 to 512.")
                    return None
                if not 4 <= bins_value <= 512:
                    validation_var.set("Detector bins must be between 4 and 512.")
                    return None
                bins = str(bins_value)
            else:
                bins = ""
            return self.normalize_detector_settings(
                {
                    "active_width_mm": active_width,
                    "active_height_mm": active_height,
                    "bins": bins,
                    "pixel_pitch_um": pixel_pitch,
                }
            )

        def validate_settings() -> dict[str, object] | None:
            data = collect_settings()
            if data is not None:
                validation_var.set(
                    "Validation passed: "
                    f"{float(data['active_width_mm']):.6g} x {float(data['active_height_mm']):.6g} mm, "
                    f"bins={data.get('bins') or 'global'}, pitch={float(data['pixel_pitch_um']):.6g} um"
                )
            return data

        def apply_settings() -> None:
            data = validate_settings()
            if data is None:
                return
            self._begin_history_capture()
            self._set_detector_settings(self.rows[row_index], data)
            self._sync_table()
            self._select_table_row(row_index)
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Updated detector settings for S{row_index}. Click Update to retrace analyses.")
            window.destroy()
            self._cleanup_current_popup_menu()

        def clear_settings() -> None:
            self._begin_history_capture()
            self._set_detector_settings(self.rows[row_index], {})
            self._sync_table()
            self._select_table_row(row_index)
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Cleared detector settings for S{row_index}.")
            window.destroy()
            self._cleanup_current_popup_menu()

        footer = ttk.Frame(frame)
        footer.grid(row=len(field_specs) + 2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(footer, text="Validate", command=validate_settings).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_settings).pack(side="right")
        ttk.Button(footer, text="Clear", command=clear_settings).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)

    def open_scene_target_editor(self, row_index: int | None = None) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Scene Target", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return
        if row_index is None:
            record = self._nonseq_scene_selected_record()
            if record is not None:
                try:
                    row_index = int(record.get("row_index"))
                except Exception:
                    row_index = None
        if row_index is None:
            row_index = self._selected_surface_row_index()
        if row_index is None or not (0 <= int(row_index) < len(self.rows)):
            messagebox.showinfo("Scene Target", "Select a surface row or scene target first.", parent=self.editor)
            return
        index = int(row_index)
        row = self.rows[index]

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Scene Target - S{index}")
        window.transient(self.editor)
        frame = ttk.Frame(window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text=(
                "Scene target settings are stored on the surface row and feed the scene graph, "
                "detector/path analysis, and non-sequential target selection."
            ),
            wraplength=560,
            foreground="#475569",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        name_var = tk.StringVar(master=window, value=str(row.name or row.surface or f"S{index}"))
        kind_key = self._scene_target_editor_kind_for_row(index)
        role_var = tk.StringVar(master=window, value=self.scene_target_editor_kind_labels.get(kind_key, self.scene_target_editor_kind_labels["auto"]))
        active_var = tk.BooleanVar(master=window, value=self._current_nonseq_target_surface_index() == index)
        detector_defaults = self._default_detector_settings_for_target_row(index)
        width_var = tk.StringVar(master=window, value=self._format_table_float(float(detector_defaults.get("active_width_mm", 0.0))))
        height_var = tk.StringVar(master=window, value=self._format_table_float(float(detector_defaults.get("active_height_mm", 0.0))))
        bins_var = tk.StringVar(master=window, value=str(detector_defaults.get("bins", "") or ""))
        pitch_var = tk.StringVar(master=window, value=self._format_table_float(float(detector_defaults.get("pixel_pitch_um", 0.0))))

        ttk.Label(frame, text=f"Row S{index}").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Label(frame, text=f"{row.surface} | {row.glass}").grid(row=1, column=1, sticky="w", pady=3)
        ttk.Label(frame, text="Name").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(frame, textvariable=name_var, width=28).grid(row=2, column=1, sticky="ew", pady=3)
        ttk.Label(frame, text="Target role").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=3)
        role_combo = ttk.Combobox(frame, textvariable=role_var, values=self.scene_target_editor_kind_choices, state="readonly", width=24)
        role_combo.grid(row=3, column=1, sticky="ew", pady=3)
        ttk.Checkbutton(frame, text="Set as active non-sequential TargSurf", variable=active_var).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(6, 8),
        )

        detector_frame = ttk.LabelFrame(frame, text="Detector metadata", padding=8)
        detector_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
        detector_frame.columnconfigure(1, weight=1)
        detector_widgets: list[ttk.Widget] = []
        for grid_row, (label, var) in enumerate(
            (
                ("Active width [mm]", width_var),
                ("Active height [mm]", height_var),
                ("Detector bins (blank = global)", bins_var),
                ("Pixel pitch [um]", pitch_var),
            )
        ):
            ttk.Label(detector_frame, text=label).grid(row=grid_row, column=0, sticky="w", padx=(0, 10), pady=3)
            entry = ttk.Entry(detector_frame, textvariable=var, width=18)
            entry.grid(row=grid_row, column=1, sticky="ew", pady=3)
            detector_widgets.append(entry)

        validation_var = tk.StringVar(master=window, value="Scene target metadata is row-backed; click Apply to update the table state.")
        ttk.Label(frame, textvariable=validation_var, foreground="#475569", wraplength=560).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        def collect_detector_settings() -> dict[str, object] | None:
            try:
                active_width = float(width_var.get().strip() or "0")
                active_height = float(height_var.get().strip() or "0")
                pixel_pitch = float(pitch_var.get().strip() or "0")
            except ValueError:
                validation_var.set("Detector active size and pixel pitch must be numbers.")
                return None
            if active_width < 0.0 or active_height < 0.0 or pixel_pitch < 0.0:
                validation_var.set("Detector active size and pixel pitch must be non-negative.")
                return None
            bins = bins_var.get().strip()
            if bins and bins.lower() not in {"auto", "default"}:
                try:
                    bins_value = int(float(bins))
                except ValueError:
                    validation_var.set("Detector bins must be blank, Auto, or an integer from 4 to 512.")
                    return None
                if not 4 <= bins_value <= 512:
                    validation_var.set("Detector bins must be between 4 and 512.")
                    return None
                bins = str(bins_value)
            else:
                bins = ""
            return self.normalize_detector_settings(
                {
                    "active_width_mm": active_width,
                    "active_height_mm": active_height,
                    "bins": bins,
                    "pixel_pitch_um": pixel_pitch,
                }
            )

        def sync_detector_state(*_args) -> None:
            detector_enabled = self.normalize_scene_target_editor_kind(role_var.get()) == "detector"
            state = "normal" if detector_enabled else "disabled"
            for widget in detector_widgets:
                widget.configure(state=state)

        def validate_target() -> tuple[str, dict[str, object] | None] | None:
            kind = self.normalize_scene_target_editor_kind(role_var.get())
            detector_data = collect_detector_settings()
            if detector_data is None:
                return None
            if kind == "detector" and row.surface == "Object":
                validation_var.set("Object rows cannot be detector planes.")
                return None
            validation_var.set(
                f"Validation passed: role={self.scene_target_editor_kind_labels.get(kind, kind)}, "
                f"active={'yes' if active_var.get() else 'no'}."
            )
            return kind, detector_data

        def apply_target() -> None:
            validated = validate_target()
            if validated is None:
                return
            kind, detector_data = validated
            self._begin_history_capture()
            try:
                result = self._apply_scene_target_editor_update(
                    index,
                    target_kind=kind,
                    detector_settings=detector_data,
                    active_target=bool(active_var.get()),
                    row_name=name_var.get(),
                )
            except Exception as exc:
                self._history_pending_state = None
                validation_var.set(str(exc))
                return
            self._sync_table()
            self._select_table_row(index)
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self._refresh_nonseq_scene_graph_if_open()
            self.status_var.set(
                f"Updated scene target S{index}: {result['surface']} / {result['target_kind']}. Click Update to trace."
            )
            window.destroy()
            self._cleanup_current_popup_menu()

        def clear_target() -> None:
            self._begin_history_capture()
            self._clear_scene_target_editor_metadata(index)
            self._sync_table()
            self._select_table_row(index)
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self._refresh_nonseq_scene_graph_if_open()
            self.status_var.set(f"Cleared scene-target metadata for S{index}.")
            window.destroy()
            self._cleanup_current_popup_menu()

        role_combo.bind("<<ComboboxSelected>>", sync_detector_state, add="+")
        sync_detector_state()

        footer = ttk.Frame(frame)
        footer.grid(row=7, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(footer, text="Validate", command=validate_target).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_target).pack(side="right")
        ttk.Button(footer, text="Clear Target", command=clear_target).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)

    def open_selected_path_local_pose_editor(self) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Path-Local Pose", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return
        blocks = self._selected_element_blocks()
        if len(blocks) != 1:
            messagebox.showinfo("Path-Local Pose", "Select one placed path element or stock-lens block first.", parent=self.editor)
            return
        indices = blocks[0]
        metadata = self._element_metadata(self.rows[indices[0]])
        if not self._metadata_has_path_pose(metadata):
            messagebox.showinfo(
                "Path-Local Pose",
                "The selected element has no path-placement metadata. Insert it with a path-component/stock-lens command first.",
                parent=self,
            )
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Path-Local Pose - rows {indices[0]}-{indices[-1]}")
        window.transient(self.editor)
        frame = ttk.Frame(window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        label = self._element_key(self.rows[indices[0]]) or str(metadata.get("element_name", "") or "Path element")
        branch_path = str(metadata.get("branch_path", "") or "").strip()
        frame_text = (
            self._branch_path_compact_detail(branch_path)
            if branch_path
            else self.element_metadata_summary(metadata)
        )
        ttk.Label(
            frame,
            text=(
                f"Edit the local pose of {label}. The UI recomputes global Tilt/Decenter values "
                "from the current path frame; for traced BRANCH_PATH elements, click Update first."
            ),
            wraplength=520,
            foreground="#475569",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(frame, text="Path frame").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Label(frame, text=frame_text, foreground="#334155", wraplength=360).grid(row=1, column=1, sticky="w", pady=3)

        numeric_vars = {
            key: tk.StringVar(value=self._format_table_float(float(metadata.get(key, 0.0))))
            for key in self.element_metadata_numeric_fields
        }
        field_specs = [
            ("Path distance [mm]", "arm_distance"),
            ("Local X offset [mm]", "local_decenter_x"),
            ("Local Y offset [mm]", "local_decenter_y"),
            ("Local tilt X [deg]", "local_tilt_x"),
            ("Local tilt Y [deg]", "local_tilt_y"),
            ("Local tilt Z [deg]", "local_tilt_z"),
        ]
        for grid_row, (label_text, key) in enumerate(field_specs, start=2):
            ttk.Label(frame, text=label_text).grid(row=grid_row, column=0, sticky="w", padx=(0, 10), pady=3)
            ttk.Entry(frame, textvariable=numeric_vars[key], width=16).grid(row=grid_row, column=1, sticky="ew", pady=3)

        validation_var = tk.StringVar(value="Validate checks that the saved path frame can still be resolved.")
        ttk.Label(frame, textvariable=validation_var, foreground="#475569", wraplength=520).grid(
            row=len(field_specs) + 2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        def collect_metadata() -> dict[str, object] | None:
            data = dict(metadata)
            for key, var in numeric_vars.items():
                try:
                    value = float(var.get().strip())
                except ValueError:
                    validation_var.set(f"{key.replace('_', ' ')} expects a number.")
                    return None
                if not np.isfinite(value):
                    validation_var.set(f"{key.replace('_', ' ')} must be finite.")
                    return None
                data[key] = value
            return self.normalize_element_metadata(data)

        def validate_values() -> dict[str, object] | None:
            data = collect_metadata()
            if data is None:
                return None
            try:
                self._path_frame_for_element_metadata(data)
            except Exception as exc:
                validation_var.set(self.short_error_message(exc))
                return None
            validation_var.set("Validation passed: path frame resolved and pose values are finite.")
            return data

        def apply_values() -> None:
            data = validate_values()
            if data is None:
                return
            self._begin_history_capture()
            try:
                updated_indices = self._apply_path_local_pose_to_indices(indices, data)
            except Exception as exc:
                self._history_pending_state = None
                validation_var.set(self.short_error_message(exc))
                return
            self._normalize_special_rows()
            self._sync_table()
            self._select_table_indices(updated_indices, focus_index=updated_indices[0])
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Updated path-local pose for {label}. Click Update to retrace.")
            window.destroy()
            self._cleanup_current_popup_menu()

        footer = ttk.Frame(frame)
        footer.grid(row=len(field_specs) + 3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(footer, text="Validate", command=validate_values).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)

    def open_element_settings(self) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Element Settings", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return
        blocks = self._selected_element_blocks()
        if not blocks:
            messagebox.showinfo("Element Settings", "Select a non-Object/non-Image row or element group first.", parent=self.editor)
            return
        if len(blocks) > 1:
            messagebox.showinfo("Element Settings", "Open Element Settings for one element at a time.", parent=self.editor)
            return
        indices = blocks[0]
        row = self.rows[indices[0]]
        metadata = self._element_metadata(row)
        element_label = self._element_key(row) or str(row.name or self._next_manual_element_label()).strip()
        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Element Settings - rows {indices[0]}-{indices[-1]}")
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        frame = ttk.Frame(window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        name_var = tk.StringVar(value=element_label)
        id_var = tk.StringVar(value=str(metadata.get("element_id", "") or self._element_id_from_label(element_label)))
        role_var = tk.StringVar(value=str(metadata.get("arm_role", self.element_arm_role_default)))
        parent_var = tk.StringVar(value=str(metadata.get("parent_splitter", "") or ""))
        selector_value = str(metadata.get("branch_selector", "") or "")
        selector_var = tk.StringVar(value=selector_value if selector_value else "Auto")
        branch_path_var = tk.StringVar(value=str(metadata.get("branch_path", "") or ""))
        numeric_vars = {
            key: tk.StringVar(value=self._format_table_float(float(metadata.get(key, 0.0))))
            for key in self.element_metadata_numeric_fields
        }

        rows = [
            ("Element name", ttk.Entry(frame, textvariable=name_var)),
            ("Element ID", ttk.Entry(frame, textvariable=id_var)),
            ("Path role", ttk.Combobox(frame, textvariable=role_var, values=self.element_arm_role_values, state="readonly")),
            ("Parent splitter", ttk.Combobox(frame, textvariable=parent_var, values=self._beam_splitter_element_choices())),
            ("Split selector", ttk.Combobox(frame, textvariable=selector_var, values=self.element_branch_selector_values)),
            ("Traced branch path", ttk.Entry(frame, textvariable=branch_path_var)),
            ("Path distance [mm]", ttk.Entry(frame, textvariable=numeric_vars["arm_distance"])),
            ("Local decenter X [mm]", ttk.Entry(frame, textvariable=numeric_vars["local_decenter_x"])),
            ("Local decenter Y [mm]", ttk.Entry(frame, textvariable=numeric_vars["local_decenter_y"])),
            ("Local tilt X [deg]", ttk.Entry(frame, textvariable=numeric_vars["local_tilt_x"])),
            ("Local tilt Y [deg]", ttk.Entry(frame, textvariable=numeric_vars["local_tilt_y"])),
            ("Local tilt Z [deg]", ttk.Entry(frame, textvariable=numeric_vars["local_tilt_z"])),
        ]
        ttk.Label(
            frame,
            text="Element metadata is saved with each surface row. It is used by path-aware UI tools and future placement/analysis helpers.",
            wraplength=520,
            foreground="#475569",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        for grid_row, (label, widget) in enumerate(rows, start=1):
            ttk.Label(frame, text=label).grid(row=grid_row, column=0, sticky="w", padx=(0, 10), pady=3)
            widget.grid(row=grid_row, column=1, sticky="ew", pady=3)

        validation_var = tk.StringVar(value="Set Common/Transmit/Reflect/Detector path metadata for this element.")
        ttk.Label(frame, textvariable=validation_var, foreground="#475569", wraplength=520).grid(
            row=len(rows) + 1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        def collect_metadata() -> dict[str, object] | None:
            label = name_var.get().strip()
            if not label:
                validation_var.set("Element name cannot be empty.")
                return None
            role = str(role_var.get()).strip()
            if role not in self.element_arm_role_values:
                validation_var.set("Choose a valid path role.")
                return None
            data: dict[str, object] = dict(metadata)
            data.update({
                "element_id": id_var.get().strip(),
                "element_name": label,
                "arm_role": role,
                "parent_splitter": parent_var.get().strip(),
                "branch_selector": "" if selector_var.get().strip() == "Auto" else selector_var.get().strip(),
                "branch_path": branch_path_var.get().strip(),
            })
            for key, var in numeric_vars.items():
                try:
                    value = float(var.get().strip())
                except ValueError:
                    validation_var.set(f"{key.replace('_', ' ')} expects a number.")
                    return None
                if not np.isfinite(value):
                    validation_var.set(f"{key.replace('_', ' ')} must be finite.")
                    return None
                data[key] = value
            if not data["branch_selector"]:
                data["branch_selector"] = self._branch_selector_for_arm_role(role)
            return self.normalize_element_metadata(data)

        def validate_values() -> dict[str, object] | None:
            data = collect_metadata()
            if data is not None:
                validation_var.set("Validation passed: " + self.element_metadata_summary(data))
            return data

        def apply_values() -> None:
            data = validate_values()
            if data is None:
                return
            label = str(data.get("element_name", "") or "").strip()
            self._begin_history_capture()
            if self._metadata_has_path_pose(data):
                try:
                    self._apply_path_local_pose_to_indices(indices, data)
                except Exception as exc:
                    self._history_pending_state = None
                    validation_var.set(self.short_error_message(exc))
                    return
            else:
                for index in indices:
                    self.rows[index].element = label
                    self._set_element_metadata(self.rows[index], data)
            self._normalize_special_rows()
            self._sync_table()
            self._select_table_indices(indices, focus_index=indices[0])
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Updated element settings for {label}: {self.element_metadata_summary(data)}.")
            window.destroy()
            self._cleanup_current_popup_menu()

        footer = ttk.Frame(frame)
        footer.grid(row=len(rows) + 2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(footer, text="Validate", command=validate_values).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)

