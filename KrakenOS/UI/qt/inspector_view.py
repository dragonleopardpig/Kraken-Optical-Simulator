"""The real Open 3D inspector, inside the Qt shell (docs/design_qt_migration.md phase 5a).

`SceneViewport` (qt/viewport.py) draws the scene; this hosts the Tk shell's own `Kraken3DInspector`
-- the same object, the same VTK core, the same input handlers -- on a Qt VTK widget (bugs/0906).
Nothing about picking, orbiting or dragging is re-implemented here: this module only turns Qt input
into the `viewport_events` the inspector's handlers already read, in the order the Tk bindings
delivered it:

* a mouse button goes to the handler `viewport_events.button_handler` names (Shift + left pans,
  like the middle button) and is consumed -- the Tk inspector replaces the VTK widget's own button
  bindings the same way, so VTK's interactor style never sees a click;
* a bare move reaches VTK first (its MouseMoveEvent observer runs the hover pick) and then the
  "hover" handler, which is the order Tk's ``add="+"`` binding ran them in;
* the wheel is VTK's (zoom), as it is under Tk;
* a key reaches VTK first and then the inspector's shortcut table; Alt alone flips edge hover;
* the right button's press runs the inspector's own right-click handler. Its menu builders are
  handed a `context_menu.MenuModel` instead of a `tk.Menu` (the inspector sees
  `show_context_menu` installed), and `show_context_menu` renders that record as a QMenu whose
  actions run the builders' own callables (bugs/0907).

The toolkit-free rules (the cursor table, the modifier bits) are plain functions so a guard can
check them without Qt.
"""
from __future__ import annotations

from KrakenOS.UI.viewport_events import ALT, CONTROL, SHIFT, ViewportEvent, button_handler

#: the Tk cursor names the inspector asks for -> the Qt cursor shape that looks the same
QT_CURSOR_SHAPES = {
    "": "ArrowCursor",
    "crosshair": "CrossCursor",
    "fleur": "SizeAllCursor",
    "none": "BlankCursor",
    "sb_v_double_arrow": "SizeVerCursor",
    "X_cursor": "ForbiddenCursor",
}

#: buttons whose PRESS is not routed yet, and why -- none since the context menus came (0907)
DEFERRED_PRESSES: dict = {}


def qt_cursor_shape(name: str) -> str:
    """The Qt cursor shape for a Tk cursor name; an unknown name falls back to the arrow."""
    return QT_CURSOR_SHAPES.get(str(name), "ArrowCursor")


def modifier_state(*, shift: bool, control: bool, alt: bool) -> int:
    """The Tk-convention modifier bitmask the handlers test."""
    return (SHIFT if shift else 0) | (CONTROL if control else 0) | (ALT if alt else 0)


def routed_kind(button: int, state: int, phase: str) -> "str | None":
    """Which handler a button event goes to, or None when it is deliberately not routed."""
    if phase == "press" and int(button) in DEFERRED_PRESSES:
        return None
    try:
        return button_handler(int(button), int(state), phase)
    except ValueError:
        return None


class InspectorView:
    """A Qt VTK widget with the real inspector drawing into it.

    Build it only once its parent is on screen: the VTK widget hands VTK its native window id in
    its constructor (see `KrakenQtMainWindow.build_viewport`).
    """

    def __init__(self, editor, parent, *, status=None) -> None:
        import vtkmodules.vtkInteractionStyle  # noqa: F401  (registers the interactor styles)
        import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  (the GL render window factory)
        from PySide6.QtCore import QObject, Qt
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

        from KrakenOS.UI.open3d_inspector import Kraken3DInspector

        self.editor = editor
        #: where the inspector's status line is shown (a callable taking the text), if anywhere
        self.status = status
        self.widget = QVTKRenderWindowInteractor(parent)
        self.widget.setMouseTracking(True)
        self.widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        #: handler kinds dispatched, oldest first -- what a guard reads to see the routing
        self.dispatched: list[str] = []

        # docs/design_qt_migration.md phase 7f: EXPERIMENTAL until it is the default -- with
        # KRAKEN_QT_TK_FREE set the inspector is built without its hidden Tk window (bugs/0998)
        from KrakenOS.UI.qt.tk_free import tk_free

        self.inspector = Kraken3DInspector(editor, vtk_host=self.widget, tk_window=not tk_free("inspector"))
        # The shell's scene draws imported STEP hardware SOFT (bugs/0958): smooth bodies with one
        # faint pass of their edges, the look of the shell's first 3D view. The user compared the
        # two and called the outlined look "a TK version, not qt". Overlays > Soft STEP bodies
        # switches it either way; the Tk app's default is unchanged.
        self.inspector.soft_step_bodies_var.set(True)
        # ... and the table's elements and the rays in the MODERN look (bugs/0966): the user called
        # everything but the STEP bodies "old TK" and pointed at Optiland's display. Overlays >
        # Modern look switches it either way; the Tk app's default is unchanged.
        self.inspector.modern_look_var.set(True)
        self.inspector._apply_scene_backdrop()
        self.inspector.set_viewport_cursor = self.set_cursor
        self.inspector.viewport_pointer = self.pointer
        self.inspector.show_in_shell = self.show
        # the inspector's menu builders now fill a MenuModel, shown here (bugs/0907)
        self.inspector.show_context_menu = self.show_context_menu
        # the inspector's side panels as non-modal row-form dialogs (phase 5d)
        self.inspector.show_row_form = self.show_row_form
        #: the row-form dialog last shown, for a guard to read and drive
        self.last_form_dialog = None
        #: the QMenu last shown, for a guard to read and trigger
        self.last_menu = None
        if self.inspector.available:
            editor._three_d_inspector = self.inspector
        if status is not None:
            self.inspector.status_var.trace_add("write", lambda *_a: status(self.status_text()))

        view = self

        class _Filter(QObject):
            def eventFilter(self, _obj, event):  # noqa: N802 (Qt's name)
                return view.handle_event(event)

        self._filter = _Filter(self.widget)
        self.widget.installEventFilter(self._filter)

    # ---- what the inspector asks of its viewport -------------------------------------------
    def set_cursor(self, name: str) -> None:
        from PySide6.QtCore import Qt

        if not name:
            self.widget.unsetCursor()
            return
        self.widget.setCursor(getattr(Qt.CursorShape, qt_cursor_shape(name)))

    def pointer(self) -> "tuple[int, int] | None":
        """Where the pointer is over the viewport, in render-window pixels; None when outside."""
        from PySide6.QtGui import QCursor

        local = self.widget.mapFromGlobal(QCursor.pos())
        width, height = self.widget.width(), self.widget.height()
        if not (0 <= local.x() <= width and 0 <= local.y() <= height):
            return None
        ratio = self.pixel_ratio()
        return (int(round(local.x() * ratio)), int(round(local.y() * ratio)))

    def show(self) -> None:
        dock = self.widget.parentWidget()
        while dock is not None and not hasattr(dock, "setFloating"):
            dock = dock.parentWidget()
        if dock is not None:
            dock.show()
            dock.raise_()
        self.widget.setFocus()

    def show_context_menu(self, model, event) -> None:
        """Show a recorded right-click menu at the pointer; its actions run the builder's own
        callables, through `MenuModel.run`, the way a Tk entry click does."""
        from PySide6.QtCore import QPoint

        menu = build_qmenu(model, self.widget)
        model.on_close = menu.close
        inspector = self.inspector

        def forget() -> None:
            # the shell closed it (an entry, Escape, a click away): it is no longer live
            if getattr(inspector, "_active_context_menu", None) is model:
                object.__setattr__(inspector, "_active_context_menu", None)

        menu.aboutToHide.connect(forget)
        self.last_menu = menu
        x_root, y_root = getattr(event, "x_root", None), getattr(event, "y_root", None)
        if x_root is None or y_root is None:
            ratio = self.pixel_ratio() or 1.0
            point = self.widget.mapToGlobal(QPoint(int(event.x / ratio), int(event.y / ratio)))
        else:
            point = QPoint(int(x_root), int(y_root))
        menu.popup(point)

    def show_row_form(self, form, *, on_close=None):
        """Show an inspector side panel as a non-modal row-form dialog; ``on_close`` runs when it
        goes, however it goes (its Close button, an action's close_after, the inspector)."""
        from KrakenOS.UI.qt.dialogs.row_form_dialog import RowFormDialog
        from KrakenOS.UI.uihost import host_of

        dialog = RowFormDialog(form, parent=self.widget.window(), host=host_of(self.inspector))
        if on_close is not None:
            dialog.finished.connect(lambda _result: on_close())
        self.last_form_dialog = dialog
        dialog.show()
        return dialog

    def status_text(self) -> str:
        return str(self.inspector.status_var.get())

    def pixel_ratio(self) -> float:
        # the VTK widget scales its own event positions by this, and its render window is sized
        # in these pixels, so the handlers' positions must be too
        try:
            return float(self.widget._getPixelRatio())
        except Exception:
            return 1.0

    # ---- Qt input -> the inspector's handlers ----------------------------------------------
    def viewport_event(self, event, *, keysym: str = "") -> ViewportEvent:
        from PySide6.QtCore import Qt

        modifiers = event.modifiers()
        state = modifier_state(
            shift=bool(modifiers & Qt.KeyboardModifier.ShiftModifier),
            control=bool(modifiers & Qt.KeyboardModifier.ControlModifier),
            alt=bool(modifiers & Qt.KeyboardModifier.AltModifier))
        if not hasattr(event, "position"):
            return ViewportEvent(state=state, keysym=keysym)
        ratio = self.pixel_ratio()
        local = event.position()
        screen = event.globalPosition()
        return ViewportEvent(int(round(local.x() * ratio)), int(round(local.y() * ratio)), state,
                             keysym, int(screen.x()), int(screen.y()))

    def dispatch(self, kind: str, event) -> None:
        self.dispatched.append(kind)
        self.inspector.dispatch_viewport_event(kind, event)

    def handle_event(self, event) -> bool:
        """Route one Qt event; True when it is consumed (VTK must not see it)."""
        from PySide6.QtCore import QEvent, Qt

        kind = event.type()
        if kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
            button = _button_number(event.button())
            viewport_event = self.viewport_event(event)
            if button == 1 and kind == QEvent.Type.MouseButtonDblClick \
                    and not viewport_event.state & SHIFT:
                # Tk's <Double-Button-1> replaces the second press, as this does
                self.dispatch("double_left", viewport_event)
                return True
            handler = routed_kind(button, viewport_event.state, "press")
            if handler is not None:
                self.widget.setFocus()
                self.dispatch(handler, viewport_event)
            return True
        if kind == QEvent.Type.MouseButtonRelease:
            viewport_event = self.viewport_event(event)
            handler = routed_kind(_button_number(event.button()), viewport_event.state, "release")
            if handler is not None:
                self.dispatch(handler, viewport_event)
            return True
        if kind == QEvent.Type.MouseMove:
            viewport_event = self.viewport_event(event)
            held = _held_button(event.buttons())
            if held is None:
                # VTK first (the hover pick), then the bound handler -- Tk's add="+" order
                self.widget.mouseMoveEvent(event)
                self.dispatch("hover", viewport_event)
                return True
            handler = routed_kind(held, viewport_event.state, "motion")
            if handler is not None:
                self.dispatch(handler, viewport_event)
            return True
        if kind == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Alt:
                self.dispatch("alt_press", self.viewport_event(event, keysym="Alt_L"))
                return False
            _char, keysym = self.widget._GetKeyCharAndKeySym(event)
            # A key the inspector binds (Escape, Delete, `s`) runs ITS handler and stops there, as
            # the Tk binding does -- a specific Tk binding shadows VTK's own <KeyPress>. Forwarding
            # it to VTK as well ran the interactor's key observer too, which handles the same
            # three keys: one `s` flagged TWO bugs, one Escape cancelled the operation AND cleared
            # the selection (bugs/0957). Any other key goes to VTK, as before.
            handled = self.inspector.dispatch_viewport_key(keysym, self.viewport_event(event, keysym=keysym))
            if handled is False:
                self.widget.keyPressEvent(event)
            return True
        if kind == QEvent.Type.KeyRelease and event.key() == Qt.Key.Key_Alt:
            self.dispatch("alt_release", self.viewport_event(event, keysym="Alt_L"))
            return False
        if kind == QEvent.Type.FocusOut:
            self.dispatch("focus_out", ViewportEvent())
            return False
        return False


def qt_menu_text(label: str, accelerator: str = "") -> str:
    """A Tk menu label as QMenu text: a literal "&" doubled (Qt reads one as a mnemonic), the
    accelerator after a tab, where Qt shows shortcut text."""
    text = str(label).replace("&", "&&")
    return f"{text}\t{accelerator}" if accelerator else text


def build_qmenu(model, parent=None, run=None):
    """A QMenu showing `model`'s entries, in order; each action runs its entry via the model."""
    from PySide6.QtWidgets import QMenu

    return fill_qmenu(QMenu(parent), model, run)


def fill_qmenu(menu, model, run=None):
    """Replace ``menu``'s entries by `model`'s, cascades and all, and return it. ``run(model,
    entry)`` is what a click does -- by default the model's own `run`; a shell that must follow
    the model afterwards passes its own (bugs/0972: the ribbon's Layouts / Examples menus are
    filled this way each time they open)."""
    menu.clear()
    for entry in model.entries:
        if entry.kind == "separator":
            menu.addSeparator()
            continue
        if entry.kind == "cascade":
            if entry.submenu is None:
                continue
            submenu = build_qmenu(entry.submenu, menu, run)
            submenu.setTitle(qt_menu_text(entry.label))
            submenu.setEnabled(entry.enabled)
            menu.addMenu(submenu)
            continue
        action = menu.addAction(qt_menu_text(entry.label, entry.accelerator))
        action.setData(entry.kind)
        action.setEnabled(entry.enabled)
        if entry.kind in ("checkbutton", "radiobutton"):
            action.setCheckable(True)
            action.setChecked(entry.checked())
        if run is None:
            action.triggered.connect(lambda _checked=False, e=entry: model.run(e))
        else:
            action.triggered.connect(lambda _checked=False, e=entry, m=model: run(m, e))
    return menu


def qmenu_outline(menu) -> list:
    """A shown QMenu as the (kind, label, enabled[, children]) outline `MenuModel.outline` gives."""
    rows = []
    for action in menu.actions():
        if action.isSeparator():
            rows.append(("separator",))
            continue
        label = action.text().split("\t", 1)[0].replace("&&", "&")
        submenu = action.menu()
        if submenu is not None:
            rows.append(("cascade", label, action.isEnabled(), qmenu_outline(submenu)))
        else:
            rows.append((str(action.data() or "command"), label, action.isEnabled()))
    return rows


def _button_number(button) -> int:
    from PySide6.QtCore import Qt

    return {Qt.MouseButton.LeftButton: 1, Qt.MouseButton.MiddleButton: 2,
            Qt.MouseButton.RightButton: 3}.get(button, 0)


def _held_button(buttons) -> "int | None":
    """The button a drag belongs to: left, then middle, then right, as Tk's B1/B2/B3 order."""
    from PySide6.QtCore import Qt

    for flag, number in ((Qt.MouseButton.LeftButton, 1), (Qt.MouseButton.MiddleButton, 2),
                         (Qt.MouseButton.RightButton, 3)):
        if buttons & flag:
            return number
    return None
