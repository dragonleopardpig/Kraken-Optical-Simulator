"""The CAD/STL face-roles editor in the Qt shell (docs/design_qt_migration.md phase 5g, bugs/0934).

A view over `face_roles_session.FaceRolesSession` -- the same session the Tk dialog renders -- with
the same `face_roles_preview.FaceRolesPreview` drawing into a Qt VTK widget. Nothing here decides
anything: widgets are written into ``session.form`` before an action (`_push`) and the dialog
redraws from the session when it notifies (`sync`).

Two rules this follows:

* the face table's items are created ONCE and only their texts change on a sync, so no item a Qt
  signal is still using is ever deleted (the bugs/0932 segfault);
* the VTK widget is created by `build_preview`, after the dialog is shown -- VTK takes the native
  window id in its constructor, and a widget built before its window exists draws into a dead
  handle (see `qt/viewport.py`).
"""
from __future__ import annotations

from KrakenOS.UI import face_roles_session as frs

ROLE_INDEX = 32  # Qt.ItemDataRole.UserRole: the face's record index


def _show_choice(combo, text: str) -> None:
    """Show ``text`` in a read-only combo even when it is not one of its choices (a legacy value
    loaded from a saved row): a Tk readonly combobox shows any value its variable holds, and the
    value must round-trip unchanged through the next apply."""
    if combo.findText(text) < 0:
        combo.addItem(text)
    combo.setCurrentText(text)


def _dialog_base():
    from PySide6.QtWidgets import QDialog

    return QDialog


class FaceCoatingTableDialog(_dialog_base()):
    """The per-face coating-table editor: a preset or a hand-edited ``[R, A, W, THETA]`` table,
    validated by `frs.parse_face_coating_table` (the Tk editor's own check)."""

    def __init__(self, parent, initial_table, initial_met, on_apply, host) -> None:
        from PySide6.QtWidgets import (QComboBox, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                                       QPlainTextEdit, QVBoxLayout)

        super().__init__(parent)
        self.setWindowTitle("Face coating table")
        self._on_apply = on_apply
        self._host = host
        self.presets = frs.coating_presets()
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.preset = QComboBox()
        self.preset.addItems(["Custom", *self.presets.keys()])
        self.preset.activated.connect(self._use_preset)
        form.addRow("Preset", self.preset)
        layout.addLayout(form)
        hint = QLabel(frs.COATING_TABLE_HINT)
        hint.setStyleSheet("color: #5f6b7a")
        layout.addWidget(hint)
        self.table = QPlainTextEdit(frs.format_coating_table(initial_table))
        self.table.setMinimumSize(640, 200)
        layout.addWidget(self.table)
        met_form = QFormLayout()
        self.met = QLineEdit(str(int(initial_met or 0)))
        met_form.addRow("CoatingMet", self.met)
        layout.addLayout(met_form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _use_preset(self, _index: int) -> None:
        name = self.preset.currentText()
        if name in self.presets:
            self.table.setPlainText(frs.format_coating_table(self.presets[name]))

    def apply(self) -> bool:
        table, met, error = frs.parse_face_coating_table(self.table.toPlainText(), self.met.text())
        if error:
            self._host.showerror("Face coating", error)
            return False
        self._on_apply(table, met)
        self.accept()
        return True


class FaceRolesDialog(_dialog_base()):
    """``session``: a `FaceRolesSession`; ``host``: the shell's UI host (message boxes)."""

    def __init__(self, session, *, parent=None, host=None) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout)

        super().__init__(parent)
        self.session = session
        self.host = host
        self.preview = None
        self.vtk_widget = None
        self._syncing = False
        self.setWindowTitle(session.title())
        self.setModal(False)
        self.resize(1440, 760)
        layout = QVBoxLayout(self)
        header = QLabel(session.header_text())
        header.setWordWrap(True)
        layout.addWidget(header)
        body = self.body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(self._build_tree())
        body.addWidget(self._build_preview_pane())
        body.addWidget(self._build_form())
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 4)
        body.setStretchFactor(2, 2)
        layout.addWidget(body, 1)
        footer = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        # the Tk footer's order: four on the left, then Close / Copy Summary / Save Roles on the right
        for text, action in (
                ("Open 3D Placement", session.open_placement_view),
                ("Native Surface Props", session.open_native_surface_props),
                ("Use Face As Source Target", session.use_as_source_target),
                ("Set as Illumination Source", session.use_as_illumination_source),
                (None, None),
                ("Close", self.close),
                ("Copy Summary", session.copy_summary),
                ("Save Roles", session.save_roles)):
            if text is None:
                footer.addStretch(1)
                continue
            button = self.buttons[text] = QPushButton(text)
            button.clicked.connect(lambda _checked=False, a=action: self._act(a))
            footer.addWidget(button)
        layout.addLayout(footer)
        session.listeners.append(self.sync)
        self.finished.connect(self._forget)
        self.sync(render=False)

    # ---- layout ---------------------------------------------------------------------------------
    def _build_tree(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem

        session = self.session
        self.columns = session.columns()
        tree = self.tree = QTreeWidget()
        tree.setColumnCount(len(self.columns))
        tree.setHeaderLabels([frs.TREE_HEADINGS[c] for c in self.columns])
        tree.setRootIsDecorated(False)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        tree.setWordWrap(True)
        for column, key in enumerate(self.columns):
            tree.setColumnWidth(column, frs.TREE_WIDTHS[key])
        # the items are made once: a sync only rewrites their texts (never delete an item a
        # selection signal may still hold -- bugs/0932)
        self.items = []
        for index in range(len(session.records)):
            item = QTreeWidgetItem()
            item.setData(0, ROLE_INDEX, index)
            for column, key in enumerate(self.columns):
                if key in {"area", "triangles", "split"}:     # right-aligned, as in Tk
                    item.setTextAlignment(column, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tree.addTopLevelItem(item)
            self.items.append(item)
        tree.itemSelectionChanged.connect(self._on_tree_select)
        if session.show_face_groups:
            tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tree.customContextMenuRequested.connect(self._group_menu)
        return tree

    def _build_preview_pane(self):
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

        pane = QWidget()
        layout = QVBoxLayout(pane)
        hint = QLabel(frs.PREVIEW_HINT)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #334155")
        layout.addWidget(hint)
        self.preview_host = QWidget()
        self.preview_host.setMinimumSize(360, 360)
        self.preview_layout = QVBoxLayout(self.preview_host)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.preview_host, 1)
        self.preview_status = QLabel(self.session.preview_status)
        self.preview_status.setWordWrap(True)
        self.preview_status.setStyleSheet("color: #475569")
        layout.addWidget(self.preview_status)
        return pane

    def _build_form(self):
        from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                                       QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget)

        session = self.session
        pane = QWidget()
        outer = QVBoxLayout(pane)
        form = QFormLayout()
        outer.addLayout(form)
        self.combos: dict[str, QComboBox] = {}
        for key, (label, values) in frs.form_choices().items():
            combo = self.combos[key] = QComboBox()
            combo.addItems(list(values))
            combo.setToolTip(frs.TOOLTIPS[key])
            # activated = a USER choice (a sync's setCurrentText does not emit it)
            combo.activated.connect(lambda _i: self._auto_apply())
            form.addRow(label, combo)
        self.entries: dict[str, QLineEdit] = {}
        snap = QWidget()
        snap_layout = QGridLayout(snap)
        snap_layout.setContentsMargins(0, 0, 0, 0)
        for column, key in enumerate(("input_offset_u", "input_offset_v")):
            entry = self.entries[key] = QLineEdit()
            entry.setToolTip(frs.TOOLTIPS[key])
            snap_layout.addWidget(entry, 0, column)
        self.pick_button = QPushButton("Pick In 3D")
        self.pick_button.setToolTip(frs.TOOLTIPS["pick"])
        self.pick_button.clicked.connect(lambda: self._act(session.toggle_input_snap_pick))
        zero = self.zero_button = QPushButton("Zero")
        zero.setToolTip(frs.TOOLTIPS["zero"])
        zero.clicked.connect(lambda: self._act(session.clear_input_snap_offsets))
        snap_layout.addWidget(self.pick_button, 1, 0)
        snap_layout.addWidget(zero, 1, 1)
        snap.setToolTip(frs.TOOLTIPS["input_offset"])
        form.addRow("Input snap U/V [mm]", snap)
        for key, label in frs.FORM_TEXT_FIELDS:
            entry = self.entries[key] = QLineEdit()
            if key in frs.TOOLTIPS:
                entry.setToolTip(frs.TOOLTIPS[key])
            form.addRow(label, entry)
        coating_row = QWidget()
        coating_layout = QHBoxLayout(coating_row)
        coating_layout.setContentsMargins(0, 0, 0, 0)
        self.coating = QComboBox()
        self.coating.setEditable(True)        # legacy free-text coatings still load
        self.coating.addItems(list(frs.coating_choices()))
        self.coating.activated.connect(lambda _i: session.choose_coating(self.coating.currentText()))
        self.coating.lineEdit().editingFinished.connect(self._auto_apply)
        coating_layout.addWidget(self.coating, 1)
        edit_table = QPushButton("Edit table…")
        edit_table.clicked.connect(self.edit_coating_table)
        coating_layout.addWidget(edit_table)
        form.addRow("Coating", coating_row)
        self.flip = QCheckBox("Flip normal for UI intent")
        self.flip.clicked.connect(lambda _c: self._auto_apply())
        form.addRow(self.flip)
        self.entries["notes"] = QLineEdit()
        form.addRow("Notes", self.entries["notes"])
        for entry in self.entries.values():
            # editingFinished = Return or leaving the field: the Tk <Return> + <FocusOut> commit
            entry.editingFinished.connect(self._auto_apply)
        self.validation = QLabel(session.validation)
        self.validation.setWordWrap(True)
        self.validation.setStyleSheet("color: #475569")
        outer.addWidget(self.validation)
        physics = QLabel(frs.PHYSICS_HINT)
        physics.setWordWrap(True)
        physics.setStyleSheet("color: #64748b")
        outer.addWidget(physics)
        self.auto_orient = QCheckBox(frs.AUTO_ORIENT_LABEL)
        self.auto_orient.setToolTip(session.auto_orient_hint())
        outer.addWidget(self.auto_orient)
        for title, entries, action in (("2D side", frs.quick_sides(), session.set_side_and_apply),
                                       ("Port role", frs.quick_ports(), session.set_port_and_apply)):
            box = QGroupBox(title)
            row = QHBoxLayout(box)
            for label, value, tooltip in entries:
                button = QPushButton(label)
                button.setToolTip(tooltip)
                button.clicked.connect(lambda _c=False, a=action, v=value: self._act(a, v))
                row.addWidget(button)
            outer.addWidget(box)
        self.form_buttons: dict[str, QPushButton] = {}
        for label, action in (("Apply Form to Selected", session.apply_selected),
                              ("Auto Guess 2D Sides", session.auto_guess),
                              ("Suggest Optical Intent", session.refresh_suggestions),
                              ("Apply Suggestions to Empty", session.apply_suggestions_to_empty),
                              ("Clear Face Labels", session.clear_roles)):
            button = self.form_buttons[label] = QPushButton(label)
            button.clicked.connect(lambda _c=False, a=action: self._act(a))
            outer.addWidget(button)
        outer.addWidget(self._build_virtual_plane())
        outer.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidget(pane)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(360)
        return scroll

    def _build_virtual_plane(self):
        from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton

        session = self.session
        box = QGroupBox("Virtual Internal Plane")
        form = QFormLayout(box)
        self.virtual_diagonal = QComboBox()
        self.virtual_diagonal.addItems(list(session.le.OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_VALUES))
        form.addRow("Diagonal", self.virtual_diagonal)
        self.virtual_entries: dict[str, QLineEdit] = {}
        for key, label in frs.VIRTUAL_TEXT_FIELDS:
            entry = self.virtual_entries[key] = QLineEdit()
            form.addRow(label, entry)
        hint = QLabel(frs.VIRTUAL_HINT)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #64748b")
        form.addRow(hint)
        self.virtual_status = QLabel(session.virtual_status)
        self.virtual_status.setWordWrap(True)
        self.virtual_status.setStyleSheet("color: #475569")
        form.addRow(self.virtual_status)
        for label, action in (("Auto Cube Splitter Plane", session.build_virtual_cube_plane),
                              ("Clear Virtual Planes", session.clear_virtual_planes)):
            button = self.form_buttons[label] = QPushButton(label)
            button.clicked.connect(lambda _c=False, a=action: self._act(a))
            form.addRow(button)
        return box

    def build_preview(self) -> None:
        """The VTK preview -- call once the dialog is SHOWN (the native-window rule above)."""
        import vtkmodules.vtkInteractionStyle  # noqa: F401  (registers the interactor styles)
        import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  (the GL render window factory)
        from PySide6.QtCore import QObject
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser
        from vtkmodules.vtkRenderingCore import vtkRenderer

        from KrakenOS.UI.face_roles_preview import FaceRolesPreview

        if self.preview is not None:
            return
        widget = self.vtk_widget = QVTKRenderWindowInteractor(self.preview_host)
        self.preview_layout.addWidget(widget)
        renderer = vtkRenderer()
        widget.GetRenderWindow().AddRenderer(renderer)
        widget.Initialize()
        # the dialog owns the left button (click picks, drag orbits at a fixed rate, as in Open 3D);
        # a do-nothing style keeps VTK's trackball from ALSO turning the camera
        widget.GetRenderWindow().GetInteractor().SetInteractorStyle(vtkInteractorStyleUser())
        self.preview = FaceRolesPreview(self.session, renderer, widget.GetRenderWindow())
        dialog = self

        class _Filter(QObject):
            def eventFilter(self, _obj, event):  # noqa: N802 (Qt's name)
                return dialog._preview_event(event)

        self._filter = _Filter(widget)
        widget.installEventFilter(self._filter)
        self.render(reset_camera=True)

    # ---- the preview's mouse --------------------------------------------------------------------
    def vtk_point(self, position) -> tuple[float, float]:
        """A widget position -> VTK display coordinates (render-window pixels, y up)."""
        try:
            ratio = float(self.vtk_widget._getPixelRatio())
        except Exception:
            ratio = 1.0
        height = self.vtk_widget.GetRenderWindow().GetSize()[1]
        return float(position.x()) * ratio, float(height) - 1.0 - float(position.y()) * ratio

    def _preview_event(self, event) -> bool:
        from PySide6.QtCore import QEvent, Qt

        kind = event.type()
        if kind not in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove, QEvent.Type.MouseButtonRelease):
            return False                      # the wheel and the rest stay VTK's (zoom)
        if kind != QEvent.Type.MouseMove and event.button() != Qt.MouseButton.LeftButton:
            return False
        x, y = self.vtk_point(event.position())
        if kind == QEvent.Type.MouseButtonPress:
            self.preview.press(x, y)
        elif kind == QEvent.Type.MouseMove:
            if not event.buttons() & Qt.MouseButton.LeftButton:
                return False
            self.preview.motion(x, y)
        else:
            self._push()
            self.preview.release(x, y)
        return True

    # ---- widgets <-> session ---------------------------------------------------------------------
    def _push(self) -> None:
        form = self.session.form
        for key, combo in self.combos.items():
            form[key] = combo.currentText()
        for key, entry in self.entries.items():
            form[key] = entry.text()
        form["coating"] = self.coating.currentText()
        form["flip"] = self.flip.isChecked()
        form["auto_orient"] = self.auto_orient.isChecked()
        virtual = self.session.virtual_form
        virtual["diagonal"] = self.virtual_diagonal.currentText()
        for key, entry in self.virtual_entries.items():
            virtual[key] = entry.text()

    def _act(self, action, *args) -> None:
        self._push()
        action(*args)

    def _auto_apply(self) -> None:
        if self._syncing:
            return
        self._act(self.session.auto_apply)

    def edit_coating_table(self):
        def apply(table, met) -> None:
            self._push()
            self.session.set_coating_table(table, met)

        dialog = self.coating_dialog = FaceCoatingTableDialog(
            self, self.session.coating_state.get("table"), self.session.coating_state.get("met", 0), apply, self.host)
        dialog.show()
        return dialog

    def _on_tree_select(self) -> None:
        if self._syncing:
            return
        indices = sorted(int(item.data(0, ROLE_INDEX)) for item in self.tree.selectedItems())
        current = self.tree.currentItem()
        focus = int(current.data(0, ROLE_INDEX)) if current is not None else None
        if indices == self.session.selection and (focus is None or focus == self.session.focus):
            return
        self.session.select(indices, focus if focus in indices else None)

    def _group_menu(self, position) -> None:
        from PySide6.QtWidgets import QMenu

        item = self.tree.itemAt(position)
        if item is None:
            return
        index = int(item.data(0, ROLE_INDEX))
        label = self.session.group_menu_label(index)
        if label is None:
            return
        menu = self.group_menu = QMenu(self)
        menu.addAction(label).triggered.connect(lambda _c=False, i=index: self.session.select_group(i))
        menu.popup(self.tree.viewport().mapToGlobal(position))

    def sync(self, *, render: bool = True) -> None:
        """Redraw everything from the session (signals blocked: a sync is not a user edit)."""
        from PySide6.QtCore import QItemSelectionModel, Qt

        session = self.session
        self._syncing = True
        try:
            form = session.form
            for key, combo in self.combos.items():
                _show_choice(combo, str(form[key]))
            for key, entry in self.entries.items():
                if entry.text() != str(form[key]):
                    entry.setText(str(form[key]))
            self.coating.setCurrentText(str(form["coating"]))
            self.flip.setChecked(bool(form["flip"]))
            self.auto_orient.setChecked(bool(form["auto_orient"]))
            _show_choice(self.virtual_diagonal, str(session.virtual_form["diagonal"]))
            for key, entry in self.virtual_entries.items():
                if entry.text() != str(session.virtual_form[key]):
                    entry.setText(str(session.virtual_form[key]))
            states = session.field_states()
            for key in ("split", "loss", "phase"):
                self.entries[key].setEnabled(states[key])
            for item, cells in zip(self.items, session.rows()):
                for column, key in enumerate(self.columns):
                    if item.text(column) != cells[key]:
                        item.setText(column, cells[key])
            wanted = set(session.selection)
            current = {int(item.data(0, ROLE_INDEX)) for item in self.tree.selectedItems()}
            if wanted != current or (session.focus is not None and self.tree.currentItem() is not self.items[session.focus]):
                self.tree.blockSignals(True)
                try:
                    self.tree.clearSelection()
                    if session.focus is not None:
                        self.tree.setCurrentItem(self.items[session.focus], 0, QItemSelectionModel.SelectionFlag.NoUpdate)
                    for index in wanted:
                        self.items[index].setSelected(True)
                    if session.focus is not None:
                        self.tree.scrollToItem(self.items[session.focus])
                finally:
                    self.tree.blockSignals(False)
            self.pick_button.setText("Picking..." if session.input_snap_pick_active else "Pick In 3D")
            if self.vtk_widget is not None:
                if session.input_snap_pick_active:
                    self.vtk_widget.setCursor(Qt.CursorShape.CrossCursor)
                else:
                    self.vtk_widget.unsetCursor()
            if render:
                self.render()
            self.validation.setText(session.validation)
            self.preview_status.setText(session.preview_status)
            self.virtual_status.setText(session.virtual_status)
        finally:
            self._syncing = False

    def render(self, *, reset_camera: bool = False) -> None:
        if self.preview is not None:
            self.preview.render(reset_camera=reset_camera)
        self.preview_status.setText(self.session.preview_status)

    def _forget(self, _result=None) -> None:
        # a pending debounced retrace still runs: an edit made just before closing must reach the
        # Open 3D view (the Tk dialog never cancelled it either)
        if self.sync in self.session.listeners:
            self.session.listeners.remove(self.sync)
