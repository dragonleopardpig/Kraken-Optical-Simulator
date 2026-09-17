"""Reproduce the two user recordings (251, 078) with the bug-0033 fixes applied:
auto-fill on load (-> covering), reference surfaces ON (the user had them on, that
is why the filled clear-aperture disks showed), detector overlay ON. Render from
the exact recorded camera poses so the screenshots are directly comparable to the
user's, to confirm: (251) image circle now covers the sensor, no filled disk;
(078) object cyan circle gone, FOV box clean; labels readable + non-overlapping.
Hard 200s alarm.
"""
from __future__ import annotations

import signal
import vtk

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

CAMERA = "Allied Vision hr25MCX"

# Clean angled framings (recorded poses over-zoom / clip with this window's
# aspect ratio). "img" frames the image plane where Sensor + image-circle labels
# cluster; "obj" frames the object plane / FOV-box + its label.
VIEWS = {
    "img": dict(pos=(-70, 45, 560), foc=(0, 0, 625), up=(0.0, 1.0, 0.0), pscale=24.0),
    "obj": dict(pos=(-70, 45, -65), foc=(0, 0, 0), up=(0.0, 1.0, 0.0), pscale=18.0),
}


def _alarm(*_):
    raise SystemExit("TIMEOUT")


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
              "| max_real_img =", app._field_metrics_summary().get("max_real_image_height"))

        app.open_3d_view()
        app.update_idletasks(); app.update()
        insp = app._three_d_inspector
        if hasattr(insp, "show_reference_surfaces_var"):
            insp.show_reference_surfaces_var.set(True)   # match the user's session
        insp.show_detector_overlays_var.set(True)
        insp.refresh_from_editor(force_retrace=True)
        app.update_idletasks(); app.update()

        ren = insp._renderer
        cam = ren.GetActiveCamera()
        for tag, v in VIEWS.items():
            cam.ParallelProjectionOn()
            cam.SetPosition(*v["pos"]); cam.SetFocalPoint(*v["foc"]); cam.SetViewUp(*v["up"])
            cam.SetParallelScale(v["pscale"])
            ren.ResetCameraClippingRange()
            ren.GetRenderWindow().Render()
            w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(ren.GetRenderWindow()); w2i.Update()
            out = f"/tmp/repro_{tag}.png"
            wr = vtk.vtkPNGWriter(); wr.SetFileName(out)
            wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
            print(f"screenshot ({tag}) -> {out}")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
