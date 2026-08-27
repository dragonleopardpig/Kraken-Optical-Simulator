"""Guard for bugs/0652 -- right-click a component -> one DXF R12 sheet with all six
orthographic views (third-angle layout: TOP over FRONT, BOTTOM under, LEFT/RIGHT
beside, BACK past RIGHT), true millimetres, view captions as TEXT entities.

The user's ask (2026-08-27, after the 0650 viewport export settled): "Can we add a
right click to components and export it as a DXF with view in all 6 faces?" The sheet
reuses the whole 0650 pipeline -- silhouettes + feature edges per axis direction, the
round-8 decompose/merge/stitch post-process -- scoped to ONE component's actors
(step label or row group, companions by the round-7 containment rule).

Checks (all display-free; the VTK stage uses pure filters, no render window):
  A  BASES     -- six views, unique names, every frame right-handed toward the viewer
                  (right x up == -direction), adjacent views sharing their world axis.
  B  PLACEMENT -- third-angle sheet offsets on asymmetric synthetic bounds: TOP stays
                  x-aligned ABOVE FRONT, BOTTOM below, LEFT|FRONT|RIGHT|BACK run left
                  to right with the gap, side views keep raw y (projectional alignment).
  C  GEOMETRY  -- a real vtkCubeSource 10x20x30 through the actual collector with a
                  stub inspector: 6 captioned views; per-view silhouette extents match
                  the cube's faces (FRONT 10x30, RIGHT 20x30, TOP 10x20).
  D  WRITER    -- TEXT entities round-trip through write_dxf_r12 (centre-aligned,
                  height, caption strings on KRAKEN_LABELS).
  E  WIRING    -- the verb sits on BOTH right-click branches (STEP body and element
                  row) in open3d_face_assignment, and the editor dialog method exists.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0652_component_six_view_dxf
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.dxf_viewport_export import (
        SIX_VIEW_BASES,
        collect_component_six_view_layers,
        mesh_outline_strips,
        place_six_views,
        write_dxf_r12,
    )

    # ---------------------------------------------------------------- A: view bases
    a_problems = []
    names = [name for name, *_ in SIX_VIEW_BASES]
    if sorted(names) != ["BACK", "BOTTOM", "FRONT", "LEFT", "RIGHT", "TOP"]:
        a_problems.append(f"view set wrong: {names}")
    for name, vdir, right, up in SIX_VIEW_BASES:
        d, r, u = (np.asarray(v, dtype=float) for v in (vdir, right, up))
        if not np.allclose(np.cross(r, u), -d):
            a_problems.append(f"{name}: right x up != -direction (mirror-image view)")
        if abs(np.dot(r, u)) > 1e-12 or abs(np.linalg.norm(r) - 1) > 1e-12:
            a_problems.append(f"{name}: frame not orthonormal")
    # projectional alignment guarantees: all side views share up=+Z, top/bottom share
    # FRONT's right=+X -- that is what lets the sheet keep raw coordinates aligned.
    by_name = {name: (np.array(r), np.array(u)) for name, _, r, u in SIX_VIEW_BASES}
    for side in ("FRONT", "BACK", "LEFT", "RIGHT"):
        if not np.allclose(by_name[side][1], [0.0, 0.0, 1.0]):
            a_problems.append(f"{side}: up is not world +Z")
    for flat in ("TOP", "BOTTOM"):
        if not np.allclose(by_name[flat][0], [1.0, 0.0, 0.0]):
            a_problems.append(f"{flat}: right is not world +X")
    if a_problems:
        ok = False
        notes.append(f"FAIL: A (bugs/0652): {a_problems}")
    else:
        notes.append("PASS: A: six right-handed view frames, adjacent views share axes")

    # ---------------------------------------------------------------- B: placement
    b_problems = []
    bounds = {
        "FRONT": (-5.0, 5.0, -15.0, 15.0),
        "BACK": (-5.0, 5.0, -15.0, 15.0),
        "LEFT": (-10.0, 10.0, -15.0, 15.0),
        "RIGHT": (-10.0, 10.0, -15.0, 15.0),
        "TOP": (-5.0, 5.0, -10.0, 10.0),
        "BOTTOM": (-5.0, 5.0, -10.0, 10.0),
    }
    gap = 20.0
    off = place_six_views(bounds, gap)
    if off["FRONT"] != (0.0, 0.0):
        b_problems.append("FRONT is not the sheet origin")
    if off["TOP"][0] != 0.0 or off["BOTTOM"][0] != 0.0:
        b_problems.append("TOP/BOTTOM lost their x alignment with FRONT")
    if abs((bounds["TOP"][2] + off["TOP"][1]) - (bounds["FRONT"][3] + gap)) > 1e-9:
        b_problems.append("TOP is not exactly one gap above FRONT")
    if abs((bounds["BOTTOM"][3] + off["BOTTOM"][1]) - (bounds["FRONT"][2] - gap)) > 1e-9:
        b_problems.append("BOTTOM is not exactly one gap below FRONT")
    if off["LEFT"][1] != 0.0 or off["RIGHT"][1] != 0.0 or off["BACK"][1] != 0.0:
        b_problems.append("side views lost their raw-y projectional alignment")
    if abs((bounds["LEFT"][1] + off["LEFT"][0]) - (bounds["FRONT"][0] - gap)) > 1e-9:
        b_problems.append("LEFT is not one gap left of FRONT")
    if abs((bounds["RIGHT"][0] + off["RIGHT"][0]) - (bounds["FRONT"][1] + gap)) > 1e-9:
        b_problems.append("RIGHT is not one gap right of FRONT")
    if (bounds["BACK"][0] + off["BACK"][0]) - (bounds["RIGHT"][1] + off["RIGHT"][0]) - gap > 1e-9 or (
        bounds["BACK"][0] + off["BACK"][0]
    ) < (bounds["RIGHT"][1] + off["RIGHT"][0]):
        b_problems.append("BACK does not follow RIGHT with the gap")
    if b_problems:
        ok = False
        notes.append(f"FAIL: B (bugs/0652): {b_problems}")
    else:
        notes.append("PASS: B: third-angle sheet -- aligned columns/rows, gaps exact")

    # ---------------------------------------------------------------- C: geometry
    c_problems = []
    try:
        import vtk

        cube = vtk.vtkCubeSource()
        cube.SetXLength(10.0)
        cube.SetYLength(20.0)
        cube.SetZLength(30.0)
        cube.Update()
        polydata = cube.GetOutput()
        # per-view silhouette extents straight from the pipeline stage
        want = {"FRONT": (10.0, 30.0), "RIGHT": (20.0, 30.0), "TOP": (10.0, 20.0)}
        for name, vdir, right, up in SIX_VIEW_BASES:
            if name not in want:
                continue
            strips = mesh_outline_strips(polydata, vdir, None)
            if not strips:
                c_problems.append(f"{name}: no outline from the cube")
                continue
            pts = np.vstack(strips)
            flat = np.stack([pts @ np.asarray(right, float), pts @ np.asarray(up, float)], axis=1)
            w = float(flat[:, 0].max() - flat[:, 0].min())
            h = float(flat[:, 1].max() - flat[:, 1].min())
            if abs(w - want[name][0]) > 0.05 or abs(h - want[name][1]) > 0.05:
                c_problems.append(f"{name}: extent {w:.2f}x{h:.2f}, want {want[name]}")

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        renderer = vtk.vtkRenderer()
        renderer.AddActor(actor)
        stub = SimpleNamespace(
            _renderer=renderer,
            _actor_key=lambda a: "cube1",
            _actor_step_map={"cube1": "camera"},
            _actor_row_map={},
            _row_actor_map={},
            _actor_ray_map={},
            _ray_actor_map={},
            _actor_optical_axis_map={},
        )
        layers = collect_component_six_view_layers(stub, step_label="camera")
        captions = sorted(t["text"] for t in layers["KRAKEN_LABELS"]["texts"])
        if captions != ["BACK", "BOTTOM", "FRONT", "LEFT", "RIGHT", "TOP"]:
            c_problems.append(f"captions wrong: {captions}")
        if not layers["KRAKEN_BODIES"]["polylines"]:
            c_problems.append("no body line work collected")
        allp = np.vstack([np.asarray(q["points"]) for q in layers["KRAKEN_BODIES"]["polylines"]])
        sheet_w = float(allp[:, 0].max() - allp[:, 0].min())
        if sheet_w < 10.0 + 20.0 + 20.0 + 10.0:  # front+left+right+back widths, no gaps yet
            c_problems.append(f"sheet width {sheet_w:.1f} too small -- views overlap")
    except Exception as exc:
        c_problems.append(f"raised {type(exc).__name__}: {exc}")
    if c_problems:
        ok = False
        notes.append(f"FAIL: C (bugs/0652): {c_problems}")
    else:
        notes.append("PASS: C: a real cube collects into 6 captioned, correctly sized views")

    # ---------------------------------------------------------------- D: TEXT writer
    d_problems = []
    layers = {
        "KRAKEN_LABELS": {
            "ltype": "CONTINUOUS",
            "color": 3,
            "polylines": [],
            "texts": [{"pos": (12.0, -7.5), "height": 3.0, "text": "FRONT"}],
        }
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sheet.dxf"
        counts = write_dxf_r12(path, layers)
        text = path.read_text()
    if "\nTEXT" not in text or "\nFRONT" not in text:
        d_problems.append("TEXT entity / caption string missing")
    if "\n72\n1" not in text or "\n11\n12.0000" not in text:
        d_problems.append("centre alignment (72=1 + second alignment point) missing")
    if counts.get("KRAKEN_LABELS") != 1:
        d_problems.append(f"caption not counted: {counts}")
    if d_problems:
        ok = False
        notes.append(f"FAIL: D (bugs/0652): {d_problems}")
    else:
        notes.append("PASS: D: view captions write as centre-aligned R12 TEXT")

    # ---------------------------------------------------------------- E: wiring
    import inspect as _inspect

    e_problems = []
    try:
        from KrakenOS.UI.services import open3d_face_assignment as fa

        src = _inspect.getsource(fa)
        if src.count("Export Component DXF (6 Views)...") < 2:
            e_problems.append(
                "the verb is not on BOTH right-click branches (STEP body + element row)"
            )
        if "export_component_six_view_dxf(" not in src:
            e_problems.append("the menu does not call the editor export")
    except Exception as exc:
        e_problems.append(f"face-assignment probe failed: {exc}")
    try:
        from KrakenOS.UI.services import layout_import_export as ie

        found = any(
            "export_component_six_view_dxf" in vars(cls)
            for cls in vars(ie).values()
            if isinstance(cls, type)
        )
        if not found:
            e_problems.append("editor has no export_component_six_view_dxf")
        else:
            method_src = _inspect.getsource(ie.LayoutImportExportMixin.export_component_six_view_dxf)
            if "_lens_row_group_for_row" not in method_src:
                e_problems.append("a lens row does not export its whole row group")
    except Exception as exc:
        e_problems.append(f"editor probe failed: {exc}")
    if e_problems:
        ok = False
        notes.append(f"FAIL: E (bugs/0652): {e_problems}")
    else:
        notes.append("PASS: E: right-click verb on STEP and row branches; editor dialog wired")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Component six-view DXF validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
