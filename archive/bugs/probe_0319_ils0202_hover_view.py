"""Render the ILS0202 LED front aperture to see if its clear-aperture window is
hoverable, and from the user's 17:02 oblique angle.

The user flagged "can't highlight either clear aperture edge"; the 17:02 hover pick
resolved to F005 (a side wall). ILS0202's front aperture is THREE concentric
axis-facing rim windows (faces 266/306/185) recessed at z=7..14. Render it to see
the recess/occlusion.
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
OUT = Path("attachment/open3d_ils0202_hover_probe")

CAM_POS = (728.4724199364874, 378.3593514853171, -219.01984621565677)
CAM_FOC = (109.2966495879656, 1.5124859837535156, 43.76648289042342)
CAM_UP = (-0.31184041783803396, -0.142676475093363, -0.9393609408834995)
CAM_PSCALE = 100.2280069749051


def _settle(w, d=0.35):
    w.update_idletasks(); w.update(); time.sleep(d); w.update_idletasks(); w.update()


def _snap(insp, path: Path):
    from vtkmodules.vtkIOImage import vtkPNGWriter
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter
    path.parent.mkdir(parents=True, exist_ok=True)
    rw = insp._vtk_widget.GetRenderWindow()
    rw.SetSize(1400, 900)
    rw.Render()
    cap = vtkWindowToImageFilter(); cap.SetInput(rw); cap.ReadFrontBufferOff(); cap.Update()
    w = vtkPNGWriter(); w.SetFileName(str(path)); w.SetInputConnection(cap.GetOutputPort()); w.Write()
    print(f"  wrote {path} ({path.stat().st_size if path.exists() else 0} bytes)")


def _cam(insp, pos, foc, up, pscale):
    ren = insp._renderer
    c = ren.GetActiveCamera()
    c.SetPosition(*pos); c.SetFocalPoint(*foc); c.SetViewUp(*up)
    c.ParallelProjectionOn(); c.SetParallelScale(pscale)
    ren.ResetCameraClippingRange()


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.open_3d_view()
        _settle(app, 0.4)
        insp = app._three_d_inspector
        insp.geometry("1400x900+20+20")
        insp.show_rotation_handles_var.set(False)
        insp.show_placement_handles_var.set(False)
        insp.deiconify(); insp.lift()
        _settle(insp, 0.4)
        # Show + select the LED overlay so its actor is in the scene.
        app.select_step_component("led")
        try:
            app._invalidate_preview_scene_trace()
        except Exception:
            pass
        insp.refresh_from_editor(
            sampling_mode=app._preview_3d_sampling_mode(),
            force_retrace=True,
        )
        _settle(insp, 0.6)
        print("  renderer actor count:", insp._renderer.GetActors().GetNumberOfItems())

        print("=== whole scene (reset camera) ===")
        try:
            insp._renderer.ResetCamera()
        except Exception:
            pass
        _settle(insp, 0.2)
        _snap(insp, OUT / "00_scene_reset.png")

        print("=== user's 17:02 oblique camera ===")
        _cam(insp, CAM_POS, CAM_FOC, CAM_UP, CAM_PSCALE)
        _settle(insp, 0.2)
        _snap(insp, OUT / "01_user_1702_view.png")

        print("=== frontal view down -Z onto the LED front window ===")
        _cam(insp, (2.16, 0.0, 400.0), (2.16, 0.0, 10.0), (0.0, 1.0, 0.0), 55.0)
        _settle(insp, 0.2)
        _snap(insp, OUT / "02_frontal_window.png")

        print("=== side view (down +X) to show the recessed windows in depth ===")
        _cam(insp, (500.0, 0.0, 40.0), (0.0, 0.0, 40.0), (0.0, 0.0, 1.0), 90.0)
        _settle(insp, 0.2)
        _snap(insp, OUT / "03_side_recess.png")
    except Exception:
        traceback.print_exc()
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
