"""bugs/0330e -- flag_20260717_073340_408 "CA not highlighting, but the next
window get highlighted." The FIFTH consecutive CA flag -- and the first that
highlights SOMETHING: hover_step_cell_key=('step','led','F011') with a live
outline, but on the WRONG window.

Scene: the 90mm CO90 LED (bounds ~[+-55.6, +-47.2, 0.7..77.1]), viewed from the
BACK, scale 83.6. The user points at [420,635] wanting the central CA window;
the app instead highlights F011 (world bbox x[-6.9,48.6] y[-30.0,25.5], flat at
z=2.71). The 0330 opening stash ran at [123,589] (chosen=null) -- 300 px from the
flag cursor, the same stash-far-from-flag signature as flags 978/798/718/630.

This offscreen probe (no Xvfb) reproduces the flag camera at 1163x904 and reports
every mined opening loop's projected centroid/bbox + distance to the TRUE cursor
[420,635], flags whether the cursor is INSIDE each, runs nearest_opening_loop() at
the true + stash cursors, and locates F011 (the wrongly-highlighted window) so we
can see whether the cursor is actually nearer F011's rim than the CA's.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_opening_loops import (
    opening_loops_for_mesh, nearest_opening_loop, _project_polygon, _point_in_polygon)

LED = Path("attachment/LED/OPT-CO90-X-V1.6.2-H.STEP").resolve()
W, H = 1163, 904

CAM_POS = (106.42429438294444, -30.460346006750775, -244.75322758070575)
CAM_FOCAL = (-5.133493386800098, -5.791433953646112, 51.13146936002458)
CAM_UP = (-0.016887738634632794, 0.9958530832362732, -0.08939485943059908)
CAM_SCALE = 83.59730392740606

TRUE_CURSOR = (420.0, 635.0)
STASH_CURSOR = (123.0, 589.0)
F011_WORLD = (0.5 * (-6.893765926172291 + 48.606235503827705),
              0.5 * (-29.99694061315209 + 25.50305938684791),
              2.7104127407073975)


def _cam(ren):
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(*CAM_POS); cam.SetFocalPoint(*CAM_FOCAL)
    cam.SetViewUp(*CAM_UP); cam.SetParallelScale(CAM_SCALE)


def _load(app):
    app.imported_led_step_path = LED
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0
    return app._transformed_imported_step_mesh_for_label("led")


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    mesh = _load(app)
    b = np.asarray(mesh.bounds, float)
    print(f"CO90 bounds = {np.round(b,1).tolist()}")

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

    print(f"loops mined = {len(loops)}  (render {tuple(rw.GetSize())})")
    f011 = project(F011_WORLD)
    print(f"F011 world-center {tuple(round(v,1) for v in F011_WORLD)} -> proj {None if f011 is None else (round(f011[0]),round(f011[1]))}"
          f"  dist_to_TRUE={None if f011 is None else round(float(np.hypot(f011[0]-TRUE_CURSOR[0], f011[1]-TRUE_CURSOR[1])),1)}")

    print("\nall opening loops (perim>=60) projected at the flag camera, sorted by dist to TRUE cursor:")
    rows = []
    for lp in sorted({int(l.face_index): l for l in loops if l.perimeter >= 60.0}.values(), key=lambda l: -l.perimeter):
        poly = _project_polygon(lp.points, project)
        if poly is None:
            continue
        c = poly.mean(axis=0)
        dt = float(np.hypot(c[0]-TRUE_CURSOR[0], c[1]-TRUE_CURSOR[1]))
        inside = _point_in_polygon(np.asarray(TRUE_CURSOR, float), poly)
        rows.append((dt, lp, c, poly, inside))
    for dt, lp, c, poly, inside in sorted(rows, key=lambda r: r[0]):
        print(f"  F{lp.face_index:03d} perim={lp.perimeter:6.1f}  centroid=({c[0]:.0f},{c[1]:.0f}) "
              f"bbox x[{poly[:,0].min():.0f},{poly[:,0].max():.0f}] y[{poly[:,1].min():.0f},{poly[:,1].max():.0f}] "
              f"| dist_TRUE={dt:.0f} inside_TRUE={inside}")

    for name, cur in (("TRUE  [420,635]", TRUE_CURSOR), ("STASH [123,589]", STASH_CURSOR)):
        picked = nearest_opening_loop(loops, cur, project, tolerance_px=30.0)
        tag = (f"F{picked.face_index:03d}(perim={picked.perimeter:.0f})" if picked else "None")
        print(f"\nnearest_opening_loop {name} -> {tag}")

    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
