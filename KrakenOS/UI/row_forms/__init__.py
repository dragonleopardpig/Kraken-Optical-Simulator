"""Row forms -- dialogs that edit one surface row (docs/design_qt_migration.md phase 3)."""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm
from KrakenOS.UI.row_forms.beam_splitter import build_beam_splitter_form
from KrakenOS.UI.row_forms.diffuse_scatter import build_diffuse_scatter_form

#: name -> builder, for a shell that opens row forms by name
ROW_FORM_BUILDERS = {
    "beam_splitter": build_beam_splitter_form,
    "diffuse_scatter": build_diffuse_scatter_form,
}

__all__ = ["FormField", "FormRefused", "RowForm", "build_beam_splitter_form",
           "build_diffuse_scatter_form", "ROW_FORM_BUILDERS"]
