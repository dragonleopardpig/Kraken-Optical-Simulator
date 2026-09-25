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
from typing import Any, Callable


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


@dataclass(frozen=True)
class ReportValue:
    """A typed-in value that rebuilds the report -- a Tk dialog's entry box.

    Like :class:`ReportChoice`, ``key`` is the builder's keyword; the builder is what parses the
    text, so a bad entry is the model's problem to report, not the view's.
    """

    key: str
    label: str
    value: str = ""
    width: int = 10


@dataclass
class DetailView:
    """The second table of a master/detail dialog: the rows belonging to the selected one.

    `rows(index)` returns already-formatted cells for master row ``index`` -- the model owns that
    formatting, as it does for `Report.display_rows`.
    """

    columns: tuple[ReportColumn, ...] = ()
    rows: "Callable[[int], list[tuple[str, ...]]]" = lambda _index: []
    label: str = "Details"


@dataclass(frozen=True)
class ReportUpdate:
    """What a verb did: a status line, and control values it wants the view to adopt.

    "Use Cavity Eigenmode" computes the resonator's own mode and WRITES IT BACK into the waist
    and offset boxes, then recomputes. Returning that as data keeps the arithmetic in the model
    and leaves each toolkit one job: put these values in those widgets.
    """

    status: str = ""
    #: control key -> its new value
    controls: dict = field(default_factory=dict)
    #: rebuild the report once the controls are adopted
    rebuild: bool = True


@dataclass(frozen=True)
class ReportAction:
    """A toolbar verb beyond Refresh / Copy / Export CSV / Close.

    The model owns what the verb DOES; the view owns only what a toolkit must supply: a file
    chooser (`save_title`), the current control values (`needs_controls`) and which row is
    selected (`needs_selection`), passed in that order. A view therefore renders any action it
    has never heard of, and both toolkits offer the same verbs -- before this, "Export Events
    CSV", "Open Ray" and "Use Cavity Eigenmode" were Tk buttons Qt simply did not have.

    `run` returns a status line, or a :class:`ReportUpdate` when it also changes the controls.
    """

    label: str
    run: "Callable[..., Any]" = lambda *_args: ""
    #: when set, the view asks for a save path with this title and passes it as the FIRST argument
    save_title: str = ""
    #: pass the current control values, as a dict, after the path
    needs_controls: bool = False
    #: pass the selected master key (a row index, or a tree node's key) as the LAST argument
    needs_selection: bool = False


@dataclass
class DetailText:
    """A text PANE describing the selected master row, where a table would not read well.

    The source illumination report explains one source's loss budget in prose; that is detail
    just as much as a table of hits is, so it belongs on the `Report` rather than in one
    toolkit's dialog -- otherwise only Tk ever shows it.
    """

    text: "Callable[[Any], str]" = lambda _key: ""
    label: str = "Details"
    #: what to show when nothing is selected
    empty: str = ""
    #: rows of text, for the toolkits that size a text pane in them
    height: int = 6


@dataclass
class TreeRow:
    """One node of a master TREE: its own label, its cells, and the rows beneath it.

    `detail_key` is what the detail view is asked for when this node is selected -- a record
    index for a leaf, None for a grouping node that has no detail of its own.
    """

    label: str = ""
    cells: tuple[str, ...] = ()
    children: list = field(default_factory=list)
    detail_key: Any = None
    expanded: bool = True


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
    controls: tuple = ()
    #: the detail table, for a master/detail dialog
    detail: "DetailView | None" = None
    #: a detail text pane, for a master/detail dialog whose detail is prose
    detail_text: "DetailText | None" = None
    #: a master TREE instead of a flat table (rays with their paths nested underneath)
    tree: "tuple[TreeRow, ...] | None" = None
    #: the heading of a tree's own label column
    tree_heading: str = "Name"
    #: extra toolbar verbs
    actions: "tuple[ReportAction, ...]" = ()
    #: the model's own exporter, when the CSV is not this table (one row per HIT, say)
    csv_writer: "Callable[[Any], Any] | None" = None
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
        """The exported file: the raw values under the column keys, not the display text.

        A report whose CSV is not its table -- the ray inspector flattens each ray into one row
        per hit under ~140 columns -- carries a `csv_writer` and this defers to it, so both
        toolkits export the same file.
        """
        path = Path(path)
        if self.csv_writer is not None:
            return Path(self.csv_writer(path))
        fieldnames = list(self.csv_keys if self.csv_keys is not None else self.keys)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows([{key: row.get(key) for key in fieldnames} for row in self.rows])
        return path


class ReportFailed(Exception):
    """The model could not produce the report. Carries the message a dialog should show."""
