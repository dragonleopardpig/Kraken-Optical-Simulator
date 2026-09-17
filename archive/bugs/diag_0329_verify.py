"""bugs/0329 -- flag_20260716_150110_640 "still can't highlight the CA opening" is
recorded AFTER 0328 shipped. Cursor [886,607] sits on the central SQUARE's top rim,
but hover resolved F005 (whole front panel) and the panel gold-highlighted.

Decide: does current-code 0328 (nearest_opening_loop) find the square for THIS
camera+cursor? If yes -> the live app was stale. If no -> 0328 has a live gap here.

Renders body + returned loop (red) + cursor (green) for proof.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_opening_loops import (
    opening_loops_for_mesh, nearest_opening_loop, loop_outline_polydata)

CURSOR = np.array([886.0, 607.0]); W, H = 1838, 904


def _cam(ren):
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(285.12211524555573, 44.86112856896071, 121.92167776210495)
    cam.SetFocalPoint(0.0, 0.0, 50.0)
    cam.SetViewUp(-0.13607788549386488, 0.9877295233717259, -0.0766367910300376)
    cam.SetParallelScale(101.15273775216139)


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    app.imported_led_step_path = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0
    mesh = app._transformed_imported_step_mesh_for_label("led")

    loops = opening_loops_for_mesh(mesh)
    print(f"mined opening loops: {len(loops)}")

    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H)
    _cam(ren); ren.ResetCameraClippingRange(); rw.Render()

    def project(p):
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0); ren.WorldToDisplay()
        return np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]

    # square = front-panel inner loop (perim ~176, centroid x>40)
    sq = [lp for lp in loops if 150 <= lp.perimeter <= 210 and lp.centroid[0] > 40]
    for lp in sq:
        cxy = project(lp.centroid)
        # min projected distance of cursor to this loop's rim
        rim = np.asarray([project(p) for p in lp.points])
        segd = np.min(np.linalg.norm(rim - CURSOR, axis=1))
        print(f"  square perim={lp.perimeter:.1f} c3d=({lp.centroid[0]:.1f},{lp.centroid[1]:.1f},"
              f"{lp.centroid[2]:.1f}) proj_centroid=({cxy[0]:.0f},{cxy[1]:.0f}) "
              f"min_rim_vtx_px={segd:.1f} gate_px={np.linalg.norm(cxy-CURSOR):.1f}")

    for tol in (30.0, 40.0, 60.0):
        picked = nearest_opening_loop(loops, CURSOR, project, tolerance_px=tol)
        if picked is None:
            print(f"PICK(tol={tol}): None")
        else:
            is_sq = 150 <= picked.perimeter <= 210 and picked.centroid[0] > 40
            print(f"PICK(tol={tol}): perim={picked.perimeter:.1f} area={picked.area:.0f} "
                  f"face={picked.face_index} is_square={is_sq}")

    picked = nearest_opening_loop(loops, CURSOR, project, tolerance_px=30.0)
    bm = vtk.vtkPolyDataMapper(); bm.SetInputData(mesh)
    ba = vtk.vtkActor(); ba.SetMapper(bm); ba.GetProperty().SetColor(0.6, 0.65, 0.7); ba.GetProperty().SetOpacity(0.4)
    ren.AddActor(ba)
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
    wr = vtk.vtkPNGWriter(); out = Path("attachment/_diag_0329_verify.png").resolve()
    wr.SetFileName(str(out)); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print("wrote", out)
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
