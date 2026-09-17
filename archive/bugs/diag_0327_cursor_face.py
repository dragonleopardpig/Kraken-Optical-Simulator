"""Which analytic face is the user actually hovering (central square window)?

Scan every analytic face on the transformed LED, project its boundary rim with
the recorded camera, and rank by min screen-distance to the recorded cursor --
to identify the opening the user points at and whether the auto-detector ranks it.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import vtk

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_face_index_edges import (
    face_outline_from_face_indices,
    triangle_array_and_face_index,
)

CURSOR = np.array([850.0, 615.0])
W, H = 1838, 904


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    app.imported_led_step_path = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0
    mesh = app._transformed_imported_step_mesh_for_label("led")
    auto = {int(c.face_index) for c in app.auto_detect_step_clear_aperture_candidates("led")}

    tris, fidx = triangle_array_and_face_index(mesh)
    fidx = np.asarray(fidx, int)

    ren = vtk.vtkRenderer()
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H)
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(288.87023861611124, 36.60318223831546, 110.7787913880848)
    cam.SetFocalPoint(0.0, 0.0, 50.0)
    cam.SetViewUp(-0.08241583321912822, 0.9769984238369366, -0.19667666423584354)
    cam.SetParallelScale(101.15273775216139); ren.ResetCameraClippingRange(); rw.Render()

    def project_many(P):
        out = np.empty((P.shape[0], 2))
        for i, p in enumerate(P):
            ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0); ren.WorldToDisplay()
            out[i] = np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]
        return out

    # Per-face: centroid, normal, area, and min-rim-distance to cursor.
    rows = []
    for fi in np.unique(fidx):
        sel = tris[fidx == fi]
        if sel.shape[0] == 0:
            continue
        v0, v1, v2 = sel[:, 0], sel[:, 1], sel[:, 2]
        cr = np.cross(v1 - v0, v2 - v0); a = 0.5 * np.linalg.norm(cr, axis=1); tot = float(a.sum())
        if tot <= 0:
            continue
        cen = (sel.mean(1) * a[:, None]).sum(0) / tot
        nrm = cr.sum(0); nrm = nrm / (np.linalg.norm(nrm) + 1e-12)
        # quick centroid-projection gate to avoid projecting every rim
        pc = project_many(cen.reshape(1, 3))[0]
        rows.append((int(fi), tot, cen, nrm, np.linalg.norm(pc - CURSOR)))

    # For faces whose centroid projects within 220px, compute true rim distance.
    near = sorted([r for r in rows if r[4] < 220], key=lambda r: r[4])[:25]
    results = []
    for fi, area, cen, nrm, cdist in near:
        ol = face_outline_from_face_indices(mesh, (fi,))
        if ol is None or int(getattr(ol, "n_points", 0)) == 0:
            rimd = None
        else:
            P = np.asarray(ol.points, dtype=float).reshape(-1, 3)
            pj = project_many(P)
            rimd = float(np.linalg.norm(pj - CURSOR, axis=1).min())
        results.append((fi, area, cen, nrm, rimd))

    results.sort(key=lambda r: (999999 if r[4] is None else r[4]))
    print(f"cursor VTK {CURSOR.tolist()};  auto-detected CA faces: {sorted(auto)}")
    print("nearest face RIMS to cursor (fi | area | centroid | normal | rim px | detected?):")
    for fi, area, cen, nrm, rimd in results[:15]:
        det = "CA-CAND" if fi in auto else ""
        rs = "n/a" if rimd is None else f"{rimd:6.0f}"
        print(f"  F{fi:04d} area={area:8.1f} c=({cen[0]:6.1f},{cen[1]:6.1f},{cen[2]:6.1f}) "
              f"n=({nrm[0]:5.2f},{nrm[1]:5.2f},{nrm[2]:5.2f}) rim={rs}px  {det}")
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
