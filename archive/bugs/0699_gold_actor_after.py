"""After the 0699 fix: print ALL gold actors near face B (z ~ -50) and save a
close-up render of the face-B region so the glyph footprint is visually verifiable."""
from pathlib import Path
import numpy as np

def main():
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    editor._build_preview_system_rays_bundle(trace_rays=True)
    editor.open_3d_view()
    editor.update_idletasks(); editor.update()
    insp = editor._three_d_inspector
    insp.refresh_from_editor(sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True)
    _settle(editor, 1.0)

    props = insp._renderer.GetViewProps()
    props.InitTraversal()
    while True:
        p = props.GetNextProp()
        if p is None:
            break
        try:
            if not p.GetVisibility():
                continue
            b = p.GetBounds()
            if b is None:
                continue
            col = p.GetProperty().GetColor() if hasattr(p, "GetProperty") else (0, 0, 0)
            r, g, bl = col
            if not (r > 0.7 and g > 0.4 and bl < 0.5):
                continue
            # gold actors whose z-range touches the face-B neighbourhood
            if b[4] > -46.0 or b[5] < -54.0:
                pass
            if not (b[4] <= -46.0 <= b[5] or (-54.0 <= b[4] <= -46.0)):
                continue
            print(f"GOLD@B: x[{b[0]:.2f},{b[1]:.2f}] y[{b[2]:.2f},{b[3]:.2f}] "
                  f"z[{b[4]:.2f},{b[5]:.2f}] col=({r:.2f},{g:.2f},{bl:.2f})")
        except Exception:
            continue

    cam = insp._renderer.GetActiveCamera()
    cam.SetFocalPoint(0.0, 0.0, -50.0)
    cam.SetPosition(60.0, 45.0, -110.0)
    cam.SetViewUp(0.0, 1.0, 0.0)
    insp._renderer.ResetCameraClippingRange()
    rw = insp._renderer.GetRenderWindow()
    rw.Render()
    from vtkmodules.vtkIOImage import vtkPNGWriter
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter
    w2i = vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.Update()
    wr = vtkPNGWriter(); wr.SetFileName("bugs/0699_faceb_glyph_after.png")
    wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print("wrote bugs/0699_faceb_glyph_after.png")
    editor.destroy()

if __name__ == "__main__":
    main()
