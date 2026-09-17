"""Pin down what the big cyan filled disc on the OBJECT plane really is when the
detector coverage overlay is on, in the *default* reference-surface state (we do
NOT force show_reference_surfaces, unlike the earlier verify script).

For every actor we print full bounds (incl. z), opacity, color, representation
and the mapper-input cell count so a filled disc (many polys) is distinguishable
from a thin ring/polyline. Hard 200s alarm so it can never wedge.
"""
from __future__ import annotations

import signal
import vtk

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

CAMERA = "Allied Vision hr25MCX"


def _alarm(*_):
    raise SystemExit("TIMEOUT")


def _ncells(actor):
    try:
        mp = actor.GetMapper()
        inp = mp.GetInput()
        return int(inp.GetNumberOfCells())
    except Exception:
        return -1


def dump(ren, tag):
    actors = ren.GetActors(); actors.InitTraversal()
    rows = []
    for _ in range(actors.GetNumberOfItems()):
        a = actors.GetNextActor()
        if a is None:
            continue
        b = a.GetBounds()
        zc = 0.5 * (b[4] + b[5])
        hx = 0.5 * (b[1] - b[0]); hy = 0.5 * (b[3] - b[2])
        p = a.GetProperty()
        rows.append((round(zc, 1), round(hx, 2), round(hy, 2),
                     round(p.GetOpacity(), 2), p.GetRepresentationAsString()[:4],
                     tuple(round(c, 2) for c in p.GetColor()), _ncells(a)))
    print(f"\n=== {tag} : {len(rows)} actors (z, hx, hy, op, rep, color, ncells) ===")
    for r in sorted(rows):
        flag = "  <== FILLED DISC?" if (r[6] > 200 and abs(r[1] - r[2]) < 0.5 and r[3] > 0.05) else ""
        print(f"  z={r[0]:7.1f} half=({r[1]:6.2f},{r[2]:6.2f}) op={r[3]:.2f} {r[4]} "
              f"col={r[5]} ncells={r[6]}{flag}")


def main() -> int:
    signal.signal(signal.SIGALRM, _alarm); signal.alarm(200)
    app = KrakenLayoutEditor()
    try:
        names = list(getattr(app, "machine_vision_names", []) or [])
        target = next((n for n in names if "Measured" in n and "150" in n), None) or (names[0] if names else None)
        app.load_layout_by_name(target)
        app.update_idletasks()
        app.camera_model_var.set(CAMERA)
        app._on_camera_model_changed()
        app.update_idletasks()

        app.open_3d_view()
        app.update_idletasks(); app.update()
        insp = app._three_d_inspector
        print("default show_reference_surfaces =", insp.show_reference_surfaces_var.get())

        insp.show_detector_overlays_var.set(True)
        insp.refresh_from_editor(force_retrace=True)
        app.update_idletasks(); app.update()
        ren = insp._renderer
        dump(ren, "Det=ON, reference surfaces at DEFAULT")

        # Head-on object-plane shot in the default state.
        cam = ren.GetActiveCamera()
        cam.ParallelProjectionOn()
        cam.SetFocalPoint(0, 0, 0); cam.SetPosition(0, 0, -200); cam.SetViewUp(0, 1, 0)
        cam.SetParallelScale(20.0)
        ren.ResetCameraClippingRange(); ren.GetRenderWindow().Render()
        w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(ren.GetRenderWindow()); w2i.Update()
        wr = vtk.vtkPNGWriter(); wr.SetFileName("/tmp/diag_objdisc_default.png")
        wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
        print("\nscreenshot -> /tmp/diag_objdisc_default.png")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
