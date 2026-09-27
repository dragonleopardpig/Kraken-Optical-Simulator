"""The surface table, Qt side (docs/design_qt_migration.md phases 2 and 4).

A Qt view over the SAME `editor.rows` the trace reads -- no copy, no adapter model -- and, since
bugs/0903, an editable one. Every cell shows the text the Tk table shows, because both ask the
model's own `_table_values_for_surface_row`; every edit goes through the model's own
`commit_cell`, the path a Tk cell edit takes, so there is one parser and one set of rules
(`_table_cell_enabled` for which cells a surface type allows, the numeric and tolerance-sequence
checks, the object/image diameter coupling).
"""
from __future__ import annotations

#: the cells whose edits are a choice rather than typed text
CHOICE_FIELDS = ("surface", "glass")
#: cells whose shown text carries a "*" optimisation-variable marker the editor must not see
MARKED_FIELDS = ("rc", "thickness")


def table_fields():
    """(field, heading) in the Tk table's own order."""
    from KrakenOS.UI.layout_editor import COLUMN_LABELS, FIELDS

    return tuple((field, COLUMN_LABELS.get(field, field)) for field in FIELDS)


def choices_for(field: str) -> tuple:
    from KrakenOS.UI.layout_editor import SURFACE_TYPES
    from KrakenOS.UI.services.layout_table_workbench import TABLE_GLASS_CHOICES

    return tuple(SURFACE_TYPES) if field == "surface" else tuple(TABLE_GLASS_CHOICES)


def marker_colour() -> str:
    """The Tk optimisation-variable marker's background, so both tables mark alike."""
    from KrakenOS.UI.layout_editor import OPTIMIZATION_CELL_MARKER_BG

    return str(OPTIMIZATION_CELL_MARKER_BG)


def make_rows_model(editor):
    """A QAbstractTableModel over `editor.rows` (built here so importing the module needs no Qt)."""
    from PySide6.QtCore import QAbstractTableModel, Qt

    fields = table_fields()

    class SurfaceRowsModel(QAbstractTableModel):
        def __init__(self, owner) -> None:
            super().__init__()
            self.editor = owner
            #: the last refusal, for the shell's status bar
            self.last_refusal = ""

        def rowCount(self, parent=None) -> int:
            return len(getattr(self.editor, "rows", ()) or ())

        def columnCount(self, parent=None) -> int:
            return len(fields)

        def field(self, column: int) -> str:
            return fields[column][0]

        def cell_text(self, row: int, column: int) -> str:
            """The text the Tk table shows for this cell -- the model's own formatting."""
            rows = getattr(self.editor, "rows", ()) or ()
            if not 0 <= row < len(rows):
                return ""
            try:
                values = self.editor._table_values_for_surface_row(row, rows[row])
                return str(values[column])
            except (AttributeError, IndexError, TypeError, ValueError):
                return ""

        def data(self, index, role=Qt.ItemDataRole.DisplayRole):
            if not index.isValid():
                return None
            if role == Qt.ItemDataRole.DisplayRole:
                return self.cell_text(index.row(), index.column())
            if role == Qt.ItemDataRole.EditRole:
                text = self.cell_text(index.row(), index.column())
                if self.field(index.column()) in MARKED_FIELDS:
                    text = text.replace("*", "").strip()
                return text
            if role in (Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ToolTipRole):
                # an optimisation variable: the same rule and colour as the Tk cell marker
                # (bugs/0904) -- the model's _optimization_marker_fields_for_row decides
                if self.is_marked(index.row(), self.field(index.column())):
                    if role == Qt.ItemDataRole.ToolTipRole:
                        from KrakenOS.UI.layout_editor import OPTIMIZATION_CELL_MARKER_TEXT

                        return f"{OPTIMIZATION_CELL_MARKER_TEXT}: optimization variable"
                    from PySide6.QtGui import QColor

                    return QColor(marker_colour())
            return None

        def is_marked(self, row: int, field: str) -> bool:
            rows = getattr(self.editor, "rows", ()) or ()
            if not 0 <= row < len(rows):
                return False
            try:
                return field in self.editor._optimization_marker_fields_for_row(rows[row])
            except Exception:
                return False

        def flags(self, index):
            base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            if not index.isValid():
                return base
            field = self.field(index.column())
            if field == "label":
                return base
            try:
                enabled = bool(self.editor._table_cell_enabled(index.row(), field))
            except Exception:
                enabled = False
            return base | Qt.ItemFlag.ItemIsEditable if enabled else base

        def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
            if role != Qt.ItemDataRole.EditRole or not index.isValid():
                return False
            # quiet: a refusal is reported by the Qt shell, never by a Tk message box
            refusal = self.editor.commit_cell(index.row(), self.field(index.column()),
                                              str(value), quiet=True)
            self.last_refusal = refusal
            if refusal:
                return False
            # the commit resyncs the whole table (a surface type change rewrites the row, a
            # diameter edit couples object and image), so every cell may have moved
            self.refresh()
            return True

        def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
            if role != Qt.ItemDataRole.DisplayRole:
                return None
            if orientation == Qt.Orientation.Horizontal:
                return fields[section][1]
            return str(section)

        def refresh(self) -> None:
            """The model behind us changed wholesale (a layout was loaded, a row was added)."""
            self.beginResetModel()
            self.endResetModel()

    return SurfaceRowsModel(editor)


def make_cell_delegate(parent=None):
    """Combo editors for the choice cells; plain text for the rest."""
    from PySide6.QtWidgets import QComboBox, QStyledItemDelegate

    class CellDelegate(QStyledItemDelegate):
        def createEditor(self, widget_parent, option, index):
            field = index.model().field(index.column())
            if field not in CHOICE_FIELDS:
                return super().createEditor(widget_parent, option, index)
            combo = QComboBox(widget_parent)
            choices = list(choices_for(field))
            current = index.model().data(index)
            if current and current not in choices:
                # a loaded glass the quick list lacks stays selectable -- nothing is lost
                choices.insert(0, current)
            combo.addItems(choices)
            return combo

        def setEditorData(self, editor_widget, index):
            if isinstance(editor_widget, QComboBox):
                editor_widget.setCurrentText(str(index.model().data(index)))
                return
            super().setEditorData(editor_widget, index)

        def setModelData(self, editor_widget, model, index):
            if isinstance(editor_widget, QComboBox):
                model.setData(index, editor_widget.currentText())
                return
            super().setModelData(editor_widget, model, index)

    return CellDelegate(parent)
