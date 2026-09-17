"""Pinpoint WHICH op in the actor-add scales with pre-existing actor count N.
Pre-build all meshes first (so mesh construction is out of the timed region), then
time each candidate separately against a renderer already holding N actors:
  (A) vtkRenderer.AddActor of a pre-built actor
  (B) creating mapper+actor+SetInputData (no AddActor)
  (C) actor.GetBounds() after SetInputData
  (D) ren.ComputeVisiblePropBounds() -- explicit scene-bounds recompute
Unbuffered.
"""
from __future__ import annotations
import sys, time
import numpy as np
import pyvista as pv
from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper, vtkRenderer


def log(m): sys.stdout.write(m + "\n"); sys.stdout.flush()


def make_actor(mesh, lw=1.0):
    mp = vtkDataSetMapper(); mp.SetInputData(mesh); mp.ScalarVisibilityOff()
    a = vtkActor(); a.SetMapper(mp); a.GetProperty().SetLineWidth(lw)
    return a


def preload(ren, n):
    for i in range(n):
        ren.AddActor(make_actor(pv.Line((0.0, 0.0, 0.0), (300.0, (i % 50) - 25.0, 60 + (i % 200) * 0.5)), 1.2))


def main():
    # one representative dimension mesh set, pre-built ONCE
    lo = np.array([100.0, 0.0, 60.0]); hi = lo + np.array([12.0, 0.0, 0.0])
    arrow = pv.Line(tuple(lo), tuple(hi)).tube(radius=0.1, n_sides=10)
    leader = pv.Line(tuple(lo), tuple(lo + np.array([0.0, 20.0, 0.0])))
    meshes = [arrow, leader, leader]  # 3 mesh actors per dim, like _emit_span_dimension

    for n in (0, 800, 1600, 3249):
        ren = vtkRenderer(); preload(ren, n)

        # (A) AddActor of pre-built actors, 16 dims x 3 actors
        actors = [make_actor(m) for _ in range(16) for m in meshes]
        t0 = time.perf_counter()
        for a in actors:
            ren.AddActor(a)
        addactor_ms = (time.perf_counter() - t0) * 1000

        # (B) build mapper+actor+SetInputData only (no AddActor), 16x3
        t0 = time.perf_counter()
        for _ in range(16):
            for m in meshes:
                make_actor(m)
        build_ms = (time.perf_counter() - t0) * 1000

        # (C) GetBounds after SetInputData, 16x3
        t0 = time.perf_counter()
        for _ in range(16):
            for m in meshes:
                a = make_actor(m); a.GetBounds()
        getbounds_ms = (time.perf_counter() - t0) * 1000

        # (D) explicit ComputeVisiblePropBounds once
        t0 = time.perf_counter()
        ren.ComputeVisiblePropBounds()
        cvpb_ms = (time.perf_counter() - t0) * 1000

        log(f"N={n:5d}: AddActor(48)={addactor_ms:7.2f}ms  build(48)={build_ms:7.2f}ms  "
            f"GetBounds(48)={getbounds_ms:7.2f}ms  ComputeVisiblePropBounds(1)={cvpb_ms:7.2f}ms")


if __name__ == "__main__":
    main()
