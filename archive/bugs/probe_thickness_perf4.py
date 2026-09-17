"""DEFINITIVE: real off-screen render window (like the app), preload 3249 ray line
actors, do ONE initial Render (realise camera/bounds), THEN time adding 16 dimensions
(arrow + 2 leaders + 1 billboard label) -- with billboard vs without, and time a bare
_visible_actor_bounds-style full GetActors() traversal. Prints per-dimension timing so
we see if cost grows as more dimension actors accumulate.

Also times the renderer full-actor bounds scan (the app's _visible_actor_bounds default
path) at N=3249 to confirm its magnitude on a realised window.
"""
from __future__ import annotations
import sys, time
import numpy as np
import pyvista as pv
from vtkmodules.vtkRenderingCore import (
    vtkActor, vtkDataSetMapper, vtkRenderer, vtkRenderWindow, vtkBillboardTextActor3D,
)


def log(m): sys.stdout.write(m + "\n"); sys.stdout.flush()


def make_actor(mesh, lw=1.0):
    mp = vtkDataSetMapper(); mp.SetInputData(mesh); mp.ScalarVisibilityOff()
    a = vtkActor(); a.SetMapper(mp); a.GetProperty().SetLineWidth(lw)
    return a


def full_actor_bounds_scan(ren):
    mins = np.array((np.inf,)*3); maxs = np.array((-np.inf,)*3)
    actors = ren.GetActors(); actors.InitTraversal()
    for _ in range(actors.GetNumberOfItems()):
        a = actors.GetNextActor()
        if a is None:
            continue
        try:
            if not int(a.GetVisibility()):
                continue
            b = np.asarray(a.GetBounds(), float).reshape(6)
        except Exception:
            continue
        if b.size != 6 or not np.all(np.isfinite(b)) or b[0] > b[1]:
            continue
        mins = np.minimum(mins, (b[0], b[2], b[4])); maxs = np.maximum(maxs, (b[1], b[3], b[5]))
    return mins, maxs


def arrow_mesh(lo, hi):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    d = hi - lo; L = float(np.linalg.norm(d)); u = d / L
    head = max(0.75, min(L * 0.28, 0.75) if L * 0.28 < 0.75 else L * 0.28)
    r = max(head * 0.2, 0.12); tr = max(r * 0.36, 0.06); ins = min(head, L * 0.45)
    line = pv.Line(tuple(lo + u * ins), tuple(hi - u * ins))
    parts = [line.tube(radius=tr, n_sides=10)]
    for tip, cd in ((lo, -u), (hi, u)):
        parts.append(pv.Cone(center=tuple(tip - cd * head * 0.5), direction=tuple(cd), height=head, radius=r, resolution=24))
    m = parts[0]
    for p in parts[1:]:
        m = m.merge(p)
    return m


def emit(ren, lo, hi, kept, *, label=True):
    side = np.array([0.0, 1.0, 0.0]); off = side * 20.0
    a = make_actor(arrow_mesh(lo + off, hi + off)); ren.AddActor(a); kept.append(a)
    for tip, anc in ((lo, lo + off), (hi, hi + off)):
        la = make_actor(pv.Line(tuple(tip), tuple(anc)), 2.2); ren.AddActor(la); kept.append(la)
    if label:
        lbl = vtkBillboardTextActor3D(); lbl.SetInput("S1 Thickness = 42.45 mm")
        p = 0.5 * (lo + hi) + off + side * 15.0
        lbl.SetPosition(float(p[0]), float(p[1]), float(p[2]))
        tp = lbl.GetTextProperty(); tp.SetFontSize(13)
        ren.AddViewProp(lbl); kept.append(lbl)


def main():
    N = 3249
    rw = vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.SetSize(1100, 720)
    ren = vtkRenderer(); rw.AddRenderer(ren); ren.SetBackground(1, 1, 1)
    cam = ren.GetActiveCamera(); cam.SetPosition(-400, -400, 400); cam.SetFocalPoint(150, 0, 60); cam.SetViewUp(0, 0, 1)
    log(f"preloading {N} ray actors...")
    t0 = time.perf_counter()
    for i in range(N):
        ren.AddActor(make_actor(pv.Line((0.0, 0.0, 0.0), (300.0, (i % 50) - 25.0, 60 + (i % 200) * 0.5)), 1.2))
    log(f"  preload {(time.perf_counter()-t0):.1f}s; initial Render()...")
    t0 = time.perf_counter(); rw.Render(); log(f"  initial Render {(time.perf_counter()-t0):.1f}s")

    for use_label in (True, False):
        kept = []
        per = []
        for d in range(16):
            lo = np.array([50.0 + d * 15.0, 0.0, 60.0]); hi = lo + np.array([12.0, 0.0, 0.0])
            t0 = time.perf_counter(); emit(ren, lo, hi, kept, label=use_label); per.append((time.perf_counter()-t0)*1000)
        log(f"label={use_label}: total 16 dims = {sum(per):8.1f} ms  first={per[0]:7.1f}  last={per[-1]:7.1f}  mean={sum(per)/16:7.1f} ms/dim")
        # remove the dimension actors we just added so the next pass starts clean-ish
        for a in kept:
            try: ren.RemoveActor(a)
            except Exception:
                try: ren.RemoveViewProp(a)
                except Exception: pass

    # the app's _visible_actor_bounds default full scan, once, at this scale
    t0 = time.perf_counter(); full_actor_bounds_scan(ren); log(f"full GetActors() bounds scan (1x, N={N}): {(time.perf_counter()-t0)*1000:.1f} ms")
    t0 = time.perf_counter(); ren.ComputeVisiblePropBounds(); log(f"ComputeVisiblePropBounds (1x): {(time.perf_counter()-t0)*1000:.1f} ms")

    try: rw.Finalize()
    except Exception: pass


if __name__ == "__main__":
    main()
