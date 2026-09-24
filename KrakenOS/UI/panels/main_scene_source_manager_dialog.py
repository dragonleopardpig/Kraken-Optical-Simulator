"""Scene Source Manager dialog (docs/design_qt_migration.md phase 3).

The record list, the fields, the collection verbs and Apply live in
``KrakenOS/UI/row_forms/scene_sources.py``; the Tk layout lives in
``KrakenOS/UI/panels/row_form_view.py``. What is left here is the factory's
kwargs -- the constants the builder falls back to when an owner lacks them.
"""

from __future__ import annotations

from tkinter import messagebox
from typing import Any, Callable

from KrakenOS.UI.panels.row_form_view import render_row_form
from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.scene_sources import build_scene_source_manager_form


class MainSceneSourceManagerDialog:
    """Own the Scene Source Manager while delegating source state to the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        source_model_values: tuple[str, ...],
        source_model_default: str,
        source_direction_preset_values: tuple[str, ...],
        source_angular_weight_default: str,
        source_angular_weight_values: tuple[str, ...],
        source_row_order_default: str,
        source_row_order_before_object: str,
        source_row_order_after_object: str,
        normalize_source_row_order: Callable[[object], str],
        # bugs/0402: the left Source panel folds into this Manager, so the Manager must expose the
        # imaging-only controls the panel uniquely held -- pupil sampling + the full Gaussian inputs.
        pupil_pattern_default: str = "Meridional fan",
        pupil_pattern_values: tuple[str, ...] = (),
        gaussian_input_mode_default: str = "Waist + offset",
        gaussian_input_mode_values: tuple[str, ...] = (),
        gaussian_waist_side_default: str = "Waist before source",
        gaussian_waist_side_values: tuple[str, ...] = (),
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "source_model_values", tuple(source_model_values))
        object.__setattr__(self, "source_model_default", source_model_default)
        object.__setattr__(self, "source_direction_preset_values", tuple(source_direction_preset_values))
        object.__setattr__(self, "source_angular_weight_default", source_angular_weight_default)
        object.__setattr__(self, "source_angular_weight_values", tuple(source_angular_weight_values))
        object.__setattr__(self, "source_row_order_default", source_row_order_default)
        object.__setattr__(self, "source_row_order_before_object", source_row_order_before_object)
        object.__setattr__(self, "source_row_order_after_object", source_row_order_after_object)
        object.__setattr__(self, "normalize_source_row_order", normalize_source_row_order)
        object.__setattr__(self, "pupil_pattern_default", pupil_pattern_default)
        object.__setattr__(self, "pupil_pattern_values", tuple(pupil_pattern_values))
        object.__setattr__(self, "gaussian_input_mode_default", gaussian_input_mode_default)
        object.__setattr__(self, "gaussian_input_mode_values", tuple(gaussian_input_mode_values))
        object.__setattr__(self, "gaussian_waist_side_default", gaussian_waist_side_default)
        object.__setattr__(self, "gaussian_waist_side_values", tuple(gaussian_waist_side_values))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "source_model_values",
            "source_model_default",
            "source_direction_preset_values",
            "source_angular_weight_default",
            "source_angular_weight_values",
            "source_row_order_default",
            "source_row_order_before_object",
            "source_row_order_after_object",
            "normalize_source_row_order",
            "pupil_pattern_default",
            "pupil_pattern_values",
            "gaussian_input_mode_default",
            "gaussian_input_mode_values",
            "gaussian_waist_side_default",
            "gaussian_waist_side_values",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_scene_source_manager(
        self,
        selected_source_id: str | None = None,
        *,
        aim_row_index: int | None = None,
        aim_face_id: str = "",
    ) -> None:
        # docs/design_qt_migration.md phase 3 (bugs/0881): the record list, the ~30 fields, the
        # collection verbs and Apply live in KrakenOS/UI/row_forms/scene_sources.py, which the
        # Qt dialog uses too. This file is now the factory's kwargs and one call.
        try:
            form = build_scene_source_manager_form(
                self,
                selected_source_id,
                aim_row_index=aim_row_index,
                aim_face_id=aim_face_id,
            )
        except FormRefused as exc:
            messagebox.showinfo("Scene Source Manager", str(exc), parent=self.editor)
            return
        window = render_row_form(self, form, wraplength=900)
        window.geometry("1120x720")
