"""bugs/0330d -- flag_20260717_072735_718 "CA not highlighting" (a DIFFERENT LED).

This is the THIRD "CA not highlighting" flag. Scene: an 85mm-class LED panel
(bounds ~[+-42.5, +-71.5, 137]) viewed from BACK, scale 69. The green crosshair
sits on the TOP RIM of the big central CA square; NOTHING is highlighted
(hover_outline_bounds=[], hover_step_cell_key=null). The 0330 stash ran at
cursor_xy=[852,356] (chosen=null) while the flag cursor is [569,712] -- 455 px
apart, the SAME stash-far-from-flag signature as flag 798.

Three flags with that signature is not random timing. This offscreen probe (no
Xvfb) reproduces the flag camera at 1163x904 and reports, for the true cursor
[569,712] and the stash cursor [852,356]:
  * the big opening loops' projected centroid/bbox (to ID the CA square),
  * nearest_opening_loop() at each cursor (does the CA resolve at the true cursor?).
It also auto-detects which LED STEP matches the flagged bounds.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_opening_loops import (
    opening_loops_for_mesh, nearest_opening_loop, _project_polygon, _point_in_polygon)

LED_DIR = Path("attachment/LED").resolve()
CANDIDATES = ["OPT-COR85-X-V1.1.3-H.STEP", "OPT-CO90-X-V1.6.2-H.STEP",
              "OPT-ILS0202-X-V1.0.2-H.STEP"]
FLAG_BOUNDS = np.array([-42.5, 42.5, -71.5, 71.5, 0.0, 137.0])
W, H = 1163, 904

CAM_POS = (12.112190886000334, 27.932350665822057, -213.75687578135802)
CAM_FOCAL = (-10.556172237981663, 23.813031776378526, 48.597444633639654)
CAM_UP = (0.024144299123141314, 0.9995503530828229, 0.017780451958719568)
CAM_SCALE = 69.08868093174054

TRUE_CURSOR = (569.0, 712.0)
STASH_CURSOR = (852.0, 356.0)


def _cam(ren):
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(*CAM_POS); cam.SetFocalPoint(*CAM_FOCAL)
    cam.SetViewUp(*CAM_UP); cam.SetParallelScale(CAM_SCALE)


def _load(app, name):
    app.imported_led_step_path = LED_DIR / name
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0
    return app._transformed_imported_step_mesh_for_label("led")


def main() -> int:
    app = KrakenLayoutEditor(headless=True)

    mesh = None
    chosen_name = None
    for name in CANDIDATES:
        if not (LED_DIR / name).exists():
            continue
        m = _load(app, name)
        if m is None:
            continue
        b = np.asarray(m.bounds, float)
        close = np.allclose(b, FLAG_BOUNDS, atol=1.5)
        print(f"{name}: bounds={np.round(b,1).tolist()}  matches_flag={close}")
        if close and mesh is None:
            mesh, chosen_name = m, name
    if mesh is None:
        print("BAD: no LED matched the flagged bounds; using first candidate for loop census")
        mesh = _load(app, CANDIDATES[0]); chosen_name = CANDIDATES[0]
    print(f"\n=> using {chosen_name}")

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
    print("\nbig loops (perim>=120) projected at the flag camera:")
    big = sorted({int(lp.face_index): lp for lp in loops if lp.perimeter >= 120.0}.values(),
                 key=lambda l: -l.perimeter)
    for lp in big:
        poly = _project_polygon(lp.points, project)
        if poly is None:
            continue
        c = poly.mean(axis=0)
        dt = float(np.hypot(c[0]-TRUE_CURSOR[0], c[1]-TRUE_CURSOR[1]))
        inside = _point_in_polygon(np.asarray(TRUE_CURSOR, float), poly)
        print(f"  F{lp.face_index:03d} perim={lp.perimeter:6.1f}  proj-centroid=({c[0]:.0f},{c[1]:.0f}) "
              f"bbox x[{poly[:,0].min():.0f},{poly[:,0].max():.0f}] y[{poly[:,1].min():.0f},{poly[:,1].max():.0f}] "
              f"| dist_to_TRUE={dt:.0f} inside_TRUE={inside}")

    for name, cur in (("TRUE  [569,712]", TRUE_CURSOR), ("STASH [852,356]", STASH_CURSOR)):
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
