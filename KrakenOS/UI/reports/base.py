"""Toolkit-free report records (docs/design_qt_migration.md phase 3).

A report dialog is a summary line, a table and an export. None of that needs a toolkit -- only
the LAYOUT does. Each dialog's data therefore becomes a :class:`Report` built by a plain
function, and each toolkit gets a thin view over it: the Tk dialog and the Qt dialog render the
same object, so a number can never differ between them, and the data can be checked by a
display-free guard.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReportColumn:
    """One table column. ``numeric`` drives both the format and the alignment."""

    key: str
    heading: str
    numeric: bool = True
    width: int = 70
    stretch: bool = False
    #: "l" / "c" / "r"; empty follows `numeric` (a Tk dialog may centre a count column)
    align: str = ""

    @property
    def alignment(self) -> str:
        return self.align or ("r" if self.numeric else "l")

    def format(self, value) -> str:
        if not self.numeric:
            return "" if value is None else str(value)
        try:
            return f"{float(value):.8g}"
        except (TypeError, ValueError):
            return str(value)


@dataclass(frozen=True)
class ReportChoice:
    """A choice that REBUILDS the report when changed -- a Tk dialog's combobox.

    ``key`` is the builder's keyword argument, so a view needs to know nothing about what the
    choice means: it collects the current value of every control and calls the builder again.
    """

    key: str
    label: str
    choices: tuple[str, ...] = ()
    value: str = ""


@dataclass
class Report:
    """A report dialog's whole content."""

    title: str
    summary: str
    columns: tuple[ReportColumn, ...] = ()
    #: the RAW records -- what the CSV writes
    rows: list[dict[str, Any]] = field(default_factory=list)
    #: already-formatted cells, one tuple per row, when the MODEL owns the formatting (some
    #: reports have shared value formatters the Tk dialog already uses; the two views must then
    #: format identically by construction, not by two implementations agreeing)
    display_rows: "list[tuple[str, ...]] | None" = None
    #: the CSV's fieldnames when they differ from the table's columns
    csv_keys: "tuple[str, ...] | None" = None
    #: the whole report as text, for Copy, when the model can produce one
    text: str = ""
    #: controls that rebuild this report when changed (a filter, a target surface...)
    controls: tuple[ReportChoice, ...] = ()
    #: what the status line should say once it is shown
    status: str = ""

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(column.key for column in self.columns)

    @property
    def headings(self) -> tuple[str, ...]:
        return tuple(column.heading for column in self.columns)

    def cell(self, row_index: int, column_index: int) -> str:
        """The displayed text of one cell -- one implementation for every toolkit."""
        if self.display_rows is not None:
            return str(self.display_rows[row_index][column_index])
        column = self.columns[column_index]
        return column.format(self.rows[row_index].get(column.key))

    def write_csv(self, path) -> Path:
        """The exported file: the raw values under the column keys, not the display text."""
        path = Path(path)
        fieldnames = list(self.csv_keys if self.csv_keys is not None else self.keys)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows([{key: row.get(key) for key in fieldnames} for row in self.rows])
        return path


class ReportFailed(Exception):
    """The model could not produce the report. Carries the message a dialog should show."""
