"""Is the central-square recess rim extractable as feature edges near the cursor?

The Alt-mode pick uses display_feature_edges(); if the square's rim shows up there as
a tight cluster of edges around the cursor, then a plain-hover "snap to nearest closed
edge loop" fix is feasible.  Project all feature edges, report those within 60px of the
recorded cursor, and render them (blue) over body + cursor for eyeballing.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_face_index_edges import (
    display_feature_edges, line_segment_pairs)

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

    edges = display_feature_edges(mesh, feature_angle=24.0, boundary_edges=True)
    P = np.asarray(edges.points, dtype=float).reshape(-1, 3)
    pairs = line_segment_pairs(edges)
    print(f"feature edges: {len(P)} points, {len(pairs)} segments")

    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H)
    _cam(ren); ren.ResetCameraClippingRange(); rw.Render()

    def proj(p):
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0); ren.WorldToDisplay()
        return np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]

    P2 = np.array([proj(p) for p in P])
    d = np.linalg.norm(P2 - CURSOR, axis=1)
    near_pts = np.where(d < 60)[0]
    print(f"feature-edge vertices within 60px of cursor: {len(near_pts)} (min {d.min():.0f}px)")

    # segments with at least one endpoint within 90px -> candidate square rim
    near_segs = [(a, b) for a, b in pairs if d[a] < 90 or d[b] < 90]
    print(f"segments touching the cursor neighbourhood (<90px): {len(near_segs)}")
    if near_segs:
        xs = np.concatenate([P2[[a, b], 0] for a, b in near_segs])
        ys = np.concatenate([P2[[a, b], 1] for a, b in near_segs])
        print(f"  their screen bbox: x[{xs.min():.0f},{xs.max():.0f}] y[{ys.min():.0f},{ys.max():.0f}]")

    # render: body translucent, near feature edges blue, all feature edges faint, cursor green
    bm = vtk.vtkPolyDataMapper(); bm.SetInputData(mesh)
    ba = vtk.vtkActor(); ba.SetMapper(bm); ba.GetProperty().SetColor(0.6, 0.65, 0.7); ba.GetProperty().SetOpacity(0.35)
    ren.AddActor(ba)
    em = vtk.vtkPolyDataMapper(); em.SetInputData(edges)
    ea = vtk.vtkActor(); ea.SetMapper(em); ea.GetProperty().SetColor(0.0, 0.0, 1.0); ea.GetProperty().SetLineWidth(2)
    ren.AddActor(ea)
    rw.Render()
    pts = vtk.vtkPoints()
    for dx, dy in ((-22, 0), (22, 0), (0, -22), (0, 22)):
        pts.InsertNextPoint(CURSOR[0] + dx, CURSOR[1] + dy, 0)
    lc = vtk.vtkCellArray()
    for a2, b2 in ((0, 1), (2, 3)):
        ln = vtk.vtkLine(); ln.GetPointIds().SetId(0, a2); ln.GetPointIds().SetId(1, b2); lc.InsertNextCell(ln)
    cpd = vtk.vtkPolyData(); cpd.SetPoints(pts); cpd.SetLines(lc)
    cm = vtk.vtkPolyDataMapper2D(); cm.SetInputData(cpd)
    ca = vtk.vtkActor2D(); ca.SetMapper(cm); ca.GetProperty().SetColor(0, 0.7, 0); ca.GetProperty().SetLineWidth(3)
    ren.AddActor2D(ca); rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.Update()
    wr = vtk.vtkPNGWriter(); out = Path("attachment/_diag_0327_feature_edges.png").resolve()
    wr.SetFileName(str(out)); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print("wrote", out)
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
