"""Weld face 53's outline by coordinate and trace closed loops; confirm the central
square is one clean closed loop near the cursor.  This validates the 0328 approach:
detect openings as inner boundary loops of large faces, then snap plain-hover to the
nearest such loop's rim.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_face_index_edges import (
    face_outline_from_face_indices, line_segment_pairs)

CURSOR = np.array([850.0, 615.0]); W, H = 1838, 904


def _cam(ren):
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(288.87023861611124, 36.60318223831546, 110.7787913880848)
    cam.SetFocalPoint(0.0, 0.0, 50.0)
    cam.SetViewUp(-0.08241583321912822, 0.9769984238369366, -0.19667666423584354)
    cam.SetParallelScale(101.15273775216139)


def _weld(P, pairs, tol=1e-4):
    keys = {}
    remap = np.empty(len(P), dtype=int)
    uniq = []
    for i, p in enumerate(P):
        k = (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
        j = keys.get(k)
        if j is None:
            j = len(uniq); keys[k] = j; uniq.append(p)
        remap[i] = j
    U = np.array(uniq)
    wpairs = set()
    for a, b in pairs:
        ra, rb = int(remap[a]), int(remap[b])
        if ra != rb:
            wpairs.add((min(ra, rb), max(ra, rb)))
    return U, sorted(wpairs)


def _trace_loops(n, pairs):
    from collections import defaultdict
    adj = defaultdict(list)
    for a, b in pairs:
        adj[a].append(b); adj[b].append(a)
    # only closed loops: every vertex degree 2 within the loop
    seen_edges = set()
    loops = []
    for start in list(adj):
        for nxt in adj[start]:
            e0 = (min(start, nxt), max(start, nxt))
            if e0 in seen_edges:
                continue
            loop = [start]; prev, cur = start, nxt
            seen_edges.add(e0); ok = True
            while cur != start:
                loop.append(cur)
                nbrs = [x for x in adj[cur] if x != prev]
                if len(nbrs) != 1:
                    ok = False; break
                prev, nn = cur, nbrs[0]
                seen_edges.add((min(cur, nn), max(cur, nn)))
                cur = nn
                if len(loop) > 100000:
                    ok = False; break
            if ok and len(loop) >= 3:
                loops.append(loop)
    return loops


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

    ol = face_outline_from_face_indices(mesh, (53,))
    P = np.asarray(ol.points, dtype=float).reshape(-1, 3)
    pairs = line_segment_pairs(ol)
    U, wpairs = _weld(P, pairs)
    loops = _trace_loops(len(U), wpairs)
    print(f"F0053 outline welded: {len(U)} verts, {len(wpairs)} edges -> {len(loops)} closed loop(s)")
    U2 = proj(U)
    rows = []
    for li, loop in enumerate(loops):
        q = U2[loop]
        w = U[loop]
        # perimeter world length + screen rim distance + area estimate
        per = float(np.linalg.norm(np.diff(np.vstack([w, w[:1]]), axis=0), axis=1).sum())
        rimd = float(np.linalg.norm(q - CURSOR, axis=1).min())
        # even-odd contains cursor?
        inside = False; nseg = len(q); j = nseg - 1
        for i in range(nseg):
            xi, yi = q[i]; xj, yj = q[j]
            if ((yi > CURSOR[1]) != (yj > CURSOR[1])) and (CURSOR[0] < (xj-xi)*(CURSOR[1]-yi)/(yj-yi+1e-12)+xi):
                inside = not inside
            j = i
        rows.append((rimd, li, len(loop), per, inside, (q[:,0].min(),q[:,0].max(),q[:,1].min(),q[:,1].max())))
    rows.sort(key=lambda r: r[0])
    print("closest loops to cursor (rim px | verts | world-perimeter | contains-cursor | screenbb):")
    for rimd, li, n, per, inside, bb in rows[:8]:
        print(f"   loop#{li} n={n:3d} rim={rimd:5.0f}px per={per:7.1f}mm contains={inside} "
              f"bb=x[{bb[0]:.0f},{bb[1]:.0f}]y[{bb[2]:.0f},{bb[3]:.0f}]")
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
