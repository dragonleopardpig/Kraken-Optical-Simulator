"""Surface shape, UDA, mask, and optical solid builder dialog."""

from __future__ import annotations

from pathlib import Path
from tkinter import messagebox
from typing import Any, Callable
from KrakenOS.UI.panels.row_form_view import render_row_form
from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.surface_shape import build_surface_shape_form



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
        # docs/design_qt_migration.md phase 3 (bugs/0887): the coefficients, the presets, the
        # validation, Apply AND the plot live in KrakenOS/UI/row_forms/surface_shape.py. The
        # plot is a FormFigure -- the model draws into a figure the view supplies -- which is
        # the phase-6 matplotlib seam, and the Qt dialog uses the same builder.
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Surface Shape Builder",
                                 f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return
        try:
            form = build_surface_shape_form(self, row_index)
        except FormRefused as exc:
            messagebox.showinfo("Surface Shape Builder", str(exc), parent=self.editor)
            return
        window = render_row_form(self, form, wraplength=420)
        window.geometry("1180x760")
