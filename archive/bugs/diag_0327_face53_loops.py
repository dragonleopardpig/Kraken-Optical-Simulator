"""Does the front panel face 53's OUTLINE already contain the central square as an
inner loop?  If yes, the 0328 fix is light: snap plain-hover to the nearest connected
loop within a face's own outline (which includes inner hole loops), rather than
treating the whole outline as one rim or relying on the noisy global feature-edge graph.

Split face 53's outline into connected components, project each, and report which loop
is nearest the recorded cursor.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_face_index_edges import (
    face_outline_from_face_indices, line_segment_pairs)

CURSOR = np.array([850.0, 615.0]); W, H = 1838, 904
TARGETS = [53, 166, 86]  # camera-facing faces the cursor sits on (frontmost first)


def _cam(ren):
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(288.87023861611124, 36.60318223831546, 110.7787913880848)
    cam.SetFocalPoint(0.0, 0.0, 50.0)
    cam.SetViewUp(-0.08241583321912822, 0.9769984238369366, -0.19667666423584354)
    cam.SetParallelScale(101.15273775216139)


def _loops(n_points, pairs):
    # union-find connected components over segment endpoints
    parent = list(range(n_points))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    comps: dict[int, list[int]] = {}
    for a, b in pairs:
        comps.setdefault(find(a), set()).update((a, b))
    return [sorted(v) for v in comps.values()]


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    app.imported_led_step_path = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0
    mesh = app._transformed_imported_step_mesh_for_label("led")

    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H)
    _cam(ren); ren.ResetCameraClippingRange(); rw.Render()

    def proj(P):
        out = np.empty((len(P), 2))
        for i, p in enumerate(P):
            ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0); ren.WorldToDisplay()
            out[i] = np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]
        return out

    for fi in TARGETS:
        ol = face_outline_from_face_indices(mesh, (fi,))
        if ol is None or int(getattr(ol, "n_points", 0)) == 0:
            print(f"F{fi:04d}: no outline"); continue
        P = np.asarray(ol.points, dtype=float).reshape(-1, 3)
        pairs = line_segment_pairs(ol)
        comps = _loops(len(P), pairs)
        P2 = proj(P)
        print(f"\nF{fi:04d}: {len(P)} pts, {len(pairs)} segs, {len(comps)} connected loop(s)")
        rows = []
        for idx, comp in enumerate(comps):
            q = P2[comp]
            rimd = float(np.linalg.norm(q - CURSOR, axis=1).min())
            w3 = P[comp]
            span = w3.max(0) - w3.min(0)
            rows.append((rimd, idx, len(comp), span, (q[:,0].min(), q[:,0].max(), q[:,1].min(), q[:,1].max())))
        rows.sort(key=lambda r: r[0])
        for rimd, idx, n, span, bb in rows[:6]:
            print(f"   loop#{idx} n={n:4d} rim={rimd:5.0f}px worldspan=({span[0]:.1f},{span[1]:.1f},{span[2]:.1f}) "
                  f"screenbb=x[{bb[0]:.0f},{bb[1]:.0f}]y[{bb[2]:.0f},{bb[3]:.0f}]")
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
