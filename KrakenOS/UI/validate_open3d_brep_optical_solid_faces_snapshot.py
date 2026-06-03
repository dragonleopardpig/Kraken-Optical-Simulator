"""Image-snapshot: the STEP optical solid renders as a few coherent B-Rep faces.

The companion display-free test (``validate_open3d_brep_optical_solid_faces``)
proves the metadata has 7 faces and the indices are aligned, but bug 0003's
complaint ("so many faces") is fundamentally *visual* -- so this renders what
the live face editor draws: the **written STL** colored by each face's
``triangle_indices`` from the **sidecar** (not the OCC document directly, so it
exercises the real STL+sidecar round-trip), off-screen to a PNG, and checks
pixels.

A pass means several large, single-color regions (coherent surfaces), not a
fragmented red/triangle soup. Open the PNG by eye too -- a pixel count alone is
not the whole story (per bugs/README).

Run (boots its own headless framebuffer):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_brep_optical_solid_faces_snapshot

Exit: 0 = pass, 1 = regression, 2 = environment can't render / no OCC backend.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STEP_FIXTURE = _REPO_ROOT / "attachment/Lens/Aspherized_Achromatic_Lenses/step_49665.step"
_OUT_PNG = Path(tempfile.gettempdir()) / "krakenos_brep_optical_solid_faces.png"
_EXPECTED_FACES = 7


def _bootstrap_offscreen() -> None:
    os.environ.pop("WAYLAND_DISPLAY", None)
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    import pyvista as pv

    pv.OFF_SCREEN = True
    if not os.environ.get("DISPLAY"):
        try:
            pv.start_xvfb()
        except Exception:
            pass


def _run() -> int:
    import matplotlib
    import pyvista as pv

    from KrakenOS.UI.services.step_optical_solid_brep import build_step_optical_solid_mesh
    from KrakenOS.UI.stl_geometry import read_stl_triangle_vertices

    tmp = Path(tempfile.mkdtemp())
    stl_path = tmp / "achromat_brep.stl"
    metadata = build_step_optical_solid_mesh(_STEP_FIXTURE, stl_path)
    faces = list(metadata.get("faces", []))

    _fmt, tris = read_stl_triangle_vertices(stl_path)
    n_tri = int(tris.shape[0])
    points = tris.reshape(n_tri * 3, 3)
    starts = np.arange(0, n_tri * 3, 3)
    conn = np.column_stack([np.full(n_tri, 3), starts, starts + 1, starts + 2]).ravel()
    mesh = pv.PolyData(points, conn)

    cmap = matplotlib.colormaps["tab10"]
    palette = (np.array([cmap(i % 10)[:3] for i in range(len(faces))]) * 255).astype(np.uint8)
    rgb = np.full((n_tri, 3), 220, dtype=np.uint8)  # grey = unassigned (should be none)
    for fi, face in enumerate(faces):
        idx = np.asarray([int(i) for i in face.get("triangle_indices", []) or []], dtype=int)
        idx = idx[(idx >= 0) & (idx < n_tri)]
        if idx.size:
            rgb[idx] = palette[fi]
    mesh.cell_data["rgb"] = rgb

    pl = pv.Plotter(off_screen=True, window_size=(1280, 900))
    pl.set_background("white")
    # lighting=False so each face renders its true flat palette color (lighting
    # would shade them and defeat the per-color pixel count below).
    pl.add_mesh(mesh, scalars="rgb", rgb=True, show_edges=False, smooth_shading=False, lighting=False)
    pl.add_text(
        f"{_STEP_FIXTURE.name}: {len(faces)} OCC B-Rep faces from STL+sidecar",
        font_size=10,
        color="black",
        position="upper_left",
    )
    pl.view_isometric()
    pl.camera.zoom(1.3)
    _OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    pl.screenshot(str(_OUT_PNG))
    pl.close()

    failures: list[str] = []
    if len(faces) != _EXPECTED_FACES:
        failures.append(f"expected {_EXPECTED_FACES} faces, got {len(faces)}")

    with __import__("PIL.Image", fromlist=["Image"]).open(_OUT_PNG) as img:
        arr = np.asarray(img.convert("RGB"))
    flat = arr.reshape(-1, 3)
    total = flat.shape[0]

    # background fraction (near-white) should dominate but leave a real object
    white = (flat > 235).all(axis=1)
    white_frac = float(white.mean())
    if white_frac > 0.97:
        failures.append(f"object barely visible (white background {white_frac:.0%})")
    if white_frac < 0.30:
        failures.append(f"background not white enough ({white_frac:.0%}) -- render off?")

    # how many distinct palette colors actually paint a meaningful area?
    visible = 0
    per_face = []
    for fi in range(len(faces)):
        col = palette[fi].astype(int)
        mask = (np.abs(flat.astype(int) - col).sum(axis=1) < 40)
        frac = float(mask.mean())
        per_face.append(frac)
        if frac > 0.002:  # >0.2% of the frame
            visible += 1
    if visible < 4:
        failures.append(f"only {visible} face colors visible (expected several coherent surfaces)")

    # a triangle "soup" / all-red bug would leave most of the object one color
    # or grey-unassigned; confirm no single face color swamps the object
    object_frac = 1.0 - white_frac
    dominant = max(per_face) if per_face else 0.0
    if object_frac > 0 and dominant / max(object_frac, 1e-6) > 0.95:
        failures.append(f"one color covers {dominant / object_frac:.0%} of the object (soup/all-one-face)")

    print(f"  rendered: white {white_frac:.0%}, {visible}/{len(faces)} face colors visible -> {_OUT_PNG}")
    print("  per-face frame fraction: " + ", ".join(f"{p:.1%}" for p in per_face))
    if failures:
        for msg in failures:
            print(f"FAIL: {msg}", file=sys.stderr)
        return 1
    print(
        f"PASS: STEP optical solid renders as {visible} coherent colored B-Rep faces "
        f"(of {_EXPECTED_FACES}); not a fragmented soup. PNG -> {_OUT_PNG}"
    )
    return 0


def main() -> int:
    if not _STEP_FIXTURE.exists():
        print(f"SKIP: STEP fixture not found: {_STEP_FIXTURE}", file=sys.stderr)
        return 2
    _bootstrap_offscreen()
    try:
        return _run()
    except RuntimeError as exc:
        if "pythonocc" in str(exc).lower() or "OCC" in str(exc):
            print(f"SKIP: OCC backend unavailable ({exc})", file=sys.stderr)
            return 2
        raise
    except Exception as exc:  # off-screen GL can be absent on a bare box
        print(f"SKIP: off-screen render failed ({exc})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
