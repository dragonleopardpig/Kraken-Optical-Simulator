"""Guard for bugs/0650 — the current 3D viewport exports to a DXF R12 vector drawing.

User: "The software can now output to STEP file, can you also add output to DXF or DWG
file? Output from the current viewport." DWG is a closed binary with no in-process
writer; DXF R12 ASCII is the universally-read dialect and converts to DWG in any CAD
package -- so the exporter writes R12 by hand (zero new dependencies), flattening the
scene orthographically into the CURRENT camera's view plane in TRUE millimetres, with
layers KRAKEN_RAYS / KRAKEN_AXES (dashed) / KRAKEN_BODIES (feature edges) /
KRAKEN_MEASURES / KRAKEN_OVERLAYS.

Checks (display-free):
  A  write_dxf_r12 round-trip: valid R12 skeleton (HEADER/TABLES/ENTITIES/EOF), the
     DASHED linetype defined, one LAYER row per layer with its colour+linetype, and
     POLYLINE/VERTEX/SEQEND entities matching the input (per-entity colour honoured,
     non-finite polylines dropped).
  B  project_points: camera view matrix + actor matrix compose in the right order and
     preserve TRUE view-plane distances (a 10 mm world segment maps to 10 DXF units).
  C  nearest_aci maps primaries onto their classic indices.
  D  the exporter is wired: the editor exposes export_3d_view_dxf and both the 3D
     window menu and the File menu offer it next to the STEP export.

  G  round 7: STEP companion edges by bounds containment; collinear-overlap merge.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0650_dxf_viewport_export
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.dxf_viewport_export import (
        nearest_aci,
        project_points,
        write_dxf_r12,
    )

    # ---------------------------------------------------------------- A: writer round-trip
    layers = {
        "KRAKEN_RAYS": {
            "ltype": "CONTINUOUS",
            "color": 3,
            "polylines": [
                {"points": np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 5.0]]), "color": 1},
                {"points": np.array([[np.nan, 0.0], [1.0, 1.0]]), "color": None},  # dropped
            ],
        },
        "KRAKEN_AXES": {
            "ltype": "DASHED",
            "color": 5,
            "polylines": [{"points": np.array([[-50.0, 0.0], [50.0, 0.0]]), "color": None}],
        },
        "__counts__": {"actors": 2},  # meta entries must be ignored
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "view.dxf"
        counts = write_dxf_r12(path, layers)
        text = path.read_text()
    a_problems = []
    for token in ("SECTION", "HEADER", "AC1009", "TABLES", "ENTITIES", "EOF"):
        if token not in text:
            a_problems.append(f"missing {token}")
    if "DASHED" not in text or text.count("\nLTYPE") < 2:
        a_problems.append("DASHED linetype not defined")
    if counts.get("KRAKEN_RAYS") != 1 or counts.get("KRAKEN_AXES") != 1:
        a_problems.append(f"entity counts wrong: {counts} (the NaN polyline must drop)")
    if text.count("POLYLINE") != 2 or text.count("SEQEND") != 2:
        a_problems.append("POLYLINE/SEQEND structure wrong")
    if text.count("VERTEX") != 5:
        a_problems.append(f"expected 5 VERTEX rows, got {text.count('VERTEX')}")
    if "__counts__" in text:
        a_problems.append("meta layer leaked into the file")
    # per-entity colour 62 on the ray polyline (1) and per-layer colours in the table
    if "\n62\n1" not in text:
        a_problems.append("per-entity ACI colour missing")
    if a_problems:
        ok = False
        notes.append(f"FAIL: A (bugs/0650): {a_problems}")
    else:
        notes.append("PASS: A: valid R12 skeleton, dashed axes, entities + colours round-trip")

    # ---------------------------------------------------------------- B: projection math
    # Camera view matrix: rotate world +Z to view -Z (identity view = looking down -Z),
    # here a simple translation + rotation about Z by 90 deg.
    c, s = 0.0, 1.0
    view = np.array(
        [[c, -s, 0, 1.0], [s, c, 0, 2.0], [0, 0, 1, 0.0], [0, 0, 0, 1.0]], dtype=float
    )
    actor = np.eye(4)
    actor[:3, 3] = (5.0, 0.0, 0.0)  # actor shifts +5 in world x
    pts = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    flat = project_points(pts, view, actor)
    # world points become (5,0,0) and (15,0,0); rotated 90deg -> (-y+1? ...): view @ p:
    expect0 = (view @ np.array([5.0, 0.0, 0.0, 1.0]))[:2]
    expect1 = (view @ np.array([15.0, 0.0, 0.0, 1.0]))[:2]
    b_problems = []
    if not (np.allclose(flat[0], expect0) and np.allclose(flat[1], expect1)):
        b_problems.append(f"compose order wrong: {flat} vs {expect0},{expect1}")
    if abs(float(np.linalg.norm(flat[1] - flat[0])) - 10.0) > 1e-9:
        b_problems.append("view-plane distances are not true scale")
    if b_problems:
        ok = False
        notes.append(f"FAIL: B (bugs/0650): {b_problems}")
    else:
        notes.append("PASS: B: actor->camera compose order right, true-scale mm preserved")

    # ---------------------------------------------------------------- C: colour mapping
    cases = {(1.0, 0.0, 0.0): 1, (0.0, 1.0, 0.0): 3, (0.0, 0.0, 1.0): 5, (1.0, 1.0, 0.0): 2}
    bad = {rgb: nearest_aci(rgb) for rgb, want in cases.items() if nearest_aci(rgb) != want}
    if bad:
        ok = False
        notes.append(f"FAIL: C (bugs/0650): primaries mis-mapped: {bad}")
    else:
        notes.append("PASS: C: primary colours map to their classic ACI indices")

    # ---------------------------------------------------------------- E: mesh line art
    # bugs/0650 rework (user: "the output lens only have horizontal lines, missing
    # those vertical and slanted lines of the housing"): meshes must export
    # view-direction SILHOUETTES + feature edges, never their stray tessellation LINE
    # cells; ray classification must consult BOTH registries + the many-segment
    # heuristic (73k polylines landed unclassified on the user's Pyrite90 file).
    import inspect as _insp2

    from KrakenOS.UI.services import dxf_viewport_export as dve

    e_problems = []
    outline_src = _insp2.getsource(dve.mesh_outline_strips)
    collect_src = _insp2.getsource(dve.collect_viewport_dxf_layers)
    if "vtkPolyDataSilhouette" not in outline_src or "SetDirectionToSpecifiedVector" not in outline_src:
        e_problems.append("no view-direction silhouette (slanted housing profiles missing)")
    if "vtkFeatureEdges" not in outline_src:
        e_problems.append("feature/boundary edges gone (rims and creases missing)")
    if "GetDirectionOfProjection" not in collect_src:
        e_problems.append("the collector does not hand the camera direction to the silhouette")
    if "if n_polys:" not in collect_src or "polydata_line_strips(polydata)\n        if not strips" not in collect_src:
        e_problems.append("mesh actors may export raw tessellation line cells again")
    if "_actor_ray_map" not in collect_src:
        e_problems.append("the direct key->ray registry is not consulted")
    if ">= 20" not in collect_src:
        e_problems.append("the many-segment ray heuristic for unregistered bundles is gone")
    # round 4 ("still have some open sides"): the STEP bodies' COMPANION edge actors
    # (pre-extracted CAD feature edges, lines-only, unregistered) carried the missing
    # crease work but were misfiled by the heuristic; and geometry living outside
    # renderer.GetActors() (assemblies / other prop classes) was invisible entirely.
    if "cad_step_actors" not in collect_src or "cad_body_keys" not in collect_src:
        e_problems.append("the CAD companion edge actors are not classified into BODIES")
    if "GetViewProps" not in collect_src:
        e_problems.append("the walk uses GetActors only (assembly/prop geometry invisible)")
    if "GetParts" not in collect_src:
        e_problems.append("assemblies are not descended")
    # round 6 (the user's freecad.png: right-side profile steps missing, asymmetric):
    if '"_row_actor_map"' not in collect_src:
        e_problems.append(
            "row-tracked companion actors (_row_actor_map, row->keys -- NOT _actor_row_map) "
            "are not classified into BODIES"
        )
    if "_actor_step_follow_map" in collect_src.replace(
        "# bugs/0650 round 5 dead end", ""
    ) and "cad_body_keys.update((getattr(inspector, \"_actor_step_follow_map\"" in collect_src:
        e_problems.append(
            "follow-map keys classified into BODIES again (they include ILLUMINATION "
            "RAYS -- the round-5 dead end)"
        )
    if "for tilt in (0.0, 0.01, -0.01)" not in outline_src:
        e_problems.append(
            "the silhouette perturbation union is gone -- tangency knife-edges on "
            "asymmetric tessellation drop one side's contour steps (freecad.png)"
        )
    if e_problems:
        ok = False
        notes.append(f"FAIL: E (bugs/0650): {e_problems}")
    else:
        notes.append(
            "PASS: E: meshes export silhouettes+feature edges (no tessellation soup); "
            "both ray registries + bundle heuristic classify"
        )

    # ---------------------------------------------------------------- F: one vector line
    # bugs/0650 (user: "many lines assembled of many short line segments ... a line
    # should be one vector line"): FeatureEdges/Silhouette emit per-edge 2-point cells;
    # the export must stitch shared-endpoint fragments and collapse collinear runs, and
    # the dashed AXES must come from the model records (one continuous line, dashes by
    # linetype), never from the dash-fragment actors.
    from KrakenOS.UI.services.dxf_viewport_export import (
        simplify_polyline_2d,
        stitch_strips_2d,
    )

    f_problems = []
    frags = [
        np.array([[0.0, 0.0], [1.0, 0.0]]),
        np.array([[2.0, 0.0], [1.0, 0.0]]),
        np.array([[2.0, 0.0], [3.0, 0.0]]),
    ]
    chains = stitch_strips_2d(frags)
    if len(chains) != 1:
        f_problems.append(f"3 collinear fragments stitched into {len(chains)} chains (want 1)")
    else:
        simple = simplify_polyline_2d(chains[0])
        if simple.shape[0] != 2:
            f_problems.append(f"collinear chain kept {simple.shape[0]} points (want 2 -- one vector)")
    bend = simplify_polyline_2d(np.array([[0.0, 0.0], [5.0, 0.0], [5.0, 5.0]]))
    if bend.shape[0] != 3:
        f_problems.append("a genuine bend was simplified away (ray kinks would vanish)")
    import inspect as _insp3

    from KrakenOS.UI.services import dxf_viewport_export as _dve

    collect_src2 = _insp3.getsource(_dve.collect_viewport_dxf_layers)
    if "_postprocess_layer_polylines" not in collect_src2:
        f_problems.append("layers are not post-processed (fragments would ship again)")
    if "_optical_axis_pick_records" not in collect_src2:
        f_problems.append("axes are not exported from the model records (dash stubs return)")
    # user round 3 ("boxes not closed, missing lines at one side, not symmetry"):
    from KrakenOS.UI.services.dxf_viewport_export import (
        _finite_runs,
        _postprocess_layer_polylines,
    )

    box = [
        {"points": np.array([[0.0, 0.0], [10.0, 0.0]]), "color": None},
        {"points": np.array([[10.0, 0.0], [10.0, 5.0]]), "color": None},
        {"points": np.array([[10.0, 5.0], [0.0, 5.0]]), "color": None},
        {"points": np.array([[0.0, 5.0], [0.0, 0.0]]), "color": None},
    ]
    closed = _postprocess_layer_polylines(box)
    if len(closed) != 1 or closed[0]["points"].shape[0] != 5 or not np.allclose(
        closed[0]["points"][0], closed[0]["points"][-1]
    ):
        f_problems.append("a 4-fragment box does not close into one chain with 4 corners")
    edge_join = stitch_strips_2d(
        [np.array([[0.0, 0.0], [10.0004, 0.0]]), np.array([[10.0011, 0.0], [20.0, 0.0]])],
        tol=1e-3,
    )
    if len(edge_join) != 1:
        f_problems.append("bin-edge endpoints fail to join (the asymmetric missing-side lottery)")
    runs = _finite_runs(np.array([[0.0, 0.0], [1.0, 0.0], [np.nan, 0.0], [3.0, 0.0], [4.0, 0.0]]))
    if len(runs) != 2:
        f_problems.append("a poisoned vertex still kills the whole chained line")
    dup = _postprocess_layer_polylines(
        [
            {"points": np.array([[0.0, 0.0], [10.0, 0.0]]), "color": None},
            {"points": np.array([[10.0, 0.0], [0.0, 0.0]]), "color": None},
        ]
    )
    if len(dup) != 1 or dup[0]["points"].shape[0] != 2:
        f_problems.append("a silhouette+feature duplicate edge does not collapse to one line")
    if f_problems:
        ok = False
        notes.append(f"FAIL: F (bugs/0650): {f_problems}")
    else:
        notes.append(
            "PASS: F: fragments stitch into single vector lines (boxes CLOSE, bin-edge "
            "joins hold, poisoned vertices split not kill, duplicates collapse)"
        )

    # ---------------------------------------------------------------- G: round 7
    # user (lens.png / camera.png): "many of them consist of black segment line joining
    # the green ... the camera, first line from the bottom seems broken". The STEP
    # bodies' companion edge actors have NO row (follow-only), so the round-6 row-tracked
    # keys never covered them and they still shipped as dark-green RAYS; and the same
    # housing edge arrived as up to nine overlapping collinear pieces (silhouette copy +
    # companion copy, each cut at every touching feature) -- endpoint stitching cannot
    # see overlap. Contract: lines-only actors INSIDE a STEP body's bounds are that
    # body's edge work (BODIES, layer colour), and overlapping collinear pieces merge
    # into ONE segment before the stitch.
    from KrakenOS.UI.services.dxf_viewport_export import merge_collinear_segments_2d

    g_problems = []
    collect_src3 = _insp3.getsource(_dve.collect_viewport_dxf_layers)
    if "_inside_step_body" not in collect_src3 or "step_bounds" not in collect_src3:
        g_problems.append("lines-only actors inside a STEP body are not filed as BODIES")
    # the camera's bottom edge exactly as the user's 20:19 export shipped it
    pieces = [
        ((54.57, -40.0), (58.05, -40.0)), ((63.05, -40.0), (58.05, -40.0)),
        ((59.40, -40.0), (58.05, -40.0)), ((61.05, -40.0), (59.40, -40.0)),
        ((59.40, -40.0), (62.69, -40.0)), ((61.21, -40.0), (62.70, -40.0)),
        ((62.70, -40.0), (62.42, -40.0)), ((82.05, -40.0), (63.05, -40.0)),
        ((63.05, -40.0), (82.05, -40.0)), ((53.57, -39.0), (54.57, -40.0)),
        ((82.05, -40.0), (83.05, -39.0)), ((53.57, -39.0), (53.57, -39.0)),
    ]
    merged = merge_collinear_segments_2d([np.array(p, dtype=float) for p in pieces])
    bottom = [
        m for m in merged if abs(m[0][1] + 40.0) < 1e-6 and abs(m[1][1] + 40.0) < 1e-6
    ]
    if len(bottom) != 1 or abs(bottom[0][0][0] - 54.57) > 1e-6 or abs(bottom[0][1][0] - 82.05) > 1e-6:
        g_problems.append(f"nine overlapping bottom-edge pieces did not merge into one span: {bottom}")
    if len(merged) != 3:
        g_problems.append(f"expected bottom + 2 chamfers after the merge, got {len(merged)}")
    whole = _postprocess_layer_polylines([{"points": np.array(p, dtype=float), "color": None} for p in pieces])
    if len(whole) != 1 or whole[0]["points"].shape[0] != 4:
        g_problems.append(
            f"the bottom edge + chamfers did not become ONE 4-point polyline "
            f"(got {len(whole)} polylines)"
        )
    # distinct parallel lines must NOT merge; a genuine gap must stay a gap
    apart = merge_collinear_segments_2d(
        [np.array([[0.0, 0.0], [10.0, 0.0]]), np.array([[0.0, 2.0], [10.0, 2.0]]),
         np.array([[20.0, 0.0], [30.0, 0.0]])]
    )
    if len(apart) != 3:
        g_problems.append(f"parallel/gapped segments were merged ({len(apart)} != 3)")
    if g_problems:
        ok = False
        notes.append(f"FAIL: G (bugs/0650 round 7): {g_problems}")
    else:
        notes.append(
            "PASS: G: STEP companion edges file as BODIES by bounds; overlapping collinear "
            "pieces merge into one vector line (camera bottom edge = one polyline)"
        )

    # ---------------------------------------------------------------- D: wiring
    import inspect as _inspect

    d_problems = []
    try:
        from KrakenOS.UI.services import layout_import_export as ie

        found = any(
            "export_3d_view_dxf" in vars(cls)
            for cls in vars(ie).values()
            if isinstance(cls, type)
        )
        if not found:
            d_problems.append("editor has no export_3d_view_dxf")
    except Exception as exc:
        d_problems.append(f"editor probe failed: {exc}")
    try:
        from KrakenOS.UI.panels import main_window as mw

        if "export_3d_view_dxf" not in _inspect.getsource(mw):
            d_problems.append("File menu does not offer the DXF export")
    except Exception as exc:
        d_problems.append(f"main_window probe failed: {exc}")
    try:
        from KrakenOS.UI.panels import open3d_top_controls as tc

        if "DXF" not in _inspect.getsource(tc):
            d_problems.append("3D window menu does not offer the DXF export")
    except Exception as exc:
        d_problems.append(f"top-controls probe failed: {exc}")
    if d_problems:
        ok = False
        notes.append(f"FAIL: D (bugs/0650): {d_problems}")
    else:
        notes.append("PASS: D: editor method + File menu + 3D window menu all wired")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("DXF-viewport-export validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
