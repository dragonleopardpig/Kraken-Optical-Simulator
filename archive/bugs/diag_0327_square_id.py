"""Identify the large camera-facing face under the cursor (the 'central square')
and render body + face266(gold) + that face(red) + cursor for a labeled compare.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_face_index_edges import (
    face_outline_from_face_indices, triangle_array_and_face_index)

CURSOR = np.array([850.0, 615.0]); W, H = 1838, 904


def _cam(ren):
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(288.87023861611124, 36.60318223831546, 110.7787913880848)
    cam.SetFocalPoint(0.0, 0.0, 50.0)
    cam.SetViewUp(-0.08241583321912822, 0.9769984238369366, -0.19667666423584354)
    cam.SetParallelScale(101.15273775216139)


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    app.imported_led_step_path = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0
    mesh = app._transformed_imported_step_mesh_for_label("led")
    tris, fidx = triangle_array_and_face_index(mesh); fidx = np.asarray(fidx, int)

    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H)
    _cam(ren); ren.ResetCameraClippingRange(); rw.Render()

    def proj(P):
        out = np.empty((P.shape[0], 2))
        for i, p in enumerate(P):
            ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0); ren.WorldToDisplay()
            out[i] = np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]
        return out

    # camera view direction (world) to rank camera-facing faces
    view = np.array([0.0, 0.0, 50.0]) - np.array([288.87, 36.60, 110.78])
    view = view / np.linalg.norm(view)

    # Large faces whose projected triangle set CONTAINS the cursor, frontmost & camera-facing.
    hits = []
    for fi in np.unique(fidx):
        sel = tris[fidx == fi]
        if sel.shape[0] == 0:
            continue
        v0, v1, v2 = sel[:, 0], sel[:, 1], sel[:, 2]
        cr = np.cross(v1 - v0, v2 - v0); a = 0.5 * np.linalg.norm(cr, axis=1); area = float(a.sum())
        if area < 400:
            continue
        nrm = cr.sum(0); nrm = nrm / (np.linalg.norm(nrm) + 1e-12)
        facing = float(-np.dot(nrm, view))  # >0 means faces camera
        # does the cursor fall inside any projected triangle of this face?
        contains = False
        depth = None
        for t in sel:
            p2 = proj(t)
            # barycentric point-in-triangle in 2D
            ax, ay = p2[0]; bx, by = p2[1]; cx, cy = p2[2]
            d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-9:
                continue
            l1 = ((by - cy) * (CURSOR[0] - cx) + (cx - bx) * (CURSOR[1] - cy)) / d
            l2 = ((cy - ay) * (CURSOR[0] - cx) + (ax - cx) * (CURSOR[1] - cy)) / d
            l3 = 1 - l1 - l2
            if l1 >= -0.01 and l2 >= -0.01 and l3 >= -0.01:
                contains = True
                wp = l1 * t[0] + l2 * t[1] + l3 * t[2]
                depth = float(-np.dot(wp - np.array([288.87, 36.60, 110.78]), -view))
                break
        if contains:
            cen = (sel.mean(1) * a[:, None]).sum(0) / area
            hits.append((depth, int(fi), area, cen, nrm, facing))

    hits.sort(key=lambda r: r[0])  # frontmost first
    print("faces the cursor sits ON (frontmost first): fi | area | centroid | normal | camdot")
    for depth, fi, area, cen, nrm, facing in hits[:10]:
        print(f"  F{fi:04d} area={area:8.1f} c=({cen[0]:6.1f},{cen[1]:6.1f},{cen[2]:6.1f}) "
              f"n=({nrm[0]:5.2f},{nrm[1]:5.2f},{nrm[2]:5.2f}) camdot={facing:5.2f} depth={depth:7.1f}")

    square_fi = hits[0][1] if hits else None

    # render body + face266 gold + square red + cursor
    bm = vtk.vtkPolyDataMapper(); bm.SetInputData(mesh)
    ba = vtk.vtkActor(); ba.SetMapper(bm); ba.GetProperty().SetColor(0.6, 0.65, 0.7); ba.GetProperty().SetOpacity(0.4)
    ren.AddActor(ba)
    for fi, col in ((266, (1.0, 0.8, 0.0)), (square_fi, (1.0, 0.0, 0.0))):
        if fi is None:
            continue
        ol = face_outline_from_face_indices(mesh, (int(fi),))
        m = vtk.vtkPolyDataMapper(); m.SetInputData(ol)
        act = vtk.vtkActor(); act.SetMapper(m); act.GetProperty().SetColor(*col); act.GetProperty().SetLineWidth(6)
        ren.AddActor(act)
    rw.Render()
    # cursor cross
    pts = vtk.vtkPoints()
    for dx, dy in ((-22, 0), (22, 0), (0, -22), (0, 22)):
        pts.InsertNextPoint(CURSOR[0] + dx, CURSOR[1] + dy, 0)
    lc = vtk.vtkCellArray()
    for a2, b2 in ((0, 1), (2, 3)):
        ln = vtk.vtkLine(); ln.GetPointIds().SetId(0, a2); ln.GetPointIds().SetId(1, b2); lc.InsertNextCell(ln)
    cpd = vtk.vtkPolyData(); cpd.SetPoints(pts); cpd.SetLines(lc)
    cm = vtk.vtkPolyDataMapper2D(); cm.SetInputData(cpd)
    ca = vtk.vtkActor2D(); ca.SetMapper(cm); ca.GetProperty().SetColor(0, 0.6, 0); ca.GetProperty().SetLineWidth(3)
    ren.AddActor2D(ca); rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.Update()
    wr = vtk.vtkPNGWriter(); out = Path("attachment/_diag_0327_square_id.png").resolve()
    wr.SetFileName(str(out)); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print("square face_index =", square_fi, "-> wrote", out)
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
