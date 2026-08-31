"""0672 verdict: focus + split field at the FOLDED image plane, then a 3D render."""
from pathlib import Path

import numpy as np

OUT = Path("attachment")


def main():
    import vtk

    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["omf"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("omf")
    try:
        editor._preview_trace_deferred_until_requested = False
    except Exception:
        pass
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    groups: dict[int, list] = {}
    n_reach = 0
    for rp in (getattr(bundle, "ray_paths", None) or []):
        if not bool(getattr(rp, "reaches_image", False)):
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p[-2:])) or not np.all(np.isfinite(p[0])):
            continue
        n_reach += 1
        a, b = p[-2], p[-1]
        d = b - a
        if abs(d[2]) < 1e-9:
            continue
        # the folded image plane is normal to -z; project onto the mean terminal z
        groups.setdefault(int(getattr(rp, "field_index", 0)), []).append((float(p[0][1]), a, d, float(b[2])))
    z_img = float(np.median([rec[3] for pts in groups.values() for rec in pts]))
    print(f"reached {n_reach}; folded image plane z ~ {z_img:.2f}")
    rms_all = []
    for fi, recs in sorted(groups.items()):
        pts = []
        for y0, a, d, _bz in recs:
            t = (z_img - a[2]) / d[2]
            pts.append(a[:2] + t * d[:2])
        arr = np.asarray(pts)
        if len(arr) < 4:
            continue
        cy = arr.mean(axis=0)
        rms = float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean()))
        rms_all.append(rms)
        y0m = float(np.mean([r[0] for r in recs]))
        print(f"  field {fi}: object y {y0m:+7.2f} -> image (x {cy[0]:+7.2f}, y {cy[1]:+7.2f}), rms {rms*1000:6.1f} um")
    print(f"worst per-field rms {max(rms_all)*1000:.1f} um" if rms_all else "no fields")

    insp = _open_3d_inspector(editor)
    insp.refresh_from_editor(sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True)
    _settle(insp)
    ren = insp._renderer
    cam = ren.GetActiveCamera()
    b = ren.ComputeVisiblePropBounds()
    cx, cy_, cz = (b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2
    cam.SetFocalPoint(cx, cy_, cz)
    cam.SetPosition(cx + 900, cy_, cz)
    cam.SetViewUp(0, 0, -1)
    ren.ResetCamera()
    insp.render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(insp._vtk_widget.GetRenderWindow())
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(str(OUT / "om05a_folded_scene_view.png"))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    print("render:", OUT / "om05a_folded_scene_view.png")
    editor.destroy()


if __name__ == "__main__":
    main()
