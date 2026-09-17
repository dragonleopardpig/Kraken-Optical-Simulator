"""Faithful offscreen repro of flag_20260716_134203_962 ("no improvement at all").

Loads the REAL LED overlay transform (bounds match the recorded step_actor_bounds),
renders it with the recorded camera, highlights the auto-detected CA opening
(face 266) rim, and marks the recorded cursor -- so we can eyeball whether the
detected opening is the window the user is actually hovering.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import vtk

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_face_index_edges import face_outline_from_face_indices

CURSOR_VTK = (850.0, 615.0)
W, H = 1838, 904
CAM_POS = (288.87023861611124, 36.60318223831546, 110.7787913880848)
CAM_FOCAL = (0.0, 0.0, 50.0)
CAM_UP = (-0.08241583321912822, 0.9769984238369366, -0.19667666423584354)
CAM_SCALE = 101.15273775216139


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    app.imported_led_step_path = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
    app.led_step_rotation_x_deg = 0.0
    app.led_step_rotation_y_deg = 0.0
    app.led_step_rotation_z_deg = 0.0

    mesh = app._transformed_imported_step_mesh_for_label("led")
    print("mesh bounds:", [round(v, 2) for v in mesh.bounds])
    auto = app.auto_detect_step_clear_aperture_candidates("led")
    fi = int(auto[0].face_index)
    print("auto[0] face_index:", fi)

    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren)
    rw.SetSize(W, H)

    # LED body (translucent)
    body_map = vtk.vtkPolyDataMapper()
    body_map.SetInputData(mesh)
    body_act = vtk.vtkActor()
    body_act.SetMapper(body_map)
    body_act.GetProperty().SetColor(0.6, 0.65, 0.7)
    body_act.GetProperty().SetOpacity(0.45)
    ren.AddActor(body_act)

    # CA rim (thick gold)
    outline = face_outline_from_face_indices(mesh, (fi,))
    rim_map = vtk.vtkPolyDataMapper()
    rim_map.SetInputData(outline)
    rim_act = vtk.vtkActor()
    rim_act.SetMapper(rim_map)
    rim_act.GetProperty().SetColor(1.0, 0.8, 0.0)
    rim_act.GetProperty().SetLineWidth(5)
    ren.AddActor(rim_act)

    cam = ren.GetActiveCamera()
    cam.SetParallelProjection(True)
    cam.SetPosition(*CAM_POS)
    cam.SetFocalPoint(*CAM_FOCAL)
    cam.SetViewUp(*CAM_UP)
    cam.SetParallelScale(CAM_SCALE)
    ren.ResetCameraClippingRange()
    rw.Render()

    # cursor crosshair (display-space) as a 2D actor
    pts = vtk.vtkPoints()
    cx, cy = CURSOR_VTK
    for dx, dy in ((-20, 0), (20, 0), (0, -20), (0, 20)):
        pts.InsertNextPoint(cx + dx, cy + dy, 0)
    lines = vtk.vtkCellArray()
    for a, b in ((0, 1), (2, 3)):
        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, a)
        line.GetPointIds().SetId(1, b)
        lines.InsertNextCell(line)
    cross = vtk.vtkPolyData()
    cross.SetPoints(pts)
    cross.SetLines(lines)
    cmap = vtk.vtkPolyDataMapper2D()
    cmap.SetInputData(cross)
    cact = vtk.vtkActor2D()
    cact.SetMapper(cmap)
    cact.GetProperty().SetColor(1, 0, 0)
    cact.GetProperty().SetLineWidth(3)
    ren.AddActor2D(cact)
    rw.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.Update()
    writer = vtk.vtkPNGWriter()
    out = Path("attachment/_diag_0327_live_repro.png").resolve()
    writer.SetFileName(str(out))
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()
    print("wrote", out)

    # distances of ALL candidate rims to the cursor
    def project(p):
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0)
        ren.WorldToDisplay()
        return np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]

    cur = np.array(CURSOR_VTK)
    print("\ncandidate rim distances to cursor:")
    for c in auto:
        cfi = int(c.face_index)
        ol = face_outline_from_face_indices(mesh, (cfi,))
        if ol is None:
            continue
        P = np.asarray(ol.points, dtype=float).reshape(-1, 3)
        pj = np.array([project(p) for p in P])
        d = np.linalg.norm(pj - cur, axis=1).min()
        print(f"  face {cfi}: centroid={[round(v,1) for v in c.centroid]} "
              f"normal={[round(v,2) for v in c.normal]} -> min {d:.0f}px  "
              f"proj y[{pj[:,1].min():.0f},{pj[:,1].max():.0f}]")
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
