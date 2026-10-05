"""The 3D inspector's View / Scene / Carry rows in the Qt shell (docs/design_qt_migration.md 5f).

The rows are data in `open3d_toolbar.py`; this lays them out as Qt widgets bound to the SAME model
variables the Tk rows bind to. A widget writes its variable and then runs the model's commit, the
way a Tk checkbutton sets its variable before its command; a model write reaches the widget
through the variable's ``trace_add`` (signals blocked, so a repaint never commits again).

The rows are TABS of one strip (user request, bugs/0961: "make all toolbars tabbed and can be
hide/unhide. Give user chance to have big clean 3D scene"): the tab names at its left, the chosen
row beside them. Three stacked rows took 96 px from the 3D scene; one row takes about a third of
that, and the strip's own arrow hides it altogether (the shell's 3D Toolbar switch brings it back).

Each row is a QToolBar: a row longer than the scene is wide puts what does not fit behind its »
button, as toolbars do -- it must not force the main window wider than the screen (0906 measured
a window pushed past it by stacked minimum sizes), and a scroll bar cost height and hid the end
of the row.
"""
from __future__ import annotations

from KrakenOS.UI import open3d_toolbar as catalogue


def _truthy(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _watch(variable, repaint) -> None:
    try:
        variable.trace_add("write", lambda *_args: repaint())
    except Exception:
        pass


def build_toolbar(inspector, parent=None):
    """The rows as one tabbed strip. ``strip.controls`` maps a label to its widget/action;
    ``strip.tabs`` is the tab bar (one tab per row), ``strip.pages`` the stack of rows and
    ``strip.hide_button`` the arrow at its right end that asks for the strip to be hidden."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QAction, QActionGroup
    from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu,
                                   QPushButton, QSizePolicy, QStackedWidget, QTabBar, QToolBar, QToolButton,
                                   QWidget)

    controls: dict = {}

    def run(target, args=()):
        return catalogue.callback(inspector, target, args)

    def bind_check(widget_or_action, variable, target, *, setter, getter_signal) -> None:
        setter(_truthy(variable.get()))

        def written(checked) -> None:
            variable.set(bool(checked))
            run(target)()

        getter_signal.connect(written)

        def repaint() -> None:
            blocker = widget_or_action.blockSignals(True)
            try:
                setter(_truthy(variable.get()))
            finally:
                widget_or_action.blockSignals(blocker)

        _watch(variable, repaint)

    def fill_menu(menu, spec) -> None:
        for entry in spec.entries:
            if entry is None:
                menu.addSeparator()
            elif isinstance(entry, catalogue.Menu):
                sub = menu.addMenu(entry.label)
                fill_menu(sub, entry)
            elif isinstance(entry, catalogue.Check):
                variable = catalogue.resolve(inspector, entry.var)
                if variable is None:
                    continue
                action = QAction(entry.label, menu)
                action.setCheckable(True)
                bind_check(action, variable, entry.target, setter=action.setChecked, getter_signal=action.toggled)
                menu.addAction(action)
                controls[f"{spec.label}/{entry.label}"] = action
            elif isinstance(entry, catalogue.Command):
                if entry.tk_only:
                    continue
                action = QAction(entry.label, menu)
                action.triggered.connect(lambda _checked=False, e=entry: run(e.target, e.args)())
                menu.addAction(action)
                controls[f"{spec.label}/{entry.label}"] = action

    def add(layout, row_widget, item) -> None:
        if isinstance(item, catalogue.Command):
            if item.tk_only:
                return
            button = QPushButton(item.label, row_widget)
            button.clicked.connect(lambda _checked=False, i=item: run(i.target, i.args)())
            layout.addWidget(button)
            controls[item.label] = button
        elif isinstance(item, catalogue.Button):
            button = QPushButton(item.label, row_widget)
            button.clicked.connect(lambda _checked=False, i=item: run(i.target)())
            layout.addWidget(button)
            controls[item.label] = button
        elif isinstance(item, catalogue.Toggle):
            variable = catalogue.resolve(inspector, item.textvar)
            button = QPushButton(str(variable.get() if variable is not None else ""), row_widget)
            button.clicked.connect(lambda _checked=False, i=item: run(i.target)())
            if variable is not None:
                _watch(variable, lambda b=button, v=variable: b.setText(str(v.get())))
            layout.addWidget(button)
            controls[item.textvar] = button
        elif isinstance(item, catalogue.Check):
            variable = catalogue.resolve(inspector, item.var)
            if variable is None:
                return
            box = QCheckBox(item.label, row_widget)
            bind_check(box, variable, item.target, setter=box.setChecked, getter_signal=box.toggled)
            layout.addWidget(box)
            controls[item.label] = box
        elif isinstance(item, catalogue.Choice):
            variable = catalogue.resolve(inspector, item.var)
            if variable is None:
                return
            holder = QWidget(row_widget)     # the label and its box stay together, also behind »
            pair = QHBoxLayout(holder)
            pair.setContentsMargins(0, 0, 0, 0)
            pair.addWidget(QLabel(item.label, holder))
            combo = QComboBox(holder)
            combo.addItems(list(catalogue.choices_for(inspector, item)))
            combo.setCurrentText(str(variable.get()))

            def chosen(text, v=variable, i=item) -> None:
                v.set(text)
                if i.target:
                    run(i.target)()

            combo.currentTextChanged.connect(chosen)

            def repaint(c=combo, v=variable) -> None:
                blocker = c.blockSignals(True)
                try:
                    c.setCurrentText(str(v.get()))
                finally:
                    c.blockSignals(blocker)

            _watch(variable, repaint)
            pair.addWidget(combo)
            layout.addWidget(holder)
            controls[item.label] = combo
        elif isinstance(item, catalogue.Entry):
            variable = catalogue.resolve(inspector, item.var)
            if variable is None:
                return
            holder = QWidget(row_widget)
            pair = QHBoxLayout(holder)
            pair.setContentsMargins(0, 0, 0, 0)
            pair.addWidget(QLabel(item.label, holder))
            edit = QLineEdit(str(variable.get()), holder)
            edit.setMaximumWidth(12 * max(int(item.width), 4))
            edit.editingFinished.connect(lambda e=edit, v=variable: v.set(e.text()))
            _watch(variable, lambda e=edit, v=variable: e.setText(str(v.get())) if e.text() != str(v.get()) else None)
            pair.addWidget(edit)
            layout.addWidget(holder)
            controls[item.label] = edit
        elif isinstance(item, catalogue.Text):
            layout.addWidget(QLabel(item.text, row_widget))
        elif isinstance(item, catalogue.Radio):
            variable = catalogue.resolve(inspector, item.var)
            if variable is None:
                return
            tool = QToolButton(row_widget)
            tool.setText(item.label)
            tool.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QMenu(tool)
            group = QActionGroup(menu)
            group.setExclusive(True)
            actions = {}
            for option_label, value in item.options:
                action = QAction(option_label, menu)
                action.setCheckable(True)
                group.addAction(action)
                menu.addAction(action)
                action.triggered.connect(lambda _checked=False, v=value, var=variable, i=item: (var.set(v), run(i.target)()))
                actions[value] = action
                controls[f"{item.label}/{option_label}"] = action

            def repaint(v=variable, acts=actions) -> None:
                current = acts.get(str(v.get()))
                if current is not None:
                    current.setChecked(True)

            repaint()
            _watch(variable, repaint)
            tool.setMenu(menu)
            layout.addWidget(tool)
            controls[item.label] = tool
        elif isinstance(item, catalogue.Menu):
            tool = QToolButton(row_widget)
            tool.setText(item.label + " ▾")
            tool.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QMenu(tool)
            fill_menu(menu, item)
            tool.setMenu(menu)
            layout.addWidget(tool)
            controls[item.label] = tool

    strip = QFrame(parent)
    strip.setObjectName("Inspector3DToolbar")
    strip.setFrameShape(QFrame.Shape.NoFrame)
    line = QHBoxLayout(strip)
    line.setContentsMargins(4, 2, 2, 2)
    line.setSpacing(6)
    tabs = QTabBar(strip)
    tabs.setDrawBase(False)
    tabs.setExpanding(False)
    tabs.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    pages = QStackedWidget(strip)
    tallest = 0
    for row in catalogue.ROWS:
        # the row is laid out as before, then handed to a toolbar widget by widget: the stretch
        # between its left and right groups becomes an expanding spacer
        row_widget = QWidget()
        layout = QHBoxLayout(row_widget)
        # a row's hint text goes after its controls: a toolbar too short for the row puts its END
        # behind », and the controls are what must stay in reach (Carry's 70-character hint came
        # first and pushed every control behind it in a 700-px scene)
        hints = [item for item in row.left if isinstance(item, catalogue.Text)]
        for item in [item for item in row.left if not isinstance(item, catalogue.Text)] + hints:
            add(layout, row_widget, item)
        layout.addStretch(1)
        for item in row.right:
            add(layout, row_widget, item)
        bar = QToolBar(row.title)
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        while layout.count():
            entry = layout.takeAt(0)
            if entry.widget() is not None:
                bar.addWidget(entry.widget())
            elif entry.spacerItem() is not None:
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                bar.addWidget(spacer)
        row_widget.deleteLater()
        tallest = max(tallest, bar.sizeHint().height())
        tabs.addTab(row.title)
        tabs.setTabToolTip(tabs.count() - 1, " ".join([f"The 3D scene's {row.title} controls."]
                                                       + [hint.text for hint in hints]))
        pages.addWidget(bar)
    tabs.currentChanged.connect(pages.setCurrentIndex)
    hide_button = QToolButton(strip)
    hide_button.setAutoRaise(True)
    hide_button.setArrowType(Qt.ArrowType.UpArrow)
    hide_button.setFixedSize(20, 20)
    hide_button.setToolTip("Hide this toolbar (more room for the 3D scene)")
    line.addWidget(tabs, 0, Qt.AlignmentFlag.AlignVCenter)
    line.addWidget(pages, 1)
    line.addWidget(hide_button, 0, Qt.AlignmentFlag.AlignVCenter)
    strip.setFixedHeight(max(tallest, tabs.sizeHint().height()) + 4)
    strip.controls = controls
    strip.tabs = tabs
    strip.pages = pages
    strip.hide_button = hide_button
    return strip
