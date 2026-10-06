"""What the Inspection Cell VIEW does, whichever toolkit shows it (bugs/0967).

A cell is a part with up to six camera stations round it (docs/inspection_cell_multi_station.md).
The view shows them composed in one scene: double-click a station to open its layout in the editor,
save that layout and the cell composes again, export the whole cell as one STEP.

Until bugs/0967 all of that lived in the Tk window (`panels/inspection_cell_window.py`), and in the
Qt shell "Open Cell View" opened that Tk window on the hidden Tk root. Measured there: on screen
(mapped, viewable, 1100 x 783) and DEAD -- nothing pumps Tk under Qt, so a 200 ms timer on it never
fired: it did not repaint, took no click, and never noticed a saved layout.

The session is everything but the window:

* the composition (off screen, each station loaded and traced) and its transplant into the renderer
  a view hands over;
* the pick that maps a double-click to a station, and opening that station's layout;
* the file watch -- a timer on the UI HOST, so it fires under either toolkit;
* the STEP export, its file question asked through the host.

A view (the Tk window; the Qt one, `qt/dialogs/inspection_cell_dialog.py`) supplies a VTK renderer
and a way to draw it, shows `status`, and offers `BUTTONS`. Nothing here is toolkit code.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from KrakenOS.UI.services import inspection_cell as cell_service
from KrakenOS.UI.uihost import host_of

TITLE = "Inspection Cell View"
HINT = ("Double-click a station to open its layout in the editor; "
        "saving that layout re-composes the cell.")
COMPOSING = "Composing the cell (each station is loaded and traced)..."
STEP_FILE_TYPES = [("STEP", "*.step *.stp"), ("All files", "*")]


class InspectionCellSession:
    """One cell being viewed: what is drawn, what a click means, what is watched."""

    #: how often the station layout files are looked at
    POLL_MS = 2000
    title = TITLE
    hint = HINT
    #: (label, method) -- the verbs a view offers beside its own Close
    BUTTONS = (("Recompose", "compose"), ("Fit view", "fit_view"), ("Export Cell STEP...", "export_step"))

    def __init__(self, editor: Any, cell_spec: dict, *, host: Any = None) -> None:
        self.editor = editor
        self.cell = cell_service.normalize_cell_spec(cell_spec)
        self.host = host if host is not None else host_of(editor)
        #: how a station's layout is opened in the editor -- a shell with its own layout loader
        #: sets this (the Qt window: its table and scene must follow); None = the editor's own
        self.open_layout: Optional[Callable[[Path], None]] = None
        #: bring the editor's window forward once a station is open in it
        self.raise_editor: Optional[Callable[[], None]] = None
        #: the window file questions belong to
        self.dialog_parent: Any = None
        self.status = ""
        self.report: dict = {}
        self.compose_count = 0
        #: id(actor) -> the face of the station it belongs to (what a double-click resolves)
        self.actor_face: dict[int, str] = {}
        self.actors: list = []
        self.station_mtimes: dict[str, float] = {}
        self.last_pick_hit: Any = None
        self.closed = False
        self._renderer: Any = None
        self._render: Callable[[], None] = lambda: None
        self._last_plotter: Any = None
        self._status_listeners: list = []
        self._watch_handle: Any = None

    # ---- what a view gives and shows ----------------------------------------------------------
    def attach(self, renderer: Any, render: Callable[[], None]) -> None:
        """The view's VTK renderer, and how to draw it."""
        self._renderer = renderer
        self._render = render

    def on_status(self, listener: Callable[[str], None]) -> None:
        self._status_listeners.append(listener)
        listener(self.status)

    def set_status(self, text: str) -> None:
        self.status = str(text)
        for listener in list(self._status_listeners):
            try:
                listener(self.status)
            except Exception:
                pass

    # ---- the composition ----------------------------------------------------------------------
    def compose(self) -> dict:
        """Compose off screen, then transplant every actor into the view's renderer."""
        if self._renderer is None or self.closed:
            return {}
        self.set_status(COMPOSING)
        try:
            self.host.update_idletasks()         # the line is on screen before the long compose
        except Exception:
            pass
        try:
            plotter, report = cell_service.compose_cell_plotter(self.cell, off_screen=True)
        except Exception as exc:
            self.set_status(f"Cell composition failed: {exc}")
            return {}
        self._renderer.RemoveAllViewProps()
        self.actor_face = {}
        self.actors = []
        station_keys: dict[str, str] = {}
        for face, keys in (report.get("station_actor_keys") or {}).items():
            for key in keys:
                station_keys[key] = face
        for key, actor in list(plotter.renderer.actors.items()):
            try:
                self._renderer.AddActor(actor)
            except Exception:
                continue
            self.actors.append(actor)
            face = station_keys.get(key)
            if face:
                self.actor_face[id(actor)] = face
        # the previous off-screen plotter is closed only now: its actors have been replaced
        old, self._last_plotter = self._last_plotter, plotter
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        self.report = report
        self.compose_count += 1
        self.station_mtimes = self.current_station_mtimes()
        self.set_status(cell_service.cell_summary(report))
        self.fit_view()
        return report

    def fit_view(self) -> None:
        if self._renderer is None or self.closed:
            return
        try:
            self._renderer.ResetCamera()
            self._render()
        except Exception:
            pass

    # ---- a click ------------------------------------------------------------------------------
    def face_at(self, x: float, y: float) -> Optional[str]:
        """The station face under a display position, or None.

        A GEOMETRIC pick (vtkCellPicker, the main inspector's picker) -- it works through actor
        user-matrices and needs no hardware selection pass, which the prop picker relies on and
        which an unmapped or off-screen window never does."""
        self.last_pick_hit = None
        if self._renderer is None:
            return None
        actor = None
        try:
            from vtkmodules.vtkRenderingCore import vtkCellPicker

            picker = vtkCellPicker()
            picker.SetTolerance(0.005)
            picker.Pick(float(x), float(y), 0.0, self._renderer)
            actor = picker.GetActor()
        except Exception:
            actor = None
        if actor is None:
            try:
                from vtkmodules.vtkRenderingCore import vtkPropPicker

                picker = vtkPropPicker()
                picker.Pick(float(x), float(y), 0.0, self._renderer)
                actor = picker.GetViewProp()
            except Exception:
                actor = None
        if actor is None:
            return None
        self.last_pick_hit = actor
        return self.actor_face.get(id(actor))

    def double_click(self, x: float, y: float) -> bool:
        """A double-click at a display position: open the station under it, if there is one."""
        face = self.face_at(x, y)
        return bool(face) and self.open_station(face)

    def open_station(self, face: str) -> bool:
        """Load the station's layout into the editor for editing."""
        entry = self.cell["stations"].get(face) or {}
        layout = entry.get("layout")
        if not layout or not Path(layout).exists():
            self.set_status(f"{face}: no station layout to open.")
            return False
        try:
            if self.open_layout is not None:
                self.open_layout(Path(layout))
            else:
                name = f"cell_{face}"
                self.editor.layout_files[name] = Path(layout)
                self.editor.load_layout_by_name(name)
        except Exception as exc:
            self.set_status(f"{face}: could not open {Path(layout).name}: {exc}")
            return False
        self.set_status(f"Opened the {face} station ({Path(layout).name}) in the editor -- Save Layout there "
                        f"and the cell re-composes.")
        if self.raise_editor is not None:
            try:
                self.raise_editor()
            except Exception:
                pass
        return True

    # ---- the file watch -----------------------------------------------------------------------
    def current_station_mtimes(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for face in cell_service.FACE_ORDER:
            entry = self.cell["stations"][face]
            if not entry["enabled"] or not entry["layout"]:
                continue
            try:
                out[face] = Path(entry["layout"]).stat().st_mtime
            except Exception:
                out[face] = -1.0
        return out

    def check_station_files(self) -> bool:
        """True (and re-composed) when a station layout changed on disk since the last compose."""
        if self.closed:
            return False
        if self.current_station_mtimes() != self.station_mtimes:
            self.compose()
            return True
        return False

    def start_watching(self) -> None:
        """Look at the station files every `POLL_MS`, on the HOST's clock, until closed."""
        if self.closed or self._watch_handle is not None:
            return
        self._watch_handle = self.host.after(self.POLL_MS, self._poll)

    def _poll(self) -> None:
        self._watch_handle = None
        if self.closed:
            return
        try:
            self.check_station_files()
        except Exception:
            pass
        self.start_watching()

    # ---- export -------------------------------------------------------------------------------
    def export_step(self) -> str:
        """Ask where, then write the cell as one STEP. Returns the path written, or ""."""
        options = {"parent": self.dialog_parent} if self.dialog_parent is not None else {}
        path = self.host.asksaveasfilename(title="Export Cell STEP", defaultextension=".step",
                                           filetypes=STEP_FILE_TYPES, **options)
        if not path:
            return ""
        self.set_status("Exporting the cell STEP...")
        try:
            self.host.update_idletasks()
            report = cell_service.export_cell_step(self.cell, path)
        except Exception as exc:
            self.set_status(f"Cell STEP failed: {exc}")
            return ""
        self.set_status(f"Cell STEP written: {Path(path).name} ({len(report['stations'])} stations)")
        return str(path)

    # ---- the end ------------------------------------------------------------------------------
    def close(self) -> None:
        """The view is going: stop watching, let go of the scene. The view then finalizes its own
        render window (VTK wants that done before the widget goes)."""
        if self.closed:
            return
        self.closed = True
        if self._watch_handle is not None:
            try:
                self.host.after_cancel(self._watch_handle)
            except Exception:
                pass
            self._watch_handle = None
        self._render = lambda: None
        try:
            if self._last_plotter is not None:
                self._last_plotter.close()
        except Exception:
            pass
        self._last_plotter = None
        try:
            if self._renderer is not None:
                self._renderer.RemoveAllViewProps()
        except Exception:
            pass


def open_inspection_cell_view(owner: Any, cell_spec: dict) -> Optional[InspectionCellSession]:
    """Open the cell's view in whichever shell is running.

    The shell's own window when it has one (`show_inspection_cell` -- the Qt shell), else the Tk
    window. Returns the session; None when only the pyvista window could be shown (Tk, with no
    VTK/Tk render widget)."""
    shell = owner.__dict__.get("show_inspection_cell") if hasattr(owner, "__dict__") else None
    if callable(shell):
        return shell(InspectionCellSession(owner, cell_spec))
    from KrakenOS.UI.panels import inspection_cell_window

    window = inspection_cell_window.open_inspection_cell_window(owner, cell_spec)
    return None if window is None else window.session
