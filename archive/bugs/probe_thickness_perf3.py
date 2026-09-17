"""Test whether the O(N) per-dimension cost is Python GC scanning the thousands of
live VTK-wrapped objects from the ray preload. Compare _emit timing with gc ENABLED
vs DISABLED, and with light (pv.Line) vs heavier (sphere) preload actors that hold
more Python references. Also count gc collections during the dimension loop.
"""
from __future__ import annotations
import sys, time, gc
import numpy as np
import pyvista as pv
from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper, vtkRenderer, vtkBillboardTextActor3D


def log(m): sys.stdout.write(m + "\n"); sys.stdout.flush()


def make_actor(mesh, lw=1.0):
    mp = vtkDataSetMapper(); mp.SetInputData(mesh); mp.ScalarVisibilityOff()
    a = vtkActor(); a.SetMapper(mp); a.GetProperty().SetLineWidth(lw)
    return a


def preload(ren, n, heavy=False):
    keep = []  # mirror the app: actors + meshes stay referenced in Python maps
    for i in range(n):
        if heavy:
            m = pv.Sphere(radius=0.3, center=(300.0, (i % 50) - 25.0, 60 + (i % 100) * 0.5),
                          theta_resolution=12, phi_resolution=8)
        else:
            m = pv.Line((0.0, 0.0, 0.0), (300.0, (i % 50) - 25.0, 60 + (i % 200) * 0.5))
        a = make_actor(m, 1.2); ren.AddActor(a); keep.append((a, m))
    return keep


def arrow_mesh(lo, hi):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    d = hi - lo; L = float(np.linalg.norm(d)); u = d / L
    head = min(max(0.27, 0.75), max(L * 0.28, 0.75)); r = max(head * 0.2, 0.12); tr = max(r * 0.36, 0.06)
    ins = min(head, L * 0.45)
    line = pv.Line(tuple(lo + u * ins), tuple(hi - u * ins))
    parts = [line.tube(radius=tr, n_sides=10)]
    for tip, cd in ((lo, -u), (hi, u)):
        parts.append(pv.Cone(center=tuple(tip - cd * head * 0.5), direction=tuple(cd), height=head, radius=r, resolution=24))
    m = parts[0]
    for p in parts[1:]:
        m = m.merge(p)
    return m


def emit(ren, lo, hi, kept):
    side = np.array([0.0, 1.0, 0.0]); off = side * 20.0
    a = make_actor(arrow_mesh(lo + off, hi + off)); ren.AddActor(a); kept.append(a)
    for tip, anc in ((lo, lo + off), (hi, hi + off)):
        la = make_actor(pv.Line(tuple(tip), tuple(anc)), 2.2); ren.AddActor(la); kept.append(la)
    lbl = vtkBillboardTextActor3D(); lbl.SetInput("S1 = 42 mm"); lbl.SetPosition(float(lo[0]), 20.0, 60.0)
    ren.AddViewProp(lbl); kept.append(lbl)


def run(n, heavy, gc_on):
    ren = vtkRenderer()
    kept_pre = preload(ren, n, heavy=heavy)  # noqa: F841  keep refs alive
    if gc_on:
        gc.enable()
    else:
        gc.disable()
    gc.collect()
    before = gc.get_count()
    kept = []
    t0 = time.perf_counter()
    for d in range(16):
        lo = np.array([50.0 + d * 15.0, 0.0, 60.0]); emit(ren, lo, lo + np.array([12.0, 0.0, 0.0]), kept)
    dt = (time.perf_counter() - t0) * 1000
    after = gc.get_count()
    gc.enable()
    return dt, before, after, len(kept_pre)


def main():
    for heavy in (False, True):
        tag = "heavy(sphere)" if heavy else "light(line)"
        for n in (0, 3249):
            dt_on, b_on, a_on, _ = run(n, heavy, gc_on=True)
            dt_off, _, _, _ = run(n, heavy, gc_on=False)
            log(f"{tag:14s} N={n:5d}: gc_ON={dt_on:8.1f}ms ({dt_on/16:6.2f}/dim)  "
                f"gc_OFF={dt_off:8.1f}ms ({dt_off/16:6.2f}/dim)  gc_count {b_on}->{a_on}")


if __name__ == "__main__":
    main()
