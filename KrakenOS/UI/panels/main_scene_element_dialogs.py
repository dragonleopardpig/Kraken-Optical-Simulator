"""Detector, scene target, path-pose, and element settings dialogs."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.detector_settings import build_detector_settings_form
from KrakenOS.UI.row_forms.element_forms import (build_element_settings_form,
                                                 build_path_local_pose_form)
from KrakenOS.UI.row_forms.scene_target import build_scene_target_form
from KrakenOS.UI.uihost import host_of



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

    # ---- one renderer for every row form in this file ------------------------------------
    def _run_row_form_dialog(self, form, *, wraplength: int = 520) -> tk.Toplevel:
        """Lay out a `RowForm` in Tk (docs/design_qt_migration.md phase 3).

        The fields, their kinds, their locks, the validation and Apply all belong to the form;
        this is the Tk half of what `qt/dialogs/row_form_dialog.py` does for Qt, and it is the
        only place in this file that knows about widgets.
        """
        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(form.title)
        window.transient(self.editor)
        frame = ttk.Frame(window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text=form.note, wraplength=wraplength + 40,
                  foreground="#475569").grid(row=0, column=0, columnspan=2, sticky="w",
                                             pady=(0, 10))

        variables: dict[str, tk.Variable] = {}
        widgets: dict[str, ttk.Widget] = {}
        for grid_row, field in enumerate(form.fields, start=1):
            value = form.values.get(field.key, "")
            if field.kind == "static":
                ttk.Label(frame, text=field.label).grid(row=grid_row, column=0, sticky="w",
                                                        padx=(0, 10), pady=3)
                ttk.Label(frame, text=value, foreground="#334155",
                          wraplength=wraplength - 160).grid(row=grid_row, column=1, sticky="w",
                                                            pady=3)
                continue
            if field.kind == "bool":
                variable = tk.BooleanVar(
                    master=window, value=str(value).strip().lower() in ("1", "true", "yes", "on"))
                widget = ttk.Checkbutton(frame, text=field.label, variable=variable)
                widget.grid(row=grid_row, column=0, columnspan=2, sticky="w", pady=(6, 8))
            else:
                ttk.Label(frame, text=field.label).grid(row=grid_row, column=0, sticky="w",
                                                        padx=(0, 10), pady=3)
                variable = tk.StringVar(master=window, value=str(value))
                if field.kind == "choice":
                    widget = ttk.Combobox(frame, textvariable=variable,
                                          values=list(form.choices_for(field.key)),
                                          state="normal" if field.editable else "readonly",
                                          width=max(field.width, 24))
                else:
                    widget = ttk.Entry(frame, textvariable=variable, width=field.width)
                widget.grid(row=grid_row, column=1, sticky="ew", pady=3)
            variables[field.key] = variable
            widgets[field.key] = widget

        validation_var = tk.StringVar(master=window, value=form.summary)
        ttk.Label(frame, textvariable=validation_var, foreground="#475569",
                  wraplength=wraplength + 40).grid(row=len(form.fields) + 1, column=0,
                                                   columnspan=2, sticky="w", pady=(10, 0))

        def sync_enabled() -> None:
            """Follow `form.locked` -- a choice may turn other fields off while we are open."""
            for key, widget in widgets.items():
                field = form.field(key)
                if field is not None and field.kind not in ("choice", "bool"):
                    widget.configure(state="normal" if form.is_enabled(key) else "disabled")

        def refresh_from_form() -> None:
            for key, variable in variables.items():
                value = str(form.values.get(key, ""))
                if isinstance(variable, tk.BooleanVar):
                    variable.set(value.strip().lower() in ("1", "true", "yes", "on"))
                elif variable.get() != value:
                    variable.set(value)
            sync_enabled()

        def on_choice_changed(field) -> None:
            if field.on_change is None:
                return
            try:
                message = field.on_change(form, variables[field.key].get())
            except FormRefused as exc:
                messagebox.showerror(form.title, str(exc), parent=self.editor)
                return
            refresh_from_form()
            if message:
                validation_var.set(message)

        for field in form.fields:
            if field.kind == "choice" and field.on_change is not None:
                widgets[field.key].bind(
                    "<<ComboboxSelected>>", lambda _event, f=field: on_choice_changed(f),
                    add="+")
        sync_enabled()

        def current_values() -> dict[str, str]:
            collected: dict[str, str] = {}
            for key, variable in variables.items():
                if isinstance(variable, tk.BooleanVar):
                    collected[key] = "true" if variable.get() else "false"
                else:
                    collected[key] = variable.get()
            return collected

        def validate_form() -> bool:
            values = current_values()
            errors = list(form.validate(values))
            if errors:
                validation_var.set(errors[0])
                return False
            try:
                validation_var.set("Validation passed: " + form.describe(values))
            except FormRefused as exc:
                validation_var.set(str(exc))
                return False
            return True

        def apply_form() -> None:
            try:
                form.apply(current_values())
            except FormRefused as exc:
                validation_var.set(str(exc))
                return
            window.destroy()
            self._cleanup_current_popup_menu()

        def run_action(action) -> None:
            try:
                action.run(form, host_of(self))
            except FormRefused as exc:
                validation_var.set(str(exc))
                return
            window.destroy()
            self._cleanup_current_popup_menu()

        footer = ttk.Frame(frame)
        footer.grid(row=len(form.fields) + 2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(footer, text="Validate", command=validate_form).pack(side="right",
                                                                        padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_form).pack(side="right")
        for action in form.actions:
            ttk.Button(footer, text=action.label,
                       command=lambda a=action: run_action(a)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
        return window

    def _open_row_form(self, title: str, builder, *args, wraplength: int = 520):
        """Read the table, build the form, show it -- what all four of these dialogs do."""
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror(title, f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return None
        try:
            form = builder(self, *args)
        except FormRefused as exc:
            messagebox.showinfo(title, str(exc), parent=self.editor)
            return None
        return self._run_row_form_dialog(form, wraplength=wraplength)

    def open_detector_settings(self, row_index: int) -> None:
        self._open_row_form("Detector Settings", build_detector_settings_form, row_index)

    def open_scene_target_editor(self, row_index: int | None = None) -> None:
        self._open_row_form("Scene Target", build_scene_target_form, row_index, wraplength=560)

    def open_selected_path_local_pose_editor(self) -> None:
        self._open_row_form("Path-Local Pose", build_path_local_pose_form)

    def open_element_settings(self) -> None:
        self._open_row_form("Element Settings", build_element_settings_form)
