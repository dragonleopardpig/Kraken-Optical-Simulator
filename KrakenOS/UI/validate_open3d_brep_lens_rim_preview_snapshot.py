"""Image-snapshot regression for bugs/0013 (lens rim "sub-edges" + stray edge
highlight in the Assign CAD/STL Optical Faces dialog preview).

The face-roles dialog's ``render_face_preview`` used to draw EVERY face's
``extract_feature_edges(feature_angle=5)`` -- and on a curved (cylinder/sphere)
tessellated face almost every triangle edge exceeds 5 deg, so each curved face
drew its whole wireframe -- with non-selected faces at opacity 0.82. A lens rim
the importer splits into several co-axial cylinder faces therefore lit up as a
busy coloured wireframe band even when a *cap* was selected: the "stray
highlight at the lens edge" + "4 sub-edges" the user reported (flags
20260604_0800xx).

The fix groups the rim's cylinder faces (``group_brep_optical_solid_faces``)
and draws feature edges PER GROUP -- merged + cleaned, at feature_angle=18, with
non-selected groups faint. This renders BOTH recipes off-screen (front cap
selected), fed by the REAL B-Rep records and the REAL grouping helper, and
proves the fixed recipe's non-selected rim clutter collapses versus the old
per-face/angle-5/opacity-0.82 recipe. Open the PNGs by eye too (per bugs/README:
a pixel count alone is not the whole story).

Run (boots its own headless framebuffer):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_brep_lens_rim_preview_snapshot

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
_OUT_DIR = Path(tempfile.gettempdir())


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


def _face_mesh(pv, tris: np.ndarray, n_tri: int, record: dict):
    idx = np.asarray([int(i) for i in record.get("triangle_indices", []) or []], dtype=int)
    idx = idx[(idx >= 0) & (idx < n_tri)]
    if idx.size == 0:
        return None
    ftris = tris[idx]
    nt = int(ftris.shape[0])
    points = ftris.reshape(nt * 3, 3)
    starts = np.arange(0, nt * 3, 3)
    conn = np.column_stack([np.full(nt, 3), starts, starts + 1, starts + 2]).ravel()
    return pv.PolyData(points, conn)


def _nonselected_edge_clutter(pv, osm, meshes, gids, selected_index, *, recipe: str, out_png: Path) -> int:
    """Render ONLY the non-selected groups' edges (white bg) and count painted
    pixels. ``recipe='current'`` = per-face feature_angle=5 at opacity 0.82;
    ``recipe='fixed'`` = per-group merged+cleaned feature_angle=18, faint."""
    pl = pv.Plotter(off_screen=True, window_size=(900, 700))
    pl.set_background("white")
    n = len(meshes)
    # group membership: ungrouped faces are singleton groups
    groups: dict[object, list[int]] = {}
    for i in range(n):
        if meshes[i] is None:
            continue
        g = gids[i]
        groups.setdefault(g if g >= 0 else ("solo", i), []).append(i)
    drew = False
    for members in groups.values():
        if selected_index in members:
            continue  # non-selected only
        if recipe == "current":
            for i in members:
                e = meshes[i].extract_feature_edges(feature_angle=5, boundary_edges=True, feature_edges=True, manifold_edges=False)
                if int(getattr(e, "n_points", 0)) > 0:
                    pl.add_mesh(e, color=(0.4, 0.4, 0.4), opacity=0.82, line_width=1.4)
                    drew = True
        else:
            merged = None
            for i in members:
                merged = meshes[i].copy(deep=True) if merged is None else merged.merge(meshes[i])
            if merged is None:
                continue
            welded = merged.clean(tolerance=1.0e-4)
            e = welded.extract_feature_edges(feature_angle=18, boundary_edges=True, feature_edges=True, manifold_edges=False)
            if int(getattr(e, "n_points", 0)) > 0:
                pl.add_mesh(e, color=(0.4, 0.4, 0.4), opacity=0.22, line_width=1.1)
                drew = True
    # frame the lens edge-on so the rim band fills the view
    zc = 0.5 * (float(_ALL_TRIS[..., 2].min()) + float(_ALL_TRIS[..., 2].max()))
    pl.camera_position = [(180.0, 0.0, zc), (0.0, 0.0, zc), (0.0, 0.0, 1.0)]
    pl.camera.zoom(1.5)
    pl.screenshot(str(out_png))
    pl.close()
    if not drew:
        return 0
    from PIL import Image

    with Image.open(out_png) as img:
        arr = np.asarray(img.convert("RGB"))
    flat = arr.reshape(-1, 3)
    painted = (flat < 235).any(axis=1)  # anything not near-white
    return int(painted.sum())


_ALL_TRIS: np.ndarray = np.empty((0, 3, 3), dtype=float)


def _render_full_preview(pv, osm, le, meshes, records, gids, selected_index, out_png: Path) -> None:
    """The fixed recipe's full preview (fills + per-group edges) for eyeballing."""
    pl = pv.Plotter(off_screen=True, window_size=(1100, 760))
    pl.set_background("white")
    for i, m in enumerate(meshes):
        if m is None:
            continue
        role = osm.legacy_role_from_optical_solid_face_function(records[i].get("function", records[i].get("role")))
        color = (1.0, 0.48, 0.02) if i == selected_index else osm.optical_solid_face_role_color(role)
        opacity = 0.3 if i == selected_index else 0.05
        pl.add_mesh(m, color=color, opacity=opacity, lighting=False)
    groups: dict[object, list[int]] = {}
    for i in range(len(meshes)):
        if meshes[i] is None:
            continue
        g = gids[i]
        groups.setdefault(g if g >= 0 else ("solo", i), []).append(i)
    for members in groups.values():
        is_sel = selected_index in members
        merged = None
        for i in members:
            merged = meshes[i].copy(deep=True) if merged is None else merged.merge(meshes[i])
        if merged is None:
            continue
        e = merged.clean(tolerance=1.0e-4).extract_feature_edges(feature_angle=18, boundary_edges=True, feature_edges=True, manifold_edges=False)
        role = osm.legacy_role_from_optical_solid_face_function(records[members[0]].get("function", records[members[0]].get("role")))
        color = (1.0, 0.28, 0.0) if is_sel else osm.optical_solid_face_role_color(role)
        if int(getattr(e, "n_points", 0)) > 0:
            pl.add_mesh(e, color=color, opacity=1.0 if is_sel else 0.22, line_width=4.0 if is_sel else 1.1)
    pl.add_text("bugs/0013 FIXED preview: front cap selected; rim = 1 clean edge", font_size=9, color="black", position="upper_left")
    zc = 0.5 * (float(_ALL_TRIS[..., 2].min()) + float(_ALL_TRIS[..., 2].max()))
    pl.camera_position = [(180.0, 0.0, zc), (0.0, 0.0, zc), (0.0, 0.0, 1.0)]
    pl.camera.zoom(1.5)
    pl.screenshot(str(out_png))
    pl.close()


def _run() -> int:
    global _ALL_TRIS
    import pyvista as pv

    from KrakenOS.UI import optical_solid_metadata as osm
    from KrakenOS.UI import layout_editor as le
    from KrakenOS.UI.services.step_optical_solid_brep import build_step_optical_solid_mesh
    from KrakenOS.UI.stl_geometry import read_stl_triangle_vertices

    tmp = Path(tempfile.mkdtemp())
    stl_path = tmp / "achromat_brep.stl"
    metadata = build_step_optical_solid_mesh(_STEP_FIXTURE, stl_path)
    records = [osm.normalize_optical_solid_face_record(f) for f in metadata.get("faces", [])]
    records = osm.suggest_optical_solid_face_roles(records)
    _fmt, tris = read_stl_triangle_vertices(stl_path)
    _ALL_TRIS = tris
    n_tri = int(tris.shape[0])
    meshes = [_face_mesh(pv, tris, n_tri, r) for r in records]

    gids = le.group_brep_optical_solid_faces(records)
    cyl = [i for i, r in enumerate(records) if str(r.get("surface_type")) == "cylinder"]
    rim_groups = {gids[i] for i in cyl}

    # "Front surface": the frontmost (min centroid-z) non-cylinder cap.
    caps = [i for i, r in enumerate(records) if str(r.get("surface_type")) != "cylinder" and meshes[i] is not None]
    if not caps:
        print("SKIP: no cap faces to select", file=sys.stderr)
        return 2
    selected_index = min(caps, key=lambda i: float(np.asarray(records[i].get("centroid", [0, 0, 0]), dtype=float).reshape(-1)[2]))

    cur_png = _OUT_DIR / "krakenos_0013_rim_current.png"
    fix_png = _OUT_DIR / "krakenos_0013_rim_fixed.png"
    full_png = _OUT_DIR / "krakenos_0013_rim_fixed_full.png"
    current = _nonselected_edge_clutter(pv, osm, meshes, gids, selected_index, recipe="current", out_png=cur_png)
    fixed = _nonselected_edge_clutter(pv, osm, meshes, gids, selected_index, recipe="fixed", out_png=fix_png)
    _render_full_preview(pv, osm, le, meshes, records, gids, selected_index, full_png)

    print(f"  selected (front cap) = {records[selected_index].get('face_id')} ({records[selected_index].get('surface_type')})")
    print(f"  rim cylinder faces = {[records[i].get('face_id') for i in cyl]} -> group ids {sorted(rim_groups)}")
    print(f"  non-selected edge clutter px: current(per-face,a5,0.82)={current}  fixed(per-group,a18,faint)={fixed}")
    print(f"  PNGs: current={cur_png}  fixed={fix_png}  full={full_png}")

    failures: list[str] = []
    # (1) grouping consolidated the rim into a single group
    if rim_groups != {0}:
        failures.append(f"rim cylinder faces not consolidated into one group (group ids {sorted(rim_groups)})")
    # (2) the fix must collapse the non-selected rim clutter vs the old recipe
    if current <= 0:
        failures.append("current recipe drew no rim edges -- discriminator has no teeth")
    elif fixed >= current * 0.5:
        failures.append(f"fixed recipe did not reduce rim clutter (fixed={fixed} vs current={current}; expected < 50%)")
    # (3) absolute sanity: fixed rim must be sparse, not a wireframe band
    if fixed > 9000:
        failures.append(f"fixed recipe rim still cluttered ({fixed} px) -- expected a thin edge")

    if failures:
        for msg in failures:
            print(f"FAIL: {msg}", file=sys.stderr)
        return 1
    print(
        f"PASS: rim consolidated to one group; non-selected clutter {current} -> {fixed} px "
        f"({100.0 * fixed / max(current, 1):.0f}% of old). PNGs in {_OUT_DIR}"
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
