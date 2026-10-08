"""The surface table's cells, as text (bugs/0989).

A cell of the surface table is TEXT: what the model formats for display
(`_table_values_for_surface_row`), then whatever was typed or chosen over it. The cell parser
(`editable_table_rows`) reads the rows back from these texts, so a typed value and a displayed one
take one path, in every shell.

Until bugs/0989 the texts lived in the Tk table widget -- the parser asked a `ttk.Treeview` for its
items and their values -- so the Qt shell and a headless editor kept a hidden Tk table to parse a
typed number. They are model state now: `_sync_table` fills this from the rows, a committed cell
sets one text, the parser reads them, and each shell's table SHOWS them.

Deliberately as dumb as the widget it replaces: an ordered set of items, each a list of texts and
some colour tags. What a text means is the parser's business.
"""
from __future__ import annotations


class TableCells:
    """The table's rows in display order: item id -> its cell texts, and its tags."""

    def __init__(self) -> None:
        self._values: dict[str, list[str]] = {}
        self._tags: dict[str, tuple[str, ...]] = {}

    def clear(self) -> None:
        self._values.clear()
        self._tags.clear()

    def add(self, item: str, values, tags=()) -> None:
        """A row at the end of the table."""
        item = str(item)
        self._values.pop(item, None)                 # an id shown twice is shown once, where it came last
        self._values[item] = [str(value) for value in values]
        self._tags[item] = tuple(str(tag) for tag in tags)

    def items(self) -> tuple[str, ...]:
        return tuple(self._values)

    def exists(self, item) -> bool:
        return str(item) in self._values

    def index(self, item) -> int:
        """The row's position in the table; ValueError when it is not there."""
        return list(self._values).index(str(item))

    def values(self, item) -> tuple[str, ...]:
        return tuple(self._values.get(str(item), ()))

    def tags(self, item) -> tuple[str, ...]:
        return self._tags.get(str(item), ())

    def text(self, item, column: int) -> str:
        values = self._values.get(str(item), ())
        return values[column] if 0 <= column < len(values) else ""

    def set_text(self, item, column: int, text) -> None:
        """One cell takes a text. A row that is not in the table takes nothing."""
        values = self._values.get(str(item))
        if values is None or column < 0:
            return
        while len(values) <= column:
            values.append("")
        values[column] = str(text)
