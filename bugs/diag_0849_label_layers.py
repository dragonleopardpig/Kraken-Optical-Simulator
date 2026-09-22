"""bugs/0849 diagnostic: the REAL inspector on om05a_folded, the user's 20 mm path, flag_20260921_172317's
camera -> a PNG of the focus / sensor / strip labels, and which layer every label, the HUD and the
banner landed on. Needs a display:

    Xvfb :93 -screen 0 1600x1100x24 &  DISPLAY=:93 devenv shell -- python bugs/diag_0849_label_layers.py out.png
"""
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace


def main(out: str) -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.inspection_part import normalize_inspection_part_spec
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    app = KrakenLayoutEditor()
    app.layout_files["s"] = Path("attachment/om05a_folded.py")
    app.load_layout_by_name("s")
    try:
        app.geometry("1590x1090+0+0")
    except Exception:
        pass
    app.open_3d_view()
    for _ in range(5):
        app.update_idletasks(); app.update(); time.sleep(0.1)
    insp = app._three_d_inspector
    insp.geometry("1466x980+0+0"); insp.deiconify(); insp.update()
    try:
        insp.show_detector_overlays_var.set(True)
    except Exception as exc:
        print("det overlay toggle:", exc)
    spec = dict(normalize_inspection_part_spec(getattr(app, "inspection_part_spec", None)))
    spec.update(width_mm=20.0, depth_mm=20.0, height_mm=1.0, enabled=True)
    app.set_inspection_part_spec(spec)
    t0 = time.time()
    ok, msg = QuickEstimationService(SimpleNamespace(editor=app)).fov_solve("object", "thickness", 21.0, 1.05)
    print(f"solve ok={ok} ({time.time()-t0:.0f} s): {str(msg)[:160]}", flush=True)
    app._preview_trace_deferred_until_requested = False
    app._refresh_open_3d_views()
    for _ in range(10):
        app.update_idletasks(); app.update(); time.sleep(0.2)
    print("focus info:", {k: (app.__dict__.get('_focused_image_plane_info') or {}).get(k) for k in ('offset_mm', 'side')}, flush=True)
    state = json.loads(Path("attachment/recorded_bug_repros/flag_20260921_172317_713/state.json").read_text())["scene_state"]
    cam = insp._renderer.GetActiveCamera()
    cam.SetPosition(*state["camera_position"]); cam.SetFocalPoint(*state["camera_focal"]); cam.SetViewUp(*state["camera_view_up"])
    if state.get("camera_parallel_scale"):
        cam.SetParallelScale(float(state["camera_parallel_scale"]))
    insp._renderer.ResetCameraClippingRange()
    insp.render(); insp.update()
    import vtk
    labels_main = labels_top = 0
    for renderer, tag in ((insp._renderer, "main"), (insp._gizmo_overlay_renderer, "top")):
        if renderer is None:
            continue
        props = renderer.GetViewProps(); props.InitTraversal()
        for _ in range(props.GetNumberOfItems()):
            p = props.GetNextProp()
            if isinstance(p, vtk.vtkBillboardTextActor3D):
                if tag == "main":
                    labels_main += 1
                else:
                    labels_top += 1
                    print(f"   on top: {p.GetInput()[:90]!r}  pickable={p.GetPickable()}")
    print(f"billboard labels: main renderer {labels_main}, always-on-top layer {labels_top}")
    for name in ("_system_info_hud_actor", "_solve_refusal_banner_actor"):
        a = insp.__dict__.get(name)
        where = [tag for r, tag in ((insp._renderer, "main"), (insp._gizmo_overlay_renderer, "top")) if r is not None and a is not None and r.HasViewProp(a)]
        print(f"   {name}: on {where}")
    print("render window size:", insp._vtk_widget.GetRenderWindow().GetSize())
    rw = insp._vtk_widget.GetRenderWindow(); rw.Render()
    cap = vtk.vtkWindowToImageFilter(); cap.SetInput(rw); cap.ReadFrontBufferOff(); cap.Update()
    w = vtk.vtkPNGWriter(); w.SetFileName(out); w.SetInputConnection(cap.GetOutputPort()); w.Write()
    print("saved", out)
    app.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
