"""bugs/0329 interior-hit proof (display-free, offscreen VTK projector).

The user's "just complement it": pointing at the MIDDLE of the emitting square must
highlight the opening, not the surrounding panel. Prove that after the fix
nearest_opening_loop snaps to the square when the cursor is INSIDE it (center of the
projected polygon), where the old rim-only (30 px) snap returned None.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_opening_loops import (
    opening_loops_for_mesh, nearest_opening_loop, _project_polygon)

W, H = 1838, 904
REC_CURSOR = (886.0, 607.0)


def _cam(ren):
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(285.12211524555573, 44.86112856896071, 121.92167776210495)
    cam.SetFocalPoint(0.0, 0.0, 50.0)
    cam.SetViewUp(-0.13607788549386488, 0.9877295233717259, -0.0766367910300376)
    cam.SetParallelScale(101.15273775216139)


def _is_square(lp):
    return lp is not None and 150 <= lp.perimeter <= 210 and lp.centroid[0] > 40


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    app.imported_led_step_path = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0
    mesh = app._transformed_imported_step_mesh_for_label("led")
    loops = opening_loops_for_mesh(mesh)

    ren = vtk.vtkRenderer()
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H)
    _cam(ren); ren.ResetCameraClippingRange(); rw.Render()

    def project(p):
        p = np.asarray(p, dtype=float).reshape(-1)
        if p.size < 3 or not np.all(np.isfinite(p[:3])):
            return None
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0); ren.WorldToDisplay()
        return np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]

    sq = next(lp for lp in loops if _is_square(lp))
    poly = _project_polygon(sq.points, project)
    center = poly.mean(axis=0)
    print(f"loops={len(loops)} square proj-centroid=({center[0]:.0f},{center[1]:.0f}) "
          f"proj-bbox x[{poly[:,0].min():.0f},{poly[:,0].max():.0f}] y[{poly[:,1].min():.0f},{poly[:,1].max():.0f}]")

    cases = {
        "square-center (interior gesture)": (float(center[0]), float(center[1])),
        "recorded cursor [886,607] (near rim)": REC_CURSOR,
        "off-body far corner": (60.0, 60.0),
    }
    ok = True
    for name, xy in cases.items():
        picked = nearest_opening_loop(loops, xy, project, tolerance_px=30.0)
        tag = "SQUARE" if _is_square(picked) else (f"other(perim={picked.perimeter:.0f})" if picked else "None")
        expect_square = "off-body" not in name
        good = _is_square(picked) == expect_square
        ok = ok and good
        print(f"  {'OK ' if good else 'BAD'} {name:42s} -> {tag}")
    print("RESULT:", "PASS" if ok else "FAIL")
    try:
        app.destroy()
    except Exception:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
