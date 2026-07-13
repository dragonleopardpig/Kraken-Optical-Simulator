"""Minimal Tk + vtkTkRenderWindowInteractor teardown repro (bug 0294).

Reproduces the "A TkRenderWidget is being destroyed before it[s] associated
vtkRenderWindow is destroyed" warning + segfault-on-exit, and lets us compare
teardown sequences to find one that exits cleanly.

Run headless:  xvfb-run -a python bugs/probe_0294_vtk_teardown.py <mode>
Modes: naive | finalize_then_destroy | robust | robust_norefs
Exit 0 + "CLEAN EXIT" printed = no segfault for that mode.
"""
from __future__ import annotations

import sys
import tkinter as tk

import vtkmodules.vtkInteractionStyle  # noqa: F401
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
from vtkmodules.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor
from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer


def build():
    root = tk.Tk()
    root.geometry("400x300")
    widget = vtkTkRenderWindowInteractor(root, width=400, height=300)
    widget.pack(fill="both", expand=1)
    rw = widget.GetRenderWindow()
    ren = vtkRenderer()
    rw.AddRenderer(ren)
    cone = vtkConeSource()
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(cone.GetOutputPort())
    actor = vtkActor()
    actor.SetMapper(mapper)
    ren.AddActor(actor)
    iren = rw.GetInteractor()
    iren.Initialize()
    rw.Render()
    root.update()
    root.update_idletasks()
    return root, widget, rw, ren, iren


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "finalize_then_destroy"
    root, widget, rw, ren, iren = build()
    print(f"built OK, tearing down with mode={mode!r}", flush=True)

    if mode == "naive":
        widget.destroy()
        root.destroy()

    elif mode == "finalize_then_destroy":
        # what _destroy_vtk_render_window + .destroy() currently does
        rw.Finalize()
        widget.destroy()
        root.destroy()

    elif mode == "robust":
        # detach the render window from the interactor + widget, THEN destroy
        try:
            iren.TerminateApp()
        except Exception:
            pass
        rw.Finalize()
        try:
            rw.SetInteractor(None)
        except Exception:
            pass
        widget.destroy()
        root.destroy()

    elif mode == "robust_norefs":
        # robust + drop every python ref to the VTK objects before exit
        try:
            iren.TerminateApp()
        except Exception:
            pass
        rw.Finalize()
        try:
            rw.SetInteractor(None)
        except Exception:
            pass
        widget.destroy()
        root.destroy()
        del iren, ren, rw, widget, root

    else:
        print(f"unknown mode {mode!r}")
        return 2

    print("CLEAN EXIT", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
