"""bugs/0330b -- flag_20260716_170326_798 "CA not highlight" fork resolver.

The fresh flag (recorded WITH the 0330 instrumentation) killed the size/DPI theory:
render_window == renderer_viewport == widget_logical == [1163, 904] (all agree).
Yet the opening pick MISSED (chosen_face_index == null -> fell back to whole panel
F005). The decisive anomaly: the stashed opening pick ran at cursor_xy=[1019,402]
(empty space right of the panel) while the user's TRUE cursor (flag vtk_xy) was
[432,652] -- the screenshot's green crosshair sits ON the square's top-left corner.

Two candidate roots remain, and this display-free offscreen probe decides between them:
  (a) PROJECTION bug -- _world_to_display_2d maps the square far from where it's drawn,
      so even the true cursor [432,652] would miss the square.
  (b) CURSOR-PLUMBING / STALE-CURSOR bug -- the projection is fine (square projects
      onto/near [432,652]) but the opening pick evaluated the wrong cursor [1019,402].

It reproduces the flag's EXACT camera at 1163x904 offscreen (no Xvfb), prints where
the square (face 53) projects, tests point-in-polygon + nearest_opening_loop at BOTH
cursors, and reprints the live stash's own centroid for face 53 for cross-check.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_opening_loops import (
    opening_loops_for_mesh, nearest_opening_loop, _project_polygon, _point_in_polygon)

LED = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
W, H = 1163, 904

# flag_20260716_170326_798 camera
CAM_POS = (290.33855105047655, -14.442679984171399, 113.04604634298116)
CAM_FOCAL = (0.0, 0.0, 50.0)
CAM_UP = (0.059512498937505, 0.997184139818969, -0.045629527322958045)
CAM_SCALE = 101.15273775216139

TRUE_CURSOR = (432.0, 652.0)     # flag vtk_xy -- crosshair ON the square corner
DEBUG_CURSOR = (1019.0, 402.0)   # what the opening pick actually evaluated (the miss)


def _cam(ren):
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(*CAM_POS)
    cam.SetFocalPoint(*CAM_FOCAL)
    cam.SetViewUp(*CAM_UP)
    cam.SetParallelScale(CAM_SCALE)


def _is_square(lp):
    return lp is not None and 150 <= lp.perimeter <= 210 and lp.centroid[0] > 40


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    app.imported_led_step_path = LED
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

    print(f"render-window size = {tuple(rw.GetSize())} (want {W}x{H})")
    print(f"loops mined = {len(loops)}")

    sq = next((lp for lp in loops if _is_square(lp)), None)
    if sq is None:
        print("BAD: no square loop mined")
        try: app.destroy()
        except Exception: pass
        return 1

    poly = _project_polygon(sq.points, project)
    center = poly.mean(axis=0)
    print(f"\nsquare face_index=F{sq.face_index:03d} perim={sq.perimeter:.1f}")
    print(f"  proj-centroid=({center[0]:.1f},{center[1]:.1f})  "
          f"proj-bbox x[{poly[:,0].min():.0f},{poly[:,0].max():.0f}] y[{poly[:,1].min():.0f},{poly[:,1].max():.0f}]")
    print(f"  live-stash reported this square centroid at [674.9, 545.4] (cross-check the projection)")

    for name, cur in (("TRUE  [432,652]", TRUE_CURSOR), ("DEBUG [1019,402]", DEBUG_CURSOR)):
        c = np.asarray(cur, float)
        inside = _point_in_polygon(c, poly)
        d_center = float(np.hypot(center[0]-c[0], center[1]-c[1]))
        picked = nearest_opening_loop(loops, cur, project, tolerance_px=30.0)
        tag = "SQUARE" if _is_square(picked) else (f"other(F{picked.face_index:03d},perim={picked.perimeter:.0f})" if picked else "None")
        print(f"\ncursor {name}:")
        print(f"  inside_projected_square={inside}  dist_to_square_centroid={d_center:.1f}px")
        print(f"  nearest_opening_loop -> {tag}")

    print("\n=> (b) CURSOR-PLUMBING if TRUE hits SQUARE but DEBUG misses; "
          "(a) PROJECTION if TRUE also misses the square")
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
