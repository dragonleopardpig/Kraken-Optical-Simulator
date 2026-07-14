"""End-to-end STEP export for the AZ85 folded periscope, headless.

Mirrors export_3d_step()'s imported-CAD branch:
  system -> _collect_native_step_export_shapes -> _step_export_ray_polylines
         -> _write_step_with_cad_shapes_and_rays(output.step)

Then reads the written STEP back and reports every top-level solid/shell with its
world bbox, so we can eyeball that:
  * the two BK7 RA prisms land on the folded legs (bugs/0300 fix),
  * the Object plane disc is present (requirement 4),
  * nothing throws when analytic surfaces + CAD overlays + prisms + rays coexist.

Run: .devenv/state/venv/bin/python bugs/diag_step_export_end_to_end.py
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.surface_table_model import SurfaceRow
from KrakenOS.UI.services.cad_step_export import _write_step_with_cad_shapes_and_rays
from KrakenOS.UI.validate_open3d_five_penta_initial_visual import _load_saved_layout

LAYOUT = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
OUT = Path("attachment/_diag_az85_export.step")


def _solid_bboxes(path: Path):
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.TopAbs import TopAbs_SOLID, TopAbs_SHELL
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib

    reader = STEPControl_Reader()
    reader.ReadFile(str(path))
    reader.TransferRoots()
    shape = reader.OneShape()
    out = []
    # Count SOLIDS, plus SHELLS that are not part of a solid (the prism shells
    # and analytic faces are free shells, not closed solids).
    from OCC.Core.TopTools import TopTools_IndexedMapOfShape
    from OCC.Core.TopExp import topexp

    solid_shells = TopTools_IndexedMapOfShape()
    topexp.MapShapes(shape, TopAbs_SHELL, solid_shells)
    # shells inside solids:
    inner = TopTools_IndexedMapOfShape()
    exp_solid = TopExp_Explorer(shape, TopAbs_SOLID)
    while exp_solid.More():
        sub = TopExp_Explorer(exp_solid.Current(), TopAbs_SHELL)
        while sub.More():
            inner.Add(sub.Current())
            sub.Next()
        exp_solid.Next()

    def _bbox(sub):
        box = Bnd_Box()
        brepbndlib.Add(sub, box)
        xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
        lo = np.array([xmin, ymin, zmin]); hi = np.array([xmax, ymax, zmax])
        return 0.5 * (lo + hi), hi - lo

    exp = TopExp_Explorer(shape, TopAbs_SOLID)
    while exp.More():
        try:
            c, s = _bbox(exp.Current()); out.append(("solid", c, s))
        except Exception:
            pass
        exp.Next()
    for i in range(1, solid_shells.Size() + 1):
        sh = solid_shells.FindKey(i)
        if inner.Contains(sh):
            continue
        try:
            c, s = _bbox(sh); out.append(("shell", c, s))
        except Exception:
            pass
    return out


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    _load_saved_layout(app, LAYOUT)
    system = app.build_system()

    print(f"_has_imported_step_cad = {app._has_imported_step_cad()}")
    cad_shapes = app._collect_native_step_export_shapes(system)
    print(f"cad_shapes = {len(cad_shapes)}:")
    for label, _shape in cad_shapes:
        print(f"    {label}")
    ray_polylines = app._step_export_ray_polylines(system)
    print(f"ray_polylines (available) = {len(ray_polylines)} -- writing with rays DISABLED for a clean geometry read-back")
    ray_polylines = []  # geometry-only read-back; ray cylinders flood the solid list

    rows_snapshot = [SurfaceRow(**asdict(row)) for row in app.rows]
    counts = _write_step_with_cad_shapes_and_rays(
        system, rows_snapshot, cad_shapes, ray_polylines, OUT,
    )
    print(f"writer counts = {counts}")
    print(f"written: {OUT}  exists={OUT.exists()}  bytes={OUT.stat().st_size if OUT.exists() else 0}")

    boxes = _solid_bboxes(OUT)
    print(f"\nread-back geometry bodies = {len(boxes)} (solids={sum(k=='solid' for k,_,_ in boxes)}, free-shells={sum(k=='shell' for k,_,_ in boxes)})")
    near_object = False
    near_image = False
    print("  structural bodies (max bbox dim >= 5 mm; tiny vendor-camera facets suppressed):")
    for kind, center, size in sorted(boxes, key=lambda b: b[1][0]):
        if np.linalg.norm(center) < 8:
            near_object = True
        if abs(center[0] - 304.19) < 8:
            near_image = True
        if float(np.max(size)) < 5.0:
            continue
        print(f"    {kind:5s} center={np.round(center, 2).tolist()} size={np.round(size, 2).tolist()}")
    print(f"\nObject-plane body near origin present = {near_object}")
    print(f"folded-Image body near x=304.19 present = {near_image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
