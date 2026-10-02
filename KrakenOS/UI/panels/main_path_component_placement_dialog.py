"""Path component placement dialog."""

from __future__ import annotations

from typing import Any, Callable
from KrakenOS.UI.panels.row_form_view import render_row_form
from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.path_component import build_path_component_form



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
        # docs/design_qt_migration.md phase 3 (bugs/0888): the component types, what each one
        # makes the parameter MEAN, the validation and the insert live in
        # KrakenOS/UI/row_forms/path_component.py, which the Qt dialog uses too.
        from KrakenOS.UI.uihost import host_of

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            host_of(self.editor).showerror("Path Component", f"Could not read the surface table:\n\n{exc}")
            return
        try:
            form = build_path_component_form(
                self, splitter_index, arm_role,
                default_component=default_component, branch_path=branch_path)
        except FormRefused as exc:
            host_of(self.editor).showinfo("Path Component", str(exc))
            return
        render_row_form(self, form, wraplength=460,
                        on_close=self._cleanup_current_popup_menu)

    def open_current_path_component_placement(self) -> None:
        """Actions -> Add Component to Current Path View: the placement form on the traced path the
        Path view shows. 0888 dropped this method while moving the form to row_forms/, and the
        editor's delegation then reached the editor again through ``__getattr__`` -- an infinite
        recursion in both shells for a week (bugs/0941)."""
        from KrakenOS.UI.uihost import host_of

        le = _layout_constants()
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            host_of(self.editor).showerror("Path Component", f"Could not read the surface table:\n\n{exc}")
            return
        self._refresh_arm_view_choices()
        label = str(self.arm_view_var.get() or le.ARM_VIEW_DEFAULT).strip()
        branch_path = self._branch_path_for_arm_key(self._arm_key_for_view_label(label))
        if not branch_path:
            host_of(self.editor).showinfo(
                "Path Component",
                "Choose a traced Path view first, then run Actions -> Add Component to Current Path View.")
            return
        self.open_arm_path_component_placement(-1, "Path", branch_path=branch_path)
