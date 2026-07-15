#!/usr/bin/env python3
"""Display-free guard for the imported-LED STEP hover fix
(bugs/0317: "mouse hover imported LED STEP: is not intuitive, the highlight is
not the nearest edge, and only a few can be selected as highlight").

Root cause
----------
A vendor LED display body is an ANALYTIC STEP mesh: every triangle carries a
per-cell ``kraken_step_selection_face_index`` (the real vendor LED has 60138
cells over 714 analytic faces, 100% indexed). But the hover PICK resolved a
cell to a highlight only when the cell's face index mapped to a METADATA
record, and those records come from planar CLUSTERING capped at 160 faces,
built on a SEPARATE re-triangulated STL. On the real LED only 165 of 714 faces
end up referenced -> 12870/60138 cells (21.4%) could highlight; ~4/5 of the body
returned nothing ("only a few can be selected as highlight").

Fix
---
1. ``raw_face_feature_for_display_cell`` -- an all-selectable fallback that
   highlights the picked cell's OWN face group straight from the per-cell face
   index, needing NO metadata record. Coverage 21.4% -> 100% on the real LED.
2. ``nearest_display_edge`` + ``_edge_refined_feature`` -- when the cursor is
   within a pixel tolerance of a projected outline segment, refine the
   whole-face highlight to that single NEAREST edge (with a per-edge dedup tag),
   so a user aligning an edge to the optical axis lights up the edge they mean.

What it checks
--------------
  A. All-selectable: on a synthetic analytic mesh whose face 0 has NO metadata
     record, ``face_pick_from_display_cell`` (OLD) returns None for face 0 while
     ``raw_face_feature_for_display_cell`` (NEW) returns a finite feature;
     face 1 (which HAS a record) stays selectable both ways.
  B. Raw feature shape: outline is a real boundary polyline, centroid/normal
     finite, normal unit-length and axis-aligned for a planar face.
  C. Nearest edge (pure): ``nearest_display_edge`` returns the segment nearest a
     fake projected cursor, None beyond tolerance, None when projection fails,
     and a stable ordinal; ``line_segment_pairs`` round-trips a multi-cell line.
  D. Edge refinement: ``_edge_refined_feature`` keeps the whole-face feature far
     from edges and returns a single-edge feature + suffixed ``face_id`` near
     one, preserving the ``(point[3], overlay, normal[3])`` feature contract.
  E. Wiring (source): ``step_feature_pick_for_display_xy`` funnels through
     ``raw_face_feature_for_display_cell`` and ``_edge_refined_feature``.
  F. Real LED (only when the analytic cache is present -- it is gitignored, so
     this is a bonus on the dev box): raw-fallback covers ~100% of sampled cells
     while the metadata records cover far less.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_step_hover_all_selectable

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import glob
import inspect
import types

import numpy as np

try:
    import pyvista as pv
except Exception:  # pragma: no cover
    pv = None


def _synthetic_two_face_mesh():
    """Two coplanar-square faces (z=0 and z=10), 2 triangles each, face index
    [0,0,1,1] -- a minimal analytic body standing in for the LED's per-cell
    ``kraken_step_selection_face_index``."""
    quad0 = np.array([[0, 0, 0], [4, 0, 0], [4, 4, 0], [0, 4, 0]], dtype=float)
    quad1 = np.array([[0, 0, 10], [4, 0, 10], [4, 4, 10], [0, 4, 10]], dtype=float)
    tris = np.array(
        [
            [quad0[0], quad0[1], quad0[2]],
            [quad0[0], quad0[2], quad0[3]],
            [quad1[0], quad1[1], quad1[2]],
            [quad1[0], quad1[2], quad1[3]],
        ],
        dtype=float,
    )
    count = int(tris.shape[0])
    points = tris.reshape((-1, 3))
    faces = np.empty((count, 4), dtype=np.int64)
    faces[:, 0] = 3
    faces[:, 1] = np.arange(0, 3 * count, 3, dtype=np.int64)
    faces[:, 2] = faces[:, 1] + 1
    faces[:, 3] = faces[:, 1] + 2
    mesh = pv.PolyData(points, faces.reshape(-1))
    face_index = np.array([0, 0, 1, 1], dtype=np.int32)
    mesh.cell_data["kraken_step_selection_face_index"] = face_index
    mesh.cell_data["kraken_step_face_index"] = face_index
    mesh.field_data["kraken_step_analytic"] = np.asarray([1], dtype=np.int8)
    return mesh


def _fake_projector():
    """Identity XY projection (world (x,y,z) -> display (x,y))."""
    return lambda point: (float(np.asarray(point, dtype=float).reshape(-1)[0]),
                          float(np.asarray(point, dtype=float).reshape(-1)[1]))


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_face_index_edges import (
        face_pick_from_display_cell,
        line_segment_pairs,
        nearest_display_edge,
        raw_face_feature_for_display_cell,
        single_edge_polydata,
    )
    from KrakenOS.UI.services import open3d_round_lens_pick as pick_mod

    failures: list[str] = []
    if pv is None:
        return False, ["FAIL: PyVista unavailable -- cannot exercise the hover fix"]

    mesh = _synthetic_two_face_mesh()

    # A) All-selectable: face 0 has no metadata record; face 1 does.
    editor = types.SimpleNamespace(
        _transformed_imported_step_mesh_for_label=lambda _label: mesh
    )
    face1_record = {
        "triangle_indices": [2, 3],
        "face_id": "F001",
        "normal_world": (0.0, 0.0, 1.0),
        "centroid_world": (2.0, 2.0, 10.0),
    }
    faces = [face1_record]
    old_face0 = face_pick_from_display_cell(editor, "led", faces, 0, pick_point=None)
    old_face1 = face_pick_from_display_cell(editor, "led", faces, 2, pick_point=None)
    new_face0 = raw_face_feature_for_display_cell(mesh, 0)
    new_face1 = raw_face_feature_for_display_cell(mesh, 2)
    if old_face0 is not None:
        failures.append("FAIL(A): OLD path unexpectedly resolved face 0 (no record) -- test setup wrong")
    if old_face1 is None:
        failures.append("FAIL(A): OLD path must still resolve face 1 (it has a record)")
    if new_face0 is None:
        failures.append("FAIL(A): raw-fallback must highlight face 0 even with NO metadata record (all-selectable)")
    if new_face1 is None:
        failures.append("FAIL(A): raw-fallback must highlight face 1")

    # B) Raw feature shape.
    if new_face0 is not None:
        face_index, outline, centroid, normal = new_face0
        if int(face_index) != 0:
            failures.append(f"FAIL(B): face 0 raw feature reports index {face_index}, expected 0")
        if outline is None or int(getattr(outline, "n_points", 0)) <= 0:
            failures.append("FAIL(B): raw feature must carry a boundary outline polyline")
        else:
            pairs0 = line_segment_pairs(outline)
            if len(pairs0) < 4:
                failures.append(f"FAIL(B): face-0 square outline should have >=4 edges, got {len(pairs0)}")
        centroid = np.asarray(centroid, dtype=float)
        normal = np.asarray(normal, dtype=float)
        if not (np.all(np.isfinite(centroid)) and np.all(np.isfinite(normal))):
            failures.append("FAIL(B): raw feature centroid/normal must be finite")
        elif not np.allclose(centroid, (2.0, 2.0, 0.0), atol=1e-6):
            failures.append(f"FAIL(B): face-0 centroid should be (2,2,0), got {tuple(centroid)}")
        elif abs(abs(float(normal[2])) - 1.0) > 1e-6:
            failures.append(f"FAIL(B): face-0 normal should be +/-Z unit, got {tuple(normal)}")

    # C) Nearest edge (pure) + line_segment_pairs round-trip.
    project = _fake_projector()
    if new_face0 is not None:
        _fi, outline0, _c, _n = new_face0
        pts0 = np.asarray(outline0.points, dtype=float).reshape((-1, 3))
        pairs0 = line_segment_pairs(outline0)
        # Cursor just outside the bottom edge (y=0) near its midpoint (2,0).
        hit = nearest_display_edge(pts0, pairs0, (2.0, 0.3), project, tolerance_px=14.0)
        if hit is None:
            failures.append("FAIL(C): nearest_display_edge should catch the bottom edge near (2,0.3)")
        else:
            ordinal, i0, i1, midpoint, distance = hit
            if not np.allclose(midpoint[:2], (2.0, 0.0), atol=1e-6):
                failures.append(f"FAIL(C): nearest edge midpoint should be ~(2,0), got {midpoint}")
            if distance > 14.0:
                failures.append(f"FAIL(C): reported distance {distance} exceeds tolerance")
            if int(ordinal) < 0:
                failures.append("FAIL(C): edge ordinal must be a stable non-negative index")
        # Cursor at the face centre with a tight tolerance -> no edge.
        if nearest_display_edge(pts0, pairs0, (2.0, 2.0), project, tolerance_px=0.5) is not None:
            failures.append("FAIL(C): centre cursor within a tight tolerance must match no edge")
        # Projection failure -> None.
        if nearest_display_edge(pts0, pairs0, (2.0, 0.3), lambda _p: None, tolerance_px=14.0) is not None:
            failures.append("FAIL(C): an all-None projector must yield no edge match")
    se = single_edge_polydata((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    if line_segment_pairs(se) != [(0, 1)]:
        failures.append(f"FAIL(C): single_edge_polydata should round-trip to [(0,1)], got {line_segment_pairs(se)}")

    # D) Edge refinement returns whole-face far, single-edge near.
    fake_inspector = types.SimpleNamespace(
        _world_to_display_2d=lambda p: np.asarray(project(p), dtype=float),
        _hover_overlay_for_feature=Kraken3DInspector._hover_overlay_for_feature,
    )
    if new_face0 is not None:
        _fi, outline0, centroid0, normal0 = new_face0
        base_feature = (
            np.asarray(centroid0, dtype=float).reshape(3),
            Kraken3DInspector._hover_overlay_for_feature(centroid0, outline0),
            np.asarray(normal0, dtype=float).reshape(3),
        )
        # Far from any edge -> unchanged whole-face feature + face_id.
        far_feature, far_id = pick_mod._edge_refined_feature(
            fake_inspector, base_feature, "F000", outline0, (2.0, 2.0), tolerance_px=0.5
        )
        if far_id != "F000" or far_feature is not base_feature:
            failures.append("FAIL(D): far-from-edge refinement must return the whole-face feature unchanged")
        # Near the bottom edge -> single-edge feature + suffixed face_id.
        near_feature, near_id = pick_mod._edge_refined_feature(
            fake_inspector, base_feature, "F000", outline0, (2.0, 0.3), tolerance_px=14.0
        )
        if not (isinstance(near_id, str) and near_id.startswith("F000") and "e" in near_id[4:]):
            failures.append(f"FAIL(D): near-edge face_id must suffix the base with an edge tag, got {near_id!r}")
        try:
            near_point = np.asarray(near_feature[0], dtype=float).reshape(-1)[:3]
            near_normal = np.asarray(near_feature[2], dtype=float).reshape(-1)[:3]
        except Exception:
            near_point = near_normal = np.asarray([], dtype=float)
        if near_point.size < 3 or not np.allclose(near_point[:2], (2.0, 0.0), atol=1e-6):
            failures.append(f"FAIL(D): near-edge feature point should be the edge midpoint ~(2,0), got {near_point}")
        if near_normal.size < 3 or abs(abs(float(near_normal[2])) - 1.0) > 1e-6:
            failures.append("FAIL(D): near-edge feature must preserve the face normal (feature[2])")
        if near_feature[1] is None or int(getattr(near_feature[1], "n_points", 0)) <= 0:
            failures.append("FAIL(D): near-edge feature must carry a highlight overlay (feature[1])")

    # E) Source wiring.
    pick_src = inspect.getsource(pick_mod.step_feature_pick_for_display_xy)
    if "raw_face_feature_for_display_cell" not in pick_src:
        failures.append("FAIL(E): step_feature_pick_for_display_xy must call the raw-face all-selectable fallback")
    if "_edge_refined_feature" not in pick_src:
        failures.append("FAIL(E): step_feature_pick_for_display_xy must apply the nearest-edge refinement")

    # F) Real LED (bonus -- cache is gitignored, skip cleanly when absent).
    caches = sorted(glob.glob("attachment/cad_cache/OPT-CO90*analytic*.vtp"))
    if caches:
        try:
            led = pv.read(caches[-1])
            surf = pv.wrap(led)
            n_cells = int(surf.n_cells)
            sample = range(0, n_cells, max(1, n_cells // 400))
            covered = sum(1 for cid in sample if raw_face_feature_for_display_cell(led, cid) is not None)
            tried = sum(1 for _ in sample)
            if tried and covered / tried < 0.95:
                failures.append(
                    f"FAIL(F): raw-fallback should cover ~100% of the real LED, got {covered}/{tried}")
        except Exception as exc:
            failures.append(f"FAIL(F): real-LED coverage check raised {type(exc).__name__}: {exc}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] imported-LED STEP hover: all-selectable + nearest-edge")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] every LED STEP patch highlights (raw-face fallback) and the "
          "nearest edge refines the hover for optical-axis alignment")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
