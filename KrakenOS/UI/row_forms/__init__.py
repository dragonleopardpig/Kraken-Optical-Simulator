"""Row forms -- dialogs that edit one surface row (docs/design_qt_migration.md phase 3)."""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm
from KrakenOS.UI.row_forms.beam_splitter import build_beam_splitter_form

#: name -> builder, for a shell that opens row forms by name
ROW_FORM_BUILDERS = {
    "beam_splitter": build_beam_splitter_form,
}

__all__ = ["FormField", "FormRefused", "RowForm", "build_beam_splitter_form",
           "ROW_FORM_BUILDERS"]
