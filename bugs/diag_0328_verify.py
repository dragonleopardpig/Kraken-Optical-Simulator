"""bugs/0328 end-to-end: with the REAL ILS0202 LED + the recorded flag camera/cursor,
the mined opening-loop pick returns the CENTRAL SQUARE (not the +y tray slot F266).
Render body + returned loop (red) + old auto-CA face266 (gold) + cursor (green) for proof.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_opening_loops import (
    opening_loops_for_mesh, nearest_opening_loop, loop_outline_polydata)
from KrakenOS.UI.services.open3d_face_index_edges import face_outline_from_face_indices

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

    loops = opening_loops_for_mesh(mesh)
    print(f"mined opening loops: {len(loops)}")
    # is the central square present? (front +x panel, perimeter ~176mm)
    sq = [lp for lp in loops if 150 <= lp.perimeter <= 210 and lp.centroid[0] > 40]
    print(f"front-panel square-sized loops: {len(sq)}")
    for lp in sq:
        print(f"   perim={lp.perimeter:.1f} area={lp.area:.0f} c=({lp.centroid[0]:.1f},"
              f"{lp.centroid[1]:.1f},{lp.centroid[2]:.1f}) face={lp.face_index}")

    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H)
    _cam(ren); ren.ResetCameraClippingRange(); rw.Render()

    def project(p):
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0); ren.WorldToDisplay()
        return np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]

    picked = nearest_opening_loop(loops, CURSOR, project, tolerance_px=30.0)
    if picked is None:
        print("PICK: None (FAIL -- cursor not near any mined opening)")
    else:
        print(f"PICK: perim={picked.perimeter:.1f} area={picked.area:.0f} "
              f"c=({picked.centroid[0]:.1f},{picked.centroid[1]:.1f},{picked.centroid[2]:.1f}) "
              f"face={picked.face_index}")
        is_square = 150 <= picked.perimeter <= 210 and picked.centroid[0] > 40
        print("PICK is the central square:", is_square)

    # render proof
    bm = vtk.vtkPolyDataMapper(); bm.SetInputData(mesh)
    ba = vtk.vtkActor(); ba.SetMapper(bm); ba.GetProperty().SetColor(0.6, 0.65, 0.7); ba.GetProperty().SetOpacity(0.4)
    ren.AddActor(ba)
    gold = face_outline_from_face_indices(mesh, (266,))
    if gold is not None:
        gm = vtk.vtkPolyDataMapper(); gm.SetInputData(gold)
        ga = vtk.vtkActor(); ga.SetMapper(gm); ga.GetProperty().SetColor(1.0, 0.8, 0.0); ga.GetProperty().SetLineWidth(4)
        ren.AddActor(ga)
    if picked is not None:
        pol = loop_outline_polydata(picked)
        pm = vtk.vtkPolyDataMapper(); pm.SetInputData(pol)
        pa = vtk.vtkActor(); pa.SetMapper(pm); pa.GetProperty().SetColor(1.0, 0.0, 0.0); pa.GetProperty().SetLineWidth(6)
        ren.AddActor(pa)
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
    wr = vtk.vtkPNGWriter(); out = Path("attachment/_diag_0328_verify.png").resolve()
    wr.SetFileName(str(out)); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print("wrote", out)
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
