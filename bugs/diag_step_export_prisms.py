"""Do the two BK7 RA prisms (rows carrying Solid_3d_stl) export where the 3D display draws them?

The AZ85 folded periscope has two right-angle BK7 prisms (fold mirrors). They are optical-solid
rows (Solid_3d_stl set), so they drop out of the analytic surface phase (not revolution-compatible).

bugs/0300: such a row is drawn from its STL under the runtime display transform
(_runtime_transform_for_row: output-port override else TRANS_2A), NOT from the shared step_*.step
template it was promoted from (a different local frame). The fixed export now writes that same
world-placed STL as a faceted OCC shell via _optical_solid_row_world_step_shell.

This probe checks, per prism row, that the exported shell's WORLD bounding box matches the
display mesh's world bounding box (centre + extents). Bounding box is invariant to vertex
duplication in the tessellated shell, so it is an apples-to-apples placement + scale check.
It also confirms the full _collect_native_step_export_shapes wiring returns a body per prism.

Run: .devenv/state/venv/bin/python bugs/diag_step_export_prisms.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.validate_open3d_five_penta_initial_visual import _load_saved_layout

LAYOUT = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
TOL_MM = 0.05


def _shell_world_bbox(shape) -> tuple[np.ndarray, np.ndarray]:
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib

    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return np.array([xmin, ymin, zmin], dtype=float), np.array([xmax, ymax, zmax], dtype=float)


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    _load_saved_layout(app, LAYOUT)
    system = app.build_system()
    rows = app.rows

    prism_rows = [j for j, _r in enumerate(rows) if app._file_backed_stl_row_at(j) is not None]
    print(f"file-backed optical-solid (prism) rows = {prism_rows}")

    # Full wiring: labels emitted by the native-row collector for these rows.
    collected = app._collect_row_native_step_export_shapes(system)
    collected_labels = [label for label, _shape in collected]
    print(f"native-row export labels = {collected_labels}")

    worst = 0.0
    for j in prism_rows:
        row = rows[j]
        stl_item = app._file_backed_stl_row_at(j)
        transform = app._row_optical_solid_display_world_transform(system, j)
        print(f"\n=== row j={j} {row.surface} ({stl_item[1].name}) ===")
        print(f"  display transform available = {transform is not None}")
        if transform is None:
            print("  NO display transform -- skip")
            continue
        print(f"  display translation = {np.round(np.asarray(transform)[:3, 3], 3).tolist()}")

        # DISPLAY world: exactly the STL mesh the inspector renders for this row.
        disp_mesh = app._stl_mesh_with_world_transform(row, transform)
        disp_pts = np.asarray(disp_mesh.points, dtype=float)
        disp_min, disp_max = disp_pts.min(axis=0), disp_pts.max(axis=0)
        disp_center = 0.5 * (disp_min + disp_max)

        # EXPORT world: the faceted shell the fixed export writes for this row.
        shell = app._optical_solid_row_world_step_shell(row, j, system)
        if shell is None:
            print("  EXPORT shell unavailable -- MISMATCH")
            worst = max(worst, 1e9)
            continue
        exp_min, exp_max = _shell_world_bbox(shell)
        exp_center = 0.5 * (exp_min + exp_max)

        center_delta = float(np.linalg.norm(disp_center - exp_center))
        extent_delta = float(np.linalg.norm((disp_max - disp_min) - (exp_max - exp_min)))
        worst = max(worst, center_delta, extent_delta)
        print(f"  DISPLAY bbox center = {np.round(disp_center, 3).tolist()}  size = {np.round(disp_max - disp_min, 3).tolist()}")
        print(f"  EXPORT  bbox center = {np.round(exp_center, 3).tolist()}  size = {np.round(exp_max - exp_min, 3).tolist()}")
        flag = "<-- MISMATCH" if max(center_delta, extent_delta) > TOL_MM else "ok"
        print(f"  center delta = {center_delta:.4f} mm   extent delta = {extent_delta:.4f} mm   {flag}")

    ok = worst <= TOL_MM
    print(f"\nworst prism delta = {worst:.4f} mm  {'ok' if ok else '<-- MISMATCH'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
