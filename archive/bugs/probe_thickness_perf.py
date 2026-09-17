"""Localize the thickness-dimension per-dimension cost. NO render window (the app's
timed block never renders) -- just PyVista mesh construction + vtkRenderer.AddActor
bookkeeping, which need no GL context. Unbuffered, flushes every line.

Measures, as a function of pre-existing actor count N in the renderer:
  (1) arrow_mesh build alone (pure PyVista Line.tube + 2 Cone + merge)
  (2) full _emit_span_dimension equivalent: arrow + 2 leaders + billboard label,
      each AddActor/AddViewProp'd to a renderer already holding N ray actors.
If (2) grows with N but (1) is flat, the cost is in the VTK actor-add, not geometry.
"""
from __future__ import annotations
import sys, time
import numpy as np
import pyvista as pv
from vtkmodules.vtkRenderingCore import (
    vtkActor, vtkDataSetMapper, vtkRenderer, vtkBillboardTextActor3D,
)


def log(msg):
    sys.stdout.write(msg + "\n"); sys.stdout.flush()


def _add_mesh_actor(ren, mesh, *, line_width=1.0):
    mapper = vtkDataSetMapper(); mapper.SetInputData(mesh); mapper.ScalarVisibilityOff()
    actor = vtkActor(); actor.SetMapper(mapper); actor.GetProperty().SetLineWidth(line_width)
    ren.AddActor(actor)
    return actor


def _preload(ren, n):
    for i in range(n):
        line = pv.Line((0.0, 0.0, 0.0), (300.0, (i % 50) - 25.0, 60 + (i % 200) * 0.5))
        _add_mesh_actor(ren, line, line_width=1.2)


def _arrow_mesh(start, end):
    start = np.asarray(start, float); end = np.asarray(end, float)
    delta = end - start; length = float(np.linalg.norm(delta)); direction = delta / length
    head = min(max(15.0 * 0.018, 0.75), max(length * 0.28, 0.75))
    radius = max(head * 0.20, 0.12); tube_radius = max(radius * 0.36, 0.06)
    inset = min(head, length * 0.45)
    line = pv.Line(tuple(start + direction * inset), tuple(end - direction * inset))
    parts = [line.tube(radius=tube_radius, n_sides=10)]
    for tip, cd in ((start, -direction), (end, direction)):
        parts.append(pv.Cone(center=tuple(tip - cd * (head * 0.5)), direction=tuple(cd),
                             height=head, radius=radius, resolution=24))
    merged = parts[0]
    for p in parts[1:]:
        merged = merged.merge(p)
    return merged


def _emit(ren, base_lo, base_hi, *, make_label=True):
    side = np.array([0.0, 1.0, 0.0]); offset = side * 20.0
    start = base_lo + offset; end = base_hi + offset
    _add_mesh_actor(ren, _arrow_mesh(start, end))
    for tip, anchor in ((base_lo, start), (base_hi, end)):
        _add_mesh_actor(ren, pv.Line(tuple(tip), tuple(anchor)), line_width=2.2)
    if make_label:
        label = vtkBillboardTextActor3D(); label.SetInput("S1 Thickness = 42.45 mm")
        pos = 0.5 * (start + end) + side * 15.0
        label.SetPosition(float(pos[0]), float(pos[1]), float(pos[2]))
        ren.AddViewProp(label)


def main():
    log(f"pyvista {pv.__version__}")
    # (1) arrow_mesh build alone, no renderer
    t0 = time.perf_counter()
    for d in range(16):
        lo = np.array([50.0 + d * 15.0, 0.0, 60.0]); _arrow_mesh(lo, lo + np.array([12.0, 0.0, 0.0]))
    log(f"(1) 16x arrow_mesh build (no renderer): {(time.perf_counter()-t0)*1000:.1f} ms")

    # (2) full emit into a renderer preloaded with N actors
    for n in (0, 300, 1600, 3249):
        ren = vtkRenderer()
        tp = time.perf_counter(); _preload(ren, n); pre_ms = (time.perf_counter()-tp)*1000
        t0 = time.perf_counter()
        for d in range(16):
            lo = np.array([50.0 + d * 15.0, 0.0, 60.0]); _emit(ren, lo, lo + np.array([12.0, 0.0, 0.0]))
        dt = (time.perf_counter()-t0)*1000
        log(f"(2) N={n:5d} (preload {pre_ms:7.1f}ms): 16 dims -> {dt:8.1f} ms ({dt/16:6.2f} ms/dim)")

    # (3) same but WITHOUT the billboard label, to isolate the label cost
    for n in (0, 3249):
        ren = vtkRenderer(); _preload(ren, n)
        t0 = time.perf_counter()
        for d in range(16):
            lo = np.array([50.0 + d * 15.0, 0.0, 60.0]); _emit(ren, lo, lo + np.array([12.0, 0.0, 0.0]), make_label=False)
        dt = (time.perf_counter()-t0)*1000
        log(f"(3) N={n:5d} NO label: 16 dims -> {dt:8.1f} ms ({dt/16:6.2f} ms/dim)")

    # (4) billboard label construction alone (no preload, no renderer add)
    t0 = time.perf_counter()
    for d in range(16):
        label = vtkBillboardTextActor3D(); label.SetInput("S1 Thickness = 42.45 mm")
        label.SetPosition(float(d), 0.0, 0.0)
    log(f"(4) 16x vtkBillboardTextActor3D construct alone: {(time.perf_counter()-t0)*1000:.1f} ms")


if __name__ == "__main__":
    main()
