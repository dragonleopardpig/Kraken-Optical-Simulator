"""Glass catalog browser dialog."""

from __future__ import annotations

from tkinter import messagebox
from typing import Any, Callable
from KrakenOS.UI.panels.row_form_view import render_row_form
from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.glass_catalog import build_glass_catalog_form


class MainGlassCatalogBrowserDialog:
    """Own the glass catalog browser while delegating row edits to the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        shared_setup: Callable[[], Any],
        short_error_message: Callable[[BaseException], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "shared_setup", shared_setup)
        object.__setattr__(self, "short_error_message", short_error_message)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "shared_setup", "short_error_message"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_glass_catalog_browser(self) -> None:
        # docs/design_qt_migration.md phase 3 (bugs/0882): the catalogue records, the live
        # filter and Apply live in KrakenOS/UI/row_forms/glass_catalog.py, which the Qt dialog
        # uses too. The browser is a record-list form with nothing to edit.
        try:
            form = build_glass_catalog_form(self)
        except FormRefused as exc:
            messagebox.showinfo("Glass Catalog Browser", str(exc), parent=self.editor)
            return
        except Exception as exc:
            message = self.short_error_message(exc)
            messagebox.showerror(
                "Glass Catalog Browser",
                f"Could not load KrakenOS glass catalogs:\n\n{message}",
                parent=self.editor,
            )
            self.status_var.set(f"Glass catalog browser failed: {message}")
            return
        window = render_row_form(self, form, wraplength=760)
        window.geometry("900x600")
