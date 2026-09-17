"""Verify bug-0033 fixes headless: (a) auto-fill, (c) object/image surface disk
suppression under Det, (b) billboard labels present. Head-on image-plane shot.
Hard 200s alarm so it can never wedge.
"""
from __future__ import annotations

import signal
import numpy as np
import vtk

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

CAMERA = "Allied Vision hr25MCX"


def _alarm(*_):
    raise SystemExit("TIMEOUT")


def _surface_opacities(ren):
    """Opacity of Surface-rep actors near object (z~0) and image (z~625) planes
    that are translucent fills (not the thin overlay lines)."""
    out = []
    actors = ren.GetActors(); actors.InitTraversal()
    for _ in range(actors.GetNumberOfItems()):
        a = actors.GetNextActor()
        if a is None:
            continue
        b = a.GetBounds()
        zc = 0.5 * (b[4] + b[5])
        hx = 0.5 * (b[1] - b[0]); hy = 0.5 * (b[3] - b[2])
        if (abs(zc) < 12 or abs(zc - 625) < 12) and a.GetProperty().GetRepresentationAsString() == "Surface":
            out.append((("OBJ" if abs(zc) < 12 else "IMG"), round(hx, 2), round(hy, 2),
                        round(a.GetProperty().GetOpacity(), 3)))
    return sorted(out)


def _count_text_actors(ren):
    n = 0
    props = ren.GetViewProps(); props.InitTraversal()
    for _ in range(props.GetNumberOfItems()):
        p = props.GetNextProp()
        if p is not None and "TextActor" in p.GetClassName():
            n += 1
    return n


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
        print("(autofill) field =", app.field_type_var.get(), "/", app.field_value_var.get(),
              "| image diam =", app.rows[-1].diameter,
              "| max_real_img =", app._field_metrics_summary().get("max_real_image_height"))

        app.open_3d_view()
        app.update_idletasks(); app.update()
        insp = app._three_d_inspector
        # Reference surfaces ON so the object/image clear-aperture disks are drawn.
        if hasattr(insp, "show_reference_surfaces_var"):
            insp.show_reference_surfaces_var.set(True)

        for det in (False, True):
            insp.show_detector_overlays_var.set(det)
            insp.refresh_from_editor(force_retrace=True)
            app.update_idletasks(); app.update()
            ren = insp._renderer
            print(f"\n--- Det={det} ---")
            print("  surface fills:", _surface_opacities(ren))
            print("  text/billboard label actors:", _count_text_actors(ren))

        # Head-on image-plane screenshot (Det on).
        ren = insp._renderer
        cam = ren.GetActiveCamera()
        cam.ParallelProjectionOn()
        cam.SetFocalPoint(0, 0, 625); cam.SetPosition(0, 0, 425); cam.SetViewUp(0, 1, 0)
        cam.SetParallelScale(26.0)
        ren.ResetCameraClippingRange()
        ren.GetRenderWindow().Render()
        w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(ren.GetRenderWindow()); w2i.Update()
        wr = vtk.vtkPNGWriter(); wr.SetFileName("/tmp/verify_0033_img.png")
        wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
        print("\nscreenshot -> /tmp/verify_0033_img.png")

        cam.SetFocalPoint(0, 0, 0); cam.SetPosition(0, 0, -200); cam.SetParallelScale(20.0)
        ren.ResetCameraClippingRange(); ren.GetRenderWindow().Render()
        w2i2 = vtk.vtkWindowToImageFilter(); w2i2.SetInput(ren.GetRenderWindow()); w2i2.Update()
        wr2 = vtk.vtkPNGWriter(); wr2.SetFileName("/tmp/verify_0033_obj.png")
        wr2.SetInputConnection(w2i2.GetOutputPort()); wr2.Write()
        print("screenshot -> /tmp/verify_0033_obj.png")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
