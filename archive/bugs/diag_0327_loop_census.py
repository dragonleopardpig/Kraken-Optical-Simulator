"""Feasibility + census for the 0328 global opening-loop cache: how many faces, how
many closed loops (after welding + a scale-relative filter), and how long to build.
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_face_index_edges import (
    face_outline_from_face_indices, line_segment_pairs, triangle_array_and_face_index)


def _weld(P, pairs, tol=1e-4):
    keys = {}; remap = np.empty(len(P), dtype=int); uniq = []
    for i, p in enumerate(P):
        k = (round(p[0]/tol), round(p[1]/tol), round(p[2]/tol))
        j = keys.get(k)
        if j is None:
            j = len(uniq); keys[k] = j; uniq.append(p)
        remap[i] = j
    U = np.array(uniq); wp = set()
    for a, b in pairs:
        ra, rb = int(remap[a]), int(remap[b])
        if ra != rb:
            wp.add((min(ra, rb), max(ra, rb)))
    return U, sorted(wp)


def _trace(n, pairs):
    from collections import defaultdict
    adj = defaultdict(list)
    for a, b in pairs:
        adj[a].append(b); adj[b].append(a)
    seen = set(); loops = []
    for s in list(adj):
        for nx in adj[s]:
            e0 = (min(s, nx), max(s, nx))
            if e0 in seen:
                continue
            loop = [s]; prev, cur = s, nx; seen.add(e0); ok = True
            while cur != s:
                loop.append(cur)
                nb = [x for x in adj[cur] if x != prev]
                if len(nb) != 1:
                    ok = False; break
                prev, nn = cur, nb[0]; seen.add((min(cur, nn), max(cur, nn))); cur = nn
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
    diag = float(np.linalg.norm(np.ptp(np.array(mesh.bounds).reshape(3, 2), axis=1)))
    tris, fidx = triangle_array_and_face_index(mesh); fidx = np.asarray(fidx, int)
    faces = np.unique(fidx)
    print(f"mesh diag={diag:.1f}mm, faces={len(faces)}")

    # per-face area (for the large-face gate)
    def face_area(fi):
        sel = tris[fidx == fi]
        v0, v1, v2 = sel[:, 0], sel[:, 1], sel[:, 2]
        return float(0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1).sum())

    AREA_GATE = 500.0
    t0 = time.perf_counter()
    kept = 0; total_loops = 0; per_hist = []; big_faces = 0
    for fi in faces:
        if face_area(fi) < AREA_GATE:
            continue
        big_faces += 1
        ol = face_outline_from_face_indices(mesh, (int(fi),))
        if ol is None or int(getattr(ol, "n_points", 0)) == 0:
            continue
        P = np.asarray(ol.points, dtype=float).reshape(-1, 3)
        pairs = line_segment_pairs(ol)
        U, wp = _weld(P, pairs)
        loops = _trace(len(U), wp)
        total_loops += len(loops)
        for loop in loops:
            w = U[loop]
            per = float(np.linalg.norm(np.diff(np.vstack([w, w[:1]]), axis=0), axis=1).sum())
            bbdiag = float(np.linalg.norm(w.max(0) - w.min(0)))
            if per >= 12.0 and bbdiag <= 0.9 * diag:
                kept += 1; per_hist.append(per)
    dt = time.perf_counter() - t0
    ph = np.array(per_hist)
    print(f"faces with area>={AREA_GATE:.0f}: {big_faces}")
    print(f"total closed loops={total_loops}; kept (per>=12mm & bbdiag<=0.9*diag)={kept}")
    if ph.size:
        print(f"kept perimeter mm: min={ph.min():.1f} med={np.median(ph):.1f} max={ph.max():.1f}")
        print(f"kept perimeters: {sorted(round(v,1) for v in per_hist)}")
    print(f"large-face extract+weld+trace+filter time: {dt*1000:.0f} ms")
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
