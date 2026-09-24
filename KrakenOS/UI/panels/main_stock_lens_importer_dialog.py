"""Stock lens importer dialog."""

from __future__ import annotations

from tkinter import messagebox
from typing import Any, Callable
from KrakenOS.UI.panels.row_form_view import render_row_form
from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.stock_lens import build_stock_lens_form



class MainStockLensImporterDialog:
    """Own the stock lens importer UI while delegating layout mutations to the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        available_stock_lens_catalogs: Callable[[], dict[str, Any]],
        load_stock_lens_catalog: Callable[[Any], dict[str, Any]],
        stock_lens_summary: Callable[[str, Any], dict[str, Any]],
        short_error_message: Callable[[BaseException], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "available_stock_lens_catalogs", available_stock_lens_catalogs)
        object.__setattr__(self, "load_stock_lens_catalog", load_stock_lens_catalog)
        object.__setattr__(self, "stock_lens_summary", stock_lens_summary)
        object.__setattr__(self, "short_error_message", short_error_message)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "available_stock_lens_catalogs",
            "load_stock_lens_catalog",
            "stock_lens_summary",
            "short_error_message",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_stock_lens_importer(self, *, path_placement: dict[str, object] | None = None) -> None:
        # docs/design_qt_migration.md phase 3 (bugs/0882): the catalogue loading, the live
        # search, the placement options and the insert live in
        # KrakenOS/UI/row_forms/stock_lens.py, which the Qt dialog uses too.
        try:
            form = build_stock_lens_form(self, path_placement=path_placement)
        except FormRefused as exc:
            messagebox.showerror("Import Stock Lens", str(exc), parent=self.editor)
            return
        window = render_row_form(self, form, wraplength=880)
        window.geometry("1080x660")
