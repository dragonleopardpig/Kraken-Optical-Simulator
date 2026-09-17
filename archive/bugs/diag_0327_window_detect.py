"""Is the central-square emitting WINDOW an analytic face, and is it detected as a
clear-aperture candidate?

Find the smallest camera-facing analytic face whose projected rim-loop CONTAINS the
recorded cursor (the innermost opening the user points at), then print its geometry
and whether the auto-detector ranks it.  Also dump every auto-detected candidate's
identity so we can see what the detector actually chose.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_face_index_edges import (
    face_outline_from_face_indices, triangle_array_and_face_index)

CURSOR = np.array([850.0, 615.0]); W, H = 1838, 904
CAM_POS = np.array([288.87023861611124, 36.60318223831546, 110.7787913880848])


def _cam(ren):
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(*CAM_POS)
    cam.SetFocalPoint(0.0, 0.0, 50.0)
    cam.SetViewUp(-0.08241583321912822, 0.9769984238369366, -0.19667666423584354)
    cam.SetParallelScale(101.15273775216139)


def _poly_contains(poly, pt):
    # even-odd point-in-polygon on projected 2D loop points (poly: Nx2)
    x, y = pt; inside = False; n = len(poly); j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    app.imported_led_step_path = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0
    mesh = app._transformed_imported_step_mesh_for_label("led")
    tris, fidx = triangle_array_and_face_index(mesh); fidx = np.asarray(fidx, int)
    cands = app.auto_detect_step_clear_aperture_candidates("led")
    auto = {int(c.face_index): c for c in cands}

    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H)
    _cam(ren); ren.ResetCameraClippingRange(); rw.Render()

    def proj(P):
        out = np.empty((len(P), 2))
        for i, p in enumerate(P):
            ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0); ren.WorldToDisplay()
            out[i] = np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]
        return out

    view = np.array([0.0, 0.0, 50.0]) - CAM_POS; view = view / np.linalg.norm(view)

    # every camera-facing face whose projected rim-loop contains the cursor
    containing = []
    for fi in np.unique(fidx):
        sel = tris[fidx == fi]
        if sel.shape[0] == 0:
            continue
        v0, v1, v2 = sel[:, 0], sel[:, 1], sel[:, 2]
        cr = np.cross(v1 - v0, v2 - v0); a = 0.5 * np.linalg.norm(cr, axis=1); area = float(a.sum())
        nrm = cr.sum(0); nrm = nrm / (np.linalg.norm(nrm) + 1e-12)
        facing = float(-np.dot(nrm, view))
        if facing < 0.5 or area < 50:
            continue
        ol = face_outline_from_face_indices(mesh, (int(fi),))
        if ol is None or int(getattr(ol, "n_points", 0)) == 0:
            continue
        P = np.asarray(ol.points, dtype=float).reshape(-1, 3)
        pj = proj(P)
        if not _poly_contains(pj, CURSOR):
            continue
        cen = (sel.mean(1) * a[:, None]).sum(0) / area
        rimd = float(np.linalg.norm(pj - CURSOR, axis=1).min())
        containing.append((area, int(fi), cen, nrm, facing, rimd,
                           (pj[:, 0].min(), pj[:, 0].max(), pj[:, 1].min(), pj[:, 1].max())))

    containing.sort(key=lambda r: r[0])  # smallest area = innermost opening
    print(f"auto-detected CA candidates: {sorted(auto)}")
    print("camera-facing faces whose RIM-LOOP contains the cursor (innermost first):")
    for area, fi, cen, nrm, facing, rimd, bb in containing:
        det = "  <== DETECTED" if fi in auto else ""
        print(f"  F{fi:04d} area={area:8.1f} c=({cen[0]:6.1f},{cen[1]:6.1f},{cen[2]:6.1f}) "
              f"n=({nrm[0]:5.2f},{nrm[1]:5.2f},{nrm[2]:5.2f}) rim={rimd:5.0f}px "
              f"bb=x[{bb[0]:.0f},{bb[1]:.0f}]y[{bb[2]:.0f},{bb[3]:.0f}]{det}")

    print("\nfull identity of each auto-detected candidate:")
    for fi in sorted(auto):
        c = auto[fi]
        print(f"  F{fi:04d} centroid={[round(v,1) for v in c.centroid]} "
              f"normal={[round(v,2) for v in c.normal]} "
              f"area={getattr(c,'area',float('nan')):.1f}")
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
