"""The Tk window over an Inspection Cell view session (bugs/0664; a view since bugs/0967).

What it does -- compose the cell and transplant its actors, map a double-click to a station and
open that station's layout, watch the station files, export the cell STEP -- is
`KrakenOS.UI.services.inspection_cell_session.InspectionCellSession`, shared with the Qt window
(`qt/dialogs/inspection_cell_dialog.py`). This is the Tk view: a Toplevel hosting a VTK render
widget (the same embedding the main 3D inspector uses), the session's buttons and its status line.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from KrakenOS.UI.services.inspection_cell import compose_cell_plotter, normalize_cell_spec
from KrakenOS.UI.services.inspection_cell_session import InspectionCellSession


class InspectionCellWindow(tk.Toplevel):
    """One window = one cell. ``available`` is False (with ``unavailable_reason``) when the
    VTK/Tk widget cannot be created -- the caller falls back to the pyvista window.

    ``session`` -- the `InspectionCellSession` to show; or ``cell_spec`` to make one."""

    def __init__(self, editor, cell_spec: "dict[str, Any] | None" = None, *,
                 session: "InspectionCellSession | None" = None) -> None:
        parent = editor.winfo_toplevel() if hasattr(editor, "winfo_toplevel") else editor
        super().__init__(parent)
        self.session = session if session is not None else InspectionCellSession(editor, cell_spec or {})
        self.editor = self.session.editor
        self.title(self.session.title)
        self.available = False
        self.unavailable_reason = ""
        self._renderer = None
        self._vtk_widget = None
        self._vtk_interactor = None
        self.status_var = tk.StringVar(master=self, value="")

        from KrakenOS.UI import layout_editor as le

        try:
            le._load_3d_backends()
        except Exception as exc:  # pragma: no cover - environment
            self.unavailable_reason = f"3D backends failed to load: {exc}"
        widget_cls = getattr(le, "vtkTkRenderWindowInteractor", None)
        renderer_cls = getattr(le, "vtkRenderer", None)
        if widget_cls is None or renderer_cls is None:
            self.unavailable_reason = self.unavailable_reason or (
                getattr(le, "_VTK_TK_UNAVAILABLE_REASON", "") or "VTK/Tk render widget unavailable"
            )
            ttk.Label(self, text=f"Embedded cell view unavailable: {self.unavailable_reason}", padding=12).grid(
                row=0, column=0
            )
            return

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(self, padding=(8, 6))
        toolbar.grid(row=0, column=0, sticky="ew")
        for index, (label, method) in enumerate(self.session.BUTTONS):
            ttk.Button(toolbar, text=label, command=getattr(self.session, method)).pack(
                side="left", padx=(6 if index else 0, 0))
        ttk.Button(toolbar, text="Close", command=self.destroy).pack(side="left", padx=(6, 0))
        ttk.Label(toolbar, text=self.session.hint).pack(side="left", padx=(14, 0))

        host = ttk.Frame(self, padding=0)
        host.columnconfigure(0, weight=1)
        host.rowconfigure(0, weight=1)
        host.grid(row=1, column=0, sticky="nsew")
        try:
            le._prepare_vtk_tk_widget(host)
            self._vtk_widget = widget_cls(host, width=1100, height=720)
            self._vtk_widget.grid(row=0, column=0, sticky="nsew")
            render_window = self._vtk_widget.GetRenderWindow()
            self._renderer = renderer_cls()
            render_window.AddRenderer(self._renderer)
            self._renderer.SetBackground(1.0, 1.0, 1.0)
            self._vtk_interactor = render_window.GetInteractor()
        except Exception as exc:  # pragma: no cover - environment
            self.unavailable_reason = f"VTK/Tk widget failed: {exc}"
            ttk.Label(self, text=f"Embedded cell view unavailable: {self.unavailable_reason}", padding=12).grid(
                row=1, column=0
            )
            return
        try:
            from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera

            self._vtk_interactor.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
        except Exception:
            pass
        if self._vtk_interactor is not None:
            self._vtk_interactor.AddObserver("LeftButtonPressEvent", self._on_left_button_press)
        ttk.Label(self, textvariable=self.status_var, padding=(8, 4), justify="left").grid(row=2, column=0, sticky="ew")
        self.session.dialog_parent = self
        self.session.raise_editor = self._lift_editor
        self.session.attach(self._renderer, self._render)
        self.session.on_status(self.status_var.set)
        self.available = True
        self.session.compose()
        self.session.start_watching()

    # ---- the view's own two jobs: draw, and tell the session where a double-click fell ---------
    def _render(self) -> None:
        try:
            self._vtk_widget.GetRenderWindow().Render()
        except Exception:
            pass

    def _on_left_button_press(self, obj, event) -> None:
        try:
            if int(self._vtk_interactor.GetRepeatCount()) < 1:  # a double-click reports repeat 1
                return
            x, y = self._vtk_interactor.GetEventPosition()
        except Exception:
            return
        self.session.double_click(x, y)

    def _lift_editor(self) -> None:
        self.editor.winfo_toplevel().lift()

    # ---- the session's verbs and state, under the names this window has always had -------------
    @property
    def cell(self) -> dict:
        return self.session.cell

    @property
    def _report(self) -> dict:
        return self.session.report

    @property
    def _actor_face(self) -> dict:
        return self.session.actor_face

    @property
    def _compose_count(self) -> int:
        return self.session.compose_count

    @property
    def _last_pick_hit(self):
        return self.session.last_pick_hit

    def compose(self) -> dict:
        return self.session.compose()

    def fit_view(self) -> None:
        self.session.fit_view()

    def face_at(self, x: int, y: int) -> "str | None":
        return self.session.face_at(x, y)

    def open_station(self, face: str) -> bool:
        return self.session.open_station(face)

    def check_station_files(self) -> bool:
        return self.session.check_station_files()

    def export_step(self) -> None:
        self.session.export_step()

    def destroy(self) -> None:
        self.session.close()
        # Tear the VTK render window down BEFORE the Tk widget (VTK warns loudly --
        # "TkRenderWidget destroyed before its vtkRenderWindow" -- when done the other way).
        try:
            if self._vtk_widget is not None:
                self._vtk_widget.GetRenderWindow().Finalize()
        except Exception:
            pass
        super().destroy()


def open_inspection_cell_window(editor, cell_spec: dict[str, Any]):
    """Open the Tk view; when VTK/Tk is unavailable fall back to the pyvista window."""
    window = InspectionCellWindow(editor, cell_spec)
    if window.available:
        return window
    reason = window.unavailable_reason
    try:
        window.destroy()
    except Exception:
        pass
    plotter, report = compose_cell_plotter(normalize_cell_spec(cell_spec))
    try:
        editor.status_var.set(f"Embedded cell view unavailable ({reason}); opened the pyvista window.")
    except Exception:
        pass
    plotter.show(title="KrakenOS Inspection Cell")
    return None
