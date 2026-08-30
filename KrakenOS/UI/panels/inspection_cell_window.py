"""Embedded Inspection Cell view (bugs/0664, phase 3 of the multi-station cell).

The pyvista pop-up of phase 2 showed the cell; this window makes it ITERATIVE: a Tk
Toplevel hosting a VTK render widget (the same embedding the main 3D inspector uses),
filled by transplanting the actors of an off-screen composition; double-clicking a
station opens its layout in the main editor; the window watches the station layout
files and re-composes when one is saved.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any

from KrakenOS.UI.services.inspection_cell import (
    FACE_ORDER,
    cell_summary,
    compose_cell_plotter,
    export_cell_step,
    normalize_cell_spec,
)


class InspectionCellWindow(tk.Toplevel):
    """One window = one cell. ``available`` is False (with ``unavailable_reason``) when the
    VTK/Tk widget cannot be created -- the caller falls back to the pyvista window."""

    POLL_MS = 2000

    def __init__(self, editor, cell_spec: dict[str, Any]) -> None:
        parent = editor.winfo_toplevel() if hasattr(editor, "winfo_toplevel") else editor
        super().__init__(parent)
        self.title("Inspection Cell View")
        self.editor = editor
        self.cell = normalize_cell_spec(cell_spec)
        self.available = False
        self.unavailable_reason = ""
        self._renderer = None
        self._vtk_widget = None
        self._vtk_interactor = None
        self._actor_face: dict[int, str] = {}
        self._actors: list = []
        self._last_plotter = None
        self._report: dict[str, Any] = {}
        self._station_mtimes: dict[str, float] = {}
        self._compose_count = 0
        self.status_var = tk.StringVar(value="")

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
        ttk.Button(toolbar, text="Recompose", command=self.compose).pack(side="left")
        ttk.Button(toolbar, text="Fit view", command=self.fit_view).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export Cell STEP...", command=self.export_step).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=self.destroy).pack(side="left", padx=(6, 0))
        ttk.Label(toolbar, text="Double-click a station to open its layout in the editor; "
                                "saving that layout re-composes the cell.").pack(side="left", padx=(14, 0))

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
        self.available = True
        self.compose()
        self.after(self.POLL_MS, self._poll_station_files)

    # ---- composition -------------------------------------------------------------
    def compose(self) -> dict[str, Any]:
        """Off-screen composition, then transplant every actor into this window's renderer."""
        if self._renderer is None:
            return {}
        self.status_var.set("Composing the cell (each station is loaded and traced)...")
        try:
            self.update_idletasks()
        except Exception:
            pass
        try:
            plotter, report = compose_cell_plotter(self.cell, off_screen=True)
        except Exception as exc:
            self.status_var.set(f"Cell composition failed: {exc}")
            return {}
        self._renderer.RemoveAllViewProps()
        self._actor_face = {}
        self._actors = []
        station_keys: dict[str, str] = {}
        for face, keys in (report.get("station_actor_keys") or {}).items():
            for key in keys:
                station_keys[key] = face
        for key, actor in list(plotter.renderer.actors.items()):
            try:
                self._renderer.AddActor(actor)
            except Exception:
                continue
            self._actors.append(actor)
            face = station_keys.get(key)
            if face:
                self._actor_face[id(actor)] = face
        old = self._last_plotter
        self._last_plotter = plotter
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        self._report = report
        self._compose_count += 1
        self._station_mtimes = self._current_station_mtimes()
        self.status_var.set(cell_summary(report))
        self.fit_view()
        return report

    def fit_view(self) -> None:
        if self._renderer is None:
            return
        try:
            self._renderer.ResetCamera()
            self._render()
        except Exception:
            pass

    def _render(self) -> None:
        try:
            self._vtk_widget.GetRenderWindow().Render()
        except Exception:
            pass

    # ---- interaction ---------------------------------------------------------------
    def _on_left_button_press(self, obj, event) -> None:
        try:
            if int(self._vtk_interactor.GetRepeatCount()) < 1:  # a double-click reports repeat 1
                return
            x, y = self._vtk_interactor.GetEventPosition()
        except Exception:
            return
        face = self.face_at(x, y)
        if face:
            self.open_station(face)

    def face_at(self, x: int, y: int) -> str | None:
        """The station face under a display position, or None.

        A GEOMETRIC pick (vtkCellPicker, the main inspector's picker) -- it works
        through actor user-matrices and needs no hardware selection pass, which the
        prop picker relies on and which an unmapped/off-screen window never does."""
        self._last_pick_hit = None
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
        self._last_pick_hit = actor
        return self._actor_face.get(id(actor))

    def open_station(self, face: str) -> bool:
        """Load the station's layout into the main editor for editing."""
        entry = self.cell["stations"].get(face) or {}
        layout = entry.get("layout")
        if not layout or not Path(layout).exists():
            self.status_var.set(f"{face}: no station layout to open.")
            return False
        name = f"cell_{face}"
        try:
            self.editor.layout_files[name] = Path(layout)
            self.editor.load_layout_by_name(name)
        except Exception as exc:
            self.status_var.set(f"{face}: could not open {Path(layout).name}: {exc}")
            return False
        self.status_var.set(
            f"Opened the {face} station ({Path(layout).name}) in the editor -- Save Layout there "
            f"and the cell re-composes."
        )
        try:
            self.editor.winfo_toplevel().lift()
        except Exception:
            pass
        return True

    # ---- file watching -------------------------------------------------------------
    def _current_station_mtimes(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for face in FACE_ORDER:
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
        current = self._current_station_mtimes()
        if current != self._station_mtimes:
            self.compose()
            return True
        return False

    def _poll_station_files(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            self.check_station_files()
        except Exception:
            pass
        try:
            self.after(self.POLL_MS, self._poll_station_files)
        except Exception:
            pass

    # ---- export ---------------------------------------------------------------------
    def export_step(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export Cell STEP", defaultextension=".step",
            filetypes=[("STEP", "*.step *.stp"), ("All files", "*")], parent=self,
        )
        if not path:
            return
        self.status_var.set("Exporting the cell STEP...")
        try:
            self.update_idletasks()
            report = export_cell_step(self.cell, path)
        except Exception as exc:
            self.status_var.set(f"Cell STEP failed: {exc}")
            return
        self.status_var.set(f"Cell STEP written: {Path(path).name} ({len(report['stations'])} stations)")

    def destroy(self) -> None:
        try:
            if self._last_plotter is not None:
                self._last_plotter.close()
        except Exception:
            pass
        self._last_plotter = None
        # Tear the VTK render window down BEFORE the Tk widget (VTK warns loudly --
        # "TkRenderWidget destroyed before its vtkRenderWindow" -- when done the other way).
        try:
            if self._renderer is not None:
                self._renderer.RemoveAllViewProps()
            if self._vtk_widget is not None:
                self._vtk_widget.GetRenderWindow().Finalize()
        except Exception:
            pass
        super().destroy()


def open_inspection_cell_window(editor, cell_spec: dict[str, Any]):
    """Open the embedded view; when VTK/Tk is unavailable fall back to the pyvista window."""
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
