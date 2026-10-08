"""What the Tk surface table draws on top of its rows, and the entry a cell is edited in (bugs/0987).

A `ttk.Treeview` has no cell border, no grid and nothing per cell, so the Tk table places small
widgets over itself:

- a border round the active cell, and round each block of selected rows;
- the grid lines;
- the "V" marker on a cell that is an optimization variable;
- the entry a cell is edited in.

And, since bugs/0989, the rows themselves: what a cell SAYS is the model's
(`services/table_cells.py`), and this module puts those texts into the `ttk.Treeview`.

The overlays were in `services/layout_table_workbench.py` -- the last module of the toolkit-free layers
to name tkinter at run time, and to load it when imported. WHICH rows are selected, which cell is
active, which cells are variables and what a committed edit does stay there; this module only
draws, and re-draws when the table scrolls.

The state these methods keep (`_active_cell`, the overlay lists, the two pending-redraw ids) is
the editor's: every attribute set here is set on the editor.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from KrakenOS.UI.uihost import host_of
from KrakenOS.UI.widgets import place_commit_cell_entry


class MainSurfaceTableOverlays:
    """The Tk surface table's borders, grid, variable markers and in-cell entry, delegating state."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _hide_active_cell_border(self) -> None:
        for part in self._cell_border_parts:
            part.place_forget()

    def _clear_selection_row_borders(self) -> None:
        overlays = self.editor.__dict__.get("_selection_border_overlays", [])
        for part in overlays:
            try:
                part.destroy()
            except Exception:
                pass
        self._selection_border_overlays = []

    def _update_selection_row_borders(self) -> None:
        if "table" not in self.editor.__dict__:
            return
        self._clear_selection_row_borders()
        selected = list(self.table.selection())
        if not selected:
            return
        border_color = "#2563eb"
        table_width = max(int(self.table.winfo_width()), 1)
        columns = list(self.table["columns"])
        children = list(self.table.get_children())
        selected_indices = sorted(children.index(item) for item in selected if item in children)
        if not selected_indices:
            return

        blocks: list[list[int]] = []
        for index in selected_indices:
            if not blocks or index != blocks[-1][-1] + 1:
                blocks.append([index])
            else:
                blocks[-1].append(index)

        def row_bbox(item: str) -> tuple[int, int, int, int] | None:
            for column_index in range(1, len(columns) + 1):
                bbox = self.table.bbox(item, f"#{column_index}")
                if bbox and len(bbox) == 4:
                    return bbox
            return None

        for block in blocks:
            visible_ranges: list[tuple[int, int]] = []
            for index in block:
                item = children[index]
                if not self.table.exists(item):
                    continue
                bbox = row_bbox(item)
                if not bbox:
                    continue
                _x, y, _width, height = bbox
                if height <= 0:
                    continue
                visible_ranges.append((y, y + height))
            if not visible_ranges:
                continue
            y_top = min(start for start, _end in visible_ranges)
            y_bottom = max(end for _start, end in visible_ranges)
            height = max(0, y_bottom - y_top)
            if height <= 0:
                continue
            top = tk.Frame(self.table, bg=border_color, height=2)
            bottom = tk.Frame(self.table, bg=border_color, height=2)
            left = tk.Frame(self.table, bg=border_color, width=2)
            right = tk.Frame(self.table, bg=border_color, width=2)
            top.place(x=0, y=y_top, width=table_width, height=2)
            bottom.place(x=0, y=y_bottom - 2, width=table_width, height=2)
            left.place(x=0, y=y_top, width=2, height=height)
            right.place(x=table_width - 2, y=y_top, width=2, height=height)
            self._selection_border_overlays.extend([top, bottom, left, right])

    def _update_active_cell_border(self, _event: tk.Event | None = None) -> None:
        self._active_cell_border_after_id = None
        if self.editor.__dict__.get("table") is None:          # no Tk table: nothing to outline (bugs/0990)
            return
        if self._active_cell is None:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        row_id, column_id = self._active_cell
        if not self.table.exists(row_id):
            self._active_cell = None
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        try:
            bbox = self.table.bbox(row_id, column_id)
        except tk.TclError:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        if not bbox or len(bbox) != 4:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        x, y, width, height = bbox
        if width <= 0 or height <= 0:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        self._update_selection_row_borders()
        top, bottom, left, right = self._cell_border_parts
        top.place(x=x, y=y, width=width, height=2)
        bottom.place(x=x, y=y + height - 2, width=width, height=2)
        left.place(x=x, y=y, width=2, height=height)
        right.place(x=x + width - 2, y=y, width=2, height=height)

    def _schedule_active_cell_border_update(self, *, delay: int | None = None) -> None:
        if self._active_cell_border_after_id is not None:
            return
        try:
            if delay is None:
                self._active_cell_border_after_id = host_of(self).after_idle(self._update_active_cell_border)
            else:
                self._active_cell_border_after_id = host_of(self).after(max(0, int(delay)), self._update_active_cell_border)
        except tk.TclError:
            self._active_cell_border_after_id = None

    def _on_table_scroll(self, scrollbar: ttk.Scrollbar, first: str, last: str) -> None:
        scrollbar.set(first, last)
        self._schedule_table_grid_update()
        self._schedule_active_cell_border_update()

    def _on_table_xview(self, *args: object) -> None:
        self.table.xview(*args)
        self._schedule_table_grid_update(delay=16)
        self._update_active_cell_border()

    def _on_table_xscroll(self, scrollbar: ttk.Scrollbar, first: str, last: str) -> None:
        scrollbar.set(first, last)
        self._update_active_cell_border()

    def _clear_table_grid(self) -> None:
        for part in self._grid_overlays:
            part.destroy()
        self._grid_overlays.clear()

    def _table_grid_context(self) -> tuple[list[str], tuple[str, ...], list[tuple[str, tuple[int, int, int, int]]]]:
        columns = list(self.table["columns"])
        items = tuple(self.table.get_children())
        visible_bboxes = []
        if columns and items:
            column_ids = [f"#{column_index}" for column_index in range(1, len(columns) + 1)]
            for item in items:
                for column_id in column_ids:
                    bbox = self.table.bbox(item, column_id)
                    if bbox:
                        visible_bboxes.append((item, bbox))
                        break
        return columns, items, visible_bboxes

    def _schedule_table_grid_update(self, _event: tk.Event | None = None, delay: int = 30) -> None:
        if self._grid_after_id is not None:
            try:
                host_of(self).after_cancel(self._grid_after_id)
            except tk.TclError:
                pass
            self._grid_after_id = None
        try:
            self._grid_after_id = host_of(self).after(max(0, int(delay)), self._update_table_grid)
        except tk.TclError:
            self._grid_after_id = None

    def _update_table_grid(self, _event: tk.Event | None = None) -> None:
        self._grid_after_id = None
        if self.editor.__dict__.get("table") is None:          # no Tk table: nothing to rule (bugs/0990)
            return
        self._clear_table_grid()
        columns, items, visible_bboxes = self._table_grid_context()
        grid_color = "#e2e7ef"
        if not columns or not items or not visible_bboxes:
            return
        data_top = min(bbox[1] for _, bbox in visible_bboxes)
        data_bottom = max(bbox[1] + bbox[3] for _, bbox in visible_bboxes)
        data_height = max(0, data_bottom - data_top)
        if data_height <= 0:
            return

        first_item = visible_bboxes[0][0]
        for column_index in range(1, len(columns)):
            bbox = self.table.bbox(first_item, f"#{column_index}")
            if not bbox:
                continue
            x, _y, width, _height = bbox
            separator = tk.Frame(self.table, bg=grid_color, width=1)
            separator.place(x=x + width - 1, y=data_top, width=1, height=data_height)
            self._grid_overlays.append(separator)

        for item, bbox in visible_bboxes:
            _x, y, width, height = bbox
            row_line = tk.Frame(self.table, bg=grid_color, height=1)
            row_line.place(x=0, y=y + height - 1, relwidth=1.0, height=1)
            self._grid_overlays.append(row_line)

        self._draw_optimization_cell_markers(items, columns)
        self._schedule_active_cell_border_update()

    def _draw_optimization_cell_markers(self, items: tuple[str, ...], columns: list[str]) -> None:
        if not items or not columns:
            return
        # the editor module defines the marker's look, and imports this one: so, late
        from KrakenOS.UI.layout_editor import (OPTIMIZATION_CELL_MARKER_BG, OPTIMIZATION_CELL_MARKER_FG,
                                               OPTIMIZATION_CELL_MARKER_TEXT)

        field_to_column = {field: f"#{index + 1}" for index, field in enumerate(columns)}
        for item in items:
            row_index = self._table_item_row_index(item)
            if row_index is None or not (0 <= row_index < len(self.rows)):
                continue
            row = self.rows[row_index]
            for field in self._optimization_marker_fields_for_row(row):
                column_id = field_to_column.get(field)
                if not column_id:
                    continue
                bbox = self.table.bbox(item, column_id)
                if not bbox or len(bbox) != 4:
                    continue
                x, y, width, height = bbox
                if width <= 24 or height <= 8:
                    continue
                marker_width = min(max(16, int(width * 0.22)), 24)
                marker = tk.Label(
                    self.table,
                    text=OPTIMIZATION_CELL_MARKER_TEXT,
                    bg=OPTIMIZATION_CELL_MARKER_BG,
                    fg=OPTIMIZATION_CELL_MARKER_FG,
                    bd=1,
                    relief="solid",
                    padx=0,
                    pady=0,
                    font=("TkDefaultFont", 8, "bold"),
                )
                marker.place(
                    x=x + width - marker_width - 1,
                    y=y + 2,
                    width=marker_width,
                    height=max(1, height - 4),
                )
                marker.bind(
                    "<Button-1>",
                    lambda event, selected_item=item, selected_field=field: self._on_optimization_marker_click(
                        event,
                        selected_item,
                        selected_field,
                    ),
                )
                marker.bind(
                    "<Button-3>",
                    lambda event, selected_item=item, selected_field=field: self._on_optimization_marker_click(
                        event,
                        selected_item,
                        selected_field,
                    ),
                )
                self._grid_overlays.append(marker)

    # ---- the rows themselves: the Tk table SHOWS the model's cells (bugs/0989) -------------------
    # `services/table_cells.py` holds what a cell says; the parser reads it there. These three put it
    # on screen, and do nothing when there is no Tk table to put it on.
    def _show_tk_table_rows(self) -> None:
        """Every row replaced by the model's: its texts, in order, with its colour tags."""
        table = self.editor.__dict__.get("table")
        if table is None:
            return
        cells = self._table_cells()
        table.delete(*table.get_children())
        for item in cells.items():
            table.insert("", "end", iid=item, values=cells.values(item), tags=cells.tags(item))

    def _show_tk_table_cell(self, item: str, field: str, text: str) -> None:
        """One cell's text, as the model now has it."""
        table = self.editor.__dict__.get("table")
        if table is None or not table.exists(item):
            return
        table.set(item, field, text)

    def _show_tk_table_headings(self, labels: dict) -> None:
        """The column headings: they change with the path view."""
        table = self.editor.__dict__.get("table")
        if table is None:
            return
        for field, label in labels.items():
            try:
                table.heading(field, text=label)
            except Exception:
                continue

    # ---- the selection: the Tk table is pointed at the model's (bugs/0990) ------------------------
    def _install_border_only_table_selection(self) -> None:
        """A selection is drawn as borders, never as the Treeview's own highlight: the widget's
        `selection*` methods become the model's, so whoever asks the table asks the model. The natives
        are kept only to clear what the widget selects on its own (a paging key)."""
        table = self.table
        self._native_table_selection = table.selection
        self._native_table_selection_set = table.selection_set
        self._native_table_selection_remove = table.selection_remove
        table.selection = self._table_selection  # type: ignore[method-assign]
        table.selection_set = self._set_table_selection  # type: ignore[method-assign]
        table.selection_remove = self._remove_from_table_selection  # type: ignore[method-assign]
        table.selection_add = self._add_to_table_selection  # type: ignore[method-assign]
        table.selection_toggle = self._toggle_table_selection  # type: ignore[method-assign]

    def _clear_native_table_selection(self) -> None:
        native_selection = self._native_table_selection
        native_remove = self._native_table_selection_remove
        if native_selection is None or native_remove is None:
            return
        try:
            selected = tuple(native_selection())
        except Exception:
            selected = ()
        if selected:
            try:
                native_remove(*selected)
            except Exception:
                pass

    def _tk_table_focus_item(self):
        """The Tk table's focus item, or None when there is no Tk table to ask."""
        table = self.editor.__dict__.get("table")
        if table is None:
            return None
        return str(table.focus() or "")

    def _show_tk_table_focus_item(self, item: str) -> None:
        table = self.editor.__dict__.get("table")
        if table is not None:
            table.focus(item)

    def _show_tk_table_item(self, item) -> None:
        """Scroll the row into view."""
        table = self.editor.__dict__.get("table")
        if table is not None:
            table.see(item)

    def _place_cell_editor(self, row_id: str, field: str, value: str, bbox) -> ttk.Entry:
        """The entry a cell is edited in, placed over the cell: Return or leaving it commits, Escape cancels."""
        return place_commit_cell_entry(
            self.table,
            value=value,
            bbox=tuple(int(part) for part in bbox),
            on_commit=lambda: self._finish_edit(row_id, field),
            on_cancel=self._cancel_edit,
        )
