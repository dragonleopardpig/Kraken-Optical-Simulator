"""Row forms -- dialogs that edit one surface row (docs/design_qt_migration.md phase 3)."""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormRefused, RowForm
from KrakenOS.UI.row_forms.beam_splitter import build_beam_splitter_form
from KrakenOS.UI.row_forms.coating_material import build_coating_material_form
from KrakenOS.UI.row_forms.diffuse_scatter import build_diffuse_scatter_form
from KrakenOS.UI.row_forms.error_map import build_error_map_form

#: name -> builder, for a shell that opens row forms by name
ROW_FORM_BUILDERS = {
    "beam_splitter": build_beam_splitter_form,
    "diffuse_scatter": build_diffuse_scatter_form,
    "error_map": build_error_map_form,
    "coating_material": build_coating_material_form,
}

__all__ = ["FormAction", "FormField", "FormRefused", "RowForm", "build_beam_splitter_form",
           "build_diffuse_scatter_form", "build_error_map_form",
           "build_coating_material_form",
           "ROW_FORM_BUILDERS"]
