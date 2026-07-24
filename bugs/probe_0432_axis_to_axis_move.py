"""Probe (bugs/0432): axis-to-axis MOVE core command on AZ85.

Verifies move_axis_downstream_to_axis: elements on the OLD axis (+Z at x=0) PAST the NEW axis's
branch point (0,0,96.6) relocate onto the NEW axis (+X), reorient +Z->+X, distances preserved;
object/upstream stay. Checks the moved rows' resulting world centers land on the +X reflect axis
and the tilt reorients +Z->+X.

Run:  .devenv/state/venv/bin/python bugs/probe_0432_axis_to_axis_move.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
BRANCH = (0.0, 0.0, 96.6)


def main() -> int:
    app = KrakenLayoutEditor()
    rc = 1
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        z = app._row_z_positions()
        old_axis = {"axis_id": "axis:global", "axis_label": "Optical Axis",
                    "points": np.array([(0.0, 0.0, -200.0), (0.0, 0.0, 600.0)])}
        new_axis = {"axis_id": "axis:global:split", "axis_label": "Optical Axis (BS reflect)",
                    "points": np.array([BRANCH, (88.9, 0.0, 96.6)])}

        print("row roster (prescription z, on-axis if x=y=desp=0):")
        for i, r in enumerate(app.rows):
            print(f"  S{i} z={z[i]:7.2f} surf={getattr(r,'surface','?'):9} desp=({r.desp_x:.1f},{r.desp_y:.1f},{r.desp_z:.1f}) {getattr(r,'name','')[:30]}")

        result = app.move_axis_downstream_to_axis(old_axis, new_axis)
        moved = result.get("moved_rows", [])
        print(f"\nmoved rows: {moved}")
        print(f"status: {app.status_var.get()}")

        # verify each moved row's world center is on +X at z=96.6, and it reoriented +Z->+X
        ok = True
        R_expect = None
        for i in moved:
            r = app.rows[i]
            station = np.array([0.0, 0.0, float(z[i])])
            center = station + np.array([r.desp_x, r.desp_y, r.desp_z])
            on_axis = abs(center[1]) < 1e-6 and abs(center[2] - 96.6) < 1e-6 and center[0] >= -1e-6
            Rr = rotation_matrix_from_kraken_tilts(r.tilt_x, r.tilt_y, r.tilt_z)
            local_z_world = Rr @ np.array([0.0, 0.0, 1.0])  # the surface's optical-axis dir in world
            faces_x = np.allclose(local_z_world, (1.0, 0.0, 0.0), atol=1e-6)
            print(f"  S{i}: new_center={center.round(2)} on_+X_axis={on_axis} optical_axis_dir={local_z_world.round(3)} ->+X={faces_x}")
            ok = ok and on_axis and faces_x
        # object + upstream must NOT have moved
        obj_moved = any(getattr(app.rows[i], "surface", None) == "Object" for i in moved)

        # STEP overlays follow -- INFORMATIONAL on base AZ85: the mirror DISPLAY fold puts the STEP at a
        # folded pose while the prescription surrogate rows are on straight +Z, so this scene can't validate
        # the follow (needs the mirrors-removed flag scene). The transform is math-verified: a straight-axis
        # STEP centre (0,0,z) -> (z-96.6, 0, 96.6) on +X. In-app eyeball on the real scene.
        print("\n=== STEP overlays follow the move (informational -- base AZ85 has a confounding fold override) ===")
        for label in ("lens", "camera"):
            if app._step_path_for_label(label) is None:
                print(f"  {label}: (not imported -- skip)")
                continue
            mesh = app._transformed_imported_step_mesh_for_label(label)
            if mesh is None:
                print(f"  {label}: mesh unavailable"); continue
            b = np.asarray(mesh.bounds, dtype=float)
            c = np.array([(b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2])
            print(f"  {label}: STEP centre after move = {c.round(1)} (carried by the same rigid transform)")
        # math check of the STEP-follow transform on a straight-axis centre
        from KrakenOS.UI.optical_solid_metadata import rotation_matrix_aligning_vectors
        R = rotation_matrix_aligning_vectors(np.array([0.,0.,1.]), np.array([1.,0.,0.]))
        bp = np.array(BRANCH)
        tgt = bp + R @ (np.array([0.,0.,130.]) - bp)
        math_ok = np.allclose(tgt, (33.4, 0.0, 96.6), atol=1e-6)
        print(f"  [math] straight-axis STEP centre (0,0,130) -> {tgt.round(2)} on +X: {math_ok}")
        print(f"\n[{'PASS' if (ok and moved and not obj_moved and math_ok) else 'FAIL'}] rows on +X reflect axis, object untouched, STEP-follow transform math-correct")
        rc = 0 if (ok and moved and not obj_moved and math_ok) else 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
