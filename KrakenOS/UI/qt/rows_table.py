"""The surface table, Qt side (docs/design_qt_migration.md phase 2).

Read-only for now: editing is phase 4, where the Tk Treeview's editing behaviour moves onto Qt's
model/view. The point of this step is that a Qt view reads the SAME `editor.rows` the trace reads
-- no copy, no adapter model.
"""
from __future__ import annotations

#: (heading, SurfaceRow attribute, formatter)
COLUMNS = (
    ("#", "label", str),
    ("Name", "name", str),
    ("Surface", "surface", str),
    ("Radius", "rc", lambda v: f"{float(v):.4f}"),
    ("Thickness", "thickness", lambda v: f"{float(v):.4f}"),
    ("Glass", "glass", str),
    ("Diameter", "diameter", lambda v: f"{float(v):.3f}"),
)


def make_rows_model(editor):
    """A QAbstractTableModel over `editor.rows` (built here so importing the module needs no Qt)."""
    from PySide6.QtCore import QAbstractTableModel, Qt

    class SurfaceRowsModel(QAbstractTableModel):
        def __init__(self, owner) -> None:
            super().__init__()
            self.editor = owner

        def rowCount(self, parent=None) -> int:
            return len(getattr(self.editor, "rows", ()) or ())

        def columnCount(self, parent=None) -> int:
            return len(COLUMNS)

        def data(self, index, role=Qt.ItemDataRole.DisplayRole):
            if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
                return None
            rows = getattr(self.editor, "rows", ()) or ()
            if not 0 <= index.row() < len(rows):
                return None
            _heading, attribute, form = COLUMNS[index.column()]
            try:
                return form(getattr(rows[index.row()], attribute))
            except (AttributeError, TypeError, ValueError):
                return ""

        def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
            if role != Qt.ItemDataRole.DisplayRole:
                return None
            if orientation == Qt.Orientation.Horizontal:
                return COLUMNS[section][0]
            return str(section)

        def refresh(self) -> None:
            """The model behind us changed wholesale (a layout was loaded)."""
            self.beginResetModel()
            self.endResetModel()

    return SurfaceRowsModel(editor)
