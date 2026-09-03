"""0701 verification: (a) NO gold glyph actors remain at either face plane,
(b) each band draws an "FOV WxH" billboard above the green plane. Saves a
close-up render of the prism-assembly region."""
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

    gold = 0
    fov_labels = []
    props = insp._renderer.GetViewProps()
    props.InitTraversal()
    while True:
        p = props.GetNextProp()
        if p is None:
            break
        try:
            if not p.GetVisibility():
                continue
            if hasattr(p, "GetInput") and callable(getattr(p, "GetInput", None)):
                try:
                    text = str(p.GetInput())
                except Exception:
                    text = ""
                if text.startswith("FOV") or "field" in text:
                    pos = p.GetPosition()
                    fov_labels.append((text, tuple(round(float(x), 2) for x in pos)))
                    continue
            b = p.GetBounds()
            if b is None:
                continue
            col = p.GetProperty().GetColor() if hasattr(p, "GetProperty") else (0, 0, 0)
            r, g, bl = col
            if r > 0.9 and 0.7 < g < 0.9 and bl < 0.4:
                gold += 1
                print(f"GOLD ACTOR: x[{b[0]:.1f},{b[1]:.1f}] y[{b[2]:.1f},{b[3]:.1f}] "
                      f"z[{b[4]:.1f},{b[5]:.1f}] col=({r:.2f},{g:.2f},{bl:.2f})")
        except Exception:
            continue
    print(f"gold glyph actors: {gold}")
    for text, pos in fov_labels:
        print(f"LABEL: {text!r} at {pos}")

    cam = insp._renderer.GetActiveCamera()
    cam.SetFocalPoint(0.0, 2.0, -25.0)
    cam.SetPosition(90.0, -55.0, -115.0)
    cam.SetViewUp(0.0, -1.0, 0.0)
    insp._renderer.ResetCameraClippingRange()
    rw = insp._renderer.GetRenderWindow()
    rw.Render()
    from vtkmodules.vtkIOImage import vtkPNGWriter
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter
    w2i = vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.Update()
    wr = vtkPNGWriter(); wr.SetFileName("bugs/0701_fov_labels_after.png")
    wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print("wrote bugs/0701_fov_labels_after.png")
    editor.destroy()

if __name__ == "__main__":
    main()
