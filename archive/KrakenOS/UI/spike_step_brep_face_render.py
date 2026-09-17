"""Spike: render an imported STEP solid by its native OpenCascade B-Rep faces.

Premise (see bugs/0003): the "optical solid" import goes STEP -> gmsh -> STL ->
re-cluster-triangles-by-plane, which shatters a curved optical surface into ~160
planar micro-faces. But the OCC analytic path (`load_step_analytic_document`)
already knows the true face topology -- for the aspheric achromat, 9 analytic
faces with a per-face triangle range. This spike proves the few-faces path end to
end: load via OCC, build ONE pyvista mesh tagged with a per-triangle `face_id`
straight from each face's `triangle_indices`, color by face, and render off-screen
to a PNG. No gmsh, no STL round-trip, no clustering.

If this reads as a handful of coherent colored surfaces (not a fragmented mess),
the optical-solid face editor can be re-pointed at this document instead of the
STL clusters.

Run (boots its own headless framebuffer):
    .devenv/state/venv/bin/python -m KrakenOS.UI.spike_step_brep_face_render
    .devenv/state/venv/bin/python -m KrakenOS.UI.spike_step_brep_face_render /path/to/other.step

Exit: 0 = rendered, 2 = environment can't render / no OCC backend.
"""
from __future__ import annotations

import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

_DEFAULT_STEP = Path("attachment/Lens/Aspherized_Achromatic_Lenses/step_49665.step")
_OUT_DIR = Path("attachment/step_brep_face_spike")


def _bootstrap_offscreen() -> None:
    """Force deterministic software off-screen GL, independent of the live desktop."""
    # A live Wayland/XWayland session makes off-screen GL flaky; a private Xvfb
    # with llvmpipe is reproducible everywhere a GitHub user would run this.
    os.environ.pop("WAYLAND_DISPLAY", None)
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    import pyvista as pv

    pv.OFF_SCREEN = True
    if not os.environ.get("DISPLAY"):
        try:
            pv.start_xvfb()
        except Exception:
            pass


def _build_face_tagged_mesh(triangles: np.ndarray, outer_faces):
    """One PolyData for the whole solid, with per-triangle face_id + a flat RGB.

    `triangles` is (N, 3, 3); face i owns the triangle rows in
    `outer_faces[i].triangle_indices`. Distinct flat color per face proves each
    B-Rep face is a single surface, not a triangle soup.
    """
    import matplotlib
    import pyvista as pv

    n_tri = int(triangles.shape[0])
    points = triangles.reshape(n_tri * 3, 3)
    starts = np.arange(0, n_tri * 3, 3)
    conn = np.column_stack(
        [np.full(n_tri, 3), starts, starts + 1, starts + 2]
    ).ravel()
    mesh = pv.PolyData(points, conn)

    face_id = np.full(n_tri, -1, dtype=np.int64)
    cmap = matplotlib.colormaps["tab20"]
    palette = (np.array([cmap(i % 20)[:3] for i in range(len(outer_faces))]) * 255).astype(np.uint8)
    rgb = np.zeros((n_tri, 3), dtype=np.uint8)
    for display_id, face in enumerate(outer_faces):
        idx = np.asarray(face.triangle_indices, dtype=np.int64)
        if idx.size:
            face_id[idx] = display_id
            rgb[idx] = palette[display_id]
    mesh.cell_data["face_id"] = face_id
    mesh.cell_data["rgb"] = rgb
    return mesh


def _render(mesh, outer_faces, out_path: Path, *, title: str) -> None:
    import pyvista as pv

    pl = pv.Plotter(off_screen=True, window_size=(1280, 900))
    pl.set_background("white")
    pl.add_mesh(mesh, scalars="rgb", rgb=True, show_edges=False, smooth_shading=False)

    centroids = np.array([f.centroid for f in outer_faces], dtype=float)
    labels = [f"{f.face_id}  {f.surface_type}" for f in outer_faces]
    pl.add_point_labels(
        centroids,
        labels,
        font_size=12,
        point_size=8,
        text_color="black",
        shape_color="white",
        shape_opacity=0.6,
        always_visible=True,
    )
    pl.add_text(title, font_size=10, color="black", position="upper_left")
    pl.view_isometric()
    pl.camera.zoom(1.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pl.screenshot(str(out_path))
    pl.close()


def main(argv: list[str]) -> int:
    step_path = Path(argv[1]) if len(argv) > 1 else _DEFAULT_STEP
    if not step_path.exists():
        print(f"SKIP: STEP fixture not found: {step_path}", file=sys.stderr)
        return 2

    _bootstrap_offscreen()

    try:
        from KrakenOS.UI.services.step_analytic_geometry import load_step_analytic_document
    except Exception as exc:
        print(f"SKIP: cannot import analytic STEP loader: {exc}", file=sys.stderr)
        return 2

    t0 = time.time()
    try:
        doc = load_step_analytic_document(step_path)
    except Exception as exc:
        print(f"SKIP: OCC could not load STEP ({exc})", file=sys.stderr)
        return 2
    t_load = time.time() - t0

    outer = list(doc.outer_faces)
    n_tri = int(doc.triangles.shape[0])
    types = Counter(f.surface_type for f in outer)

    print(f"STEP: {step_path}")
    print(f"  solids:          {doc.solid_count}")
    print(f"  raw STEP faces:  {doc.source_face_count}")
    print(f"  outer faces:     {len(outer)}   <-- the editor should show THIS, not 160")
    print(f"  by surface type: {dict(types)}")
    print(f"  triangles total: {n_tri}")
    print("  per-face triangles:")
    for f in outer:
        print(f"    {f.face_id:>10}  {f.surface_type:<10} area={f.area_mm2:8.2f} mm^2  tris={f.triangle_count}")
    print(f"  load+tessellate: {t_load:.2f}s")

    if n_tri == 0:
        print("FAIL: no triangles tessellated; nothing to render.", file=sys.stderr)
        return 2

    t1 = time.time()
    mesh = _build_face_tagged_mesh(doc.triangles, outer)
    t_build = time.time() - t1

    out_path = _OUT_DIR / f"{step_path.stem}_brep_faces.png"
    title = (
        f"{step_path.name}\n"
        f"{len(outer)} B-Rep faces  ({', '.join(f'{v} {k}' for k, v in types.items())})\n"
        f"{n_tri} triangles, one mesh tagged by face_id  |  load {t_load:.2f}s"
    )
    t2 = time.time()
    try:
        _render(mesh, outer, out_path, title=title)
    except Exception as exc:
        print(f"SKIP: off-screen render failed ({exc})", file=sys.stderr)
        return 2
    t_render = time.time() - t2

    print(f"  build mesh:      {t_build:.2f}s")
    print(f"  render:          {t_render:.2f}s")
    print(f"PNG -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
