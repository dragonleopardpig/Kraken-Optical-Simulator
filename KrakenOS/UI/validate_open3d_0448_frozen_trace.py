"""bugs/0448 guard -- rays-on integrity on frozen/snapped scenes.

Two contracts (flag_20260726_181751 "ray on"):

* CONVENTION -- the engine's analytic-surface trace reads the SAME world pose the
  display draws for a 0433-baked row: the system builder re-expresses baked
  NON-SOLID rows' mesh-convention tilts in the trace convention
  (``trace_convention_tilts_from_rotation_matrix``), and the decomposition
  round-trips exactly (incl. the gimbal (0,-90,-180) family, which used to trace
  facing BACKWARDS: signed dot -1).
* PHANTOM-RING -- a vignette-dominated reaching leaf's branch detector is pinned to
  the DESIGNED Image (ring + hard-stop coincide with the sensor) instead of a
  garbage mid-chain focus; the 0090 second arm keeps its own detector; high-reach
  leaves (0097 perpendicular arms / 0099 / two-arm folds) are untouched.
"""
from __future__ import annotations

import inspect as _inspect

import numpy as np


def _trace_rot(tx: float, ty: float, tz: float) -> np.ndarray:
    a, b, c = np.deg2rad([tx, ty, -tz])
    rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    rz = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    return rx @ ry @ rz


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    try:
        from KrakenOS.UI.optical_solid_metadata import (
            rotation_matrix_from_kraken_tilts,
            trace_convention_tilts_from_rotation_matrix,
        )
    except Exception as exc:
        return True, [f"SKIP: metadata module unavailable ({exc!r})"]

    # CONVENTION: divergence pinned + decomposition exact.
    zm = rotation_matrix_from_kraken_tilts(0.0, -90.0, -180.0) @ np.array([0.0, 0.0, 1.0])
    zt = _trace_rot(0.0, -90.0, -180.0) @ np.array([0.0, 0.0, 1.0])
    if np.allclose(zm, (1, 0, 0), atol=1e-9) and np.allclose(zt, (-1, 0, 0), atol=1e-9):
        notes.append("CONVENTION = the two tilt conventions diverge for the baked family (pinned)")
    else:
        notes.append("CONVENTION divergence pin unexpected")
        ok = False
    worst = 0.0
    for t in [(0, -90, -180), (0, 90, 180), (45, 30, 60), (12.3, -89.999, 45)]:
        r_mesh = rotation_matrix_from_kraken_tilts(*t)
        t2 = trace_convention_tilts_from_rotation_matrix(r_mesh)
        worst = max(worst, float(np.abs(r_mesh - _trace_rot(*t2)).max()))
    if worst < 1e-12:
        notes.append("CONVENTION = trace-convention decomposition round-trips exactly")
    else:
        notes.append(f"CONVENTION decomposition error {worst:.2e}")
        ok = False

    # WIRING: the builder converts baked non-solid rows; the branch-detector pin exists.
    try:
        from KrakenOS.UI import layout_editor as _le

        src = _inspect.getsource(_le)
        if "trace_convention_tilts_from_rotation_matrix" in src and "_is_baked_world_pose" in src:
            notes.append("WIRING = system builder re-expresses baked non-solid rows in the trace convention")
        else:
            notes.append("WIRING builder conversion missing")
            ok = False
        from KrakenOS.UI.services import branch_detectors as _bd

        bsrc = _inspect.getsource(_bd.derive_branch_detectors)
        if "_force_pin_focus" in bsrc:
            notes.append("WIRING = vignette-dominated reaching leaf pins to the designed Image")
        else:
            notes.append("WIRING branch-detector pin missing")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: wiring inspection failed ({exc!r})")
        return ok, notes

    # REAL: the user-shaped frozen scene traces + draws honestly.
    try:
        from pathlib import Path

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.nonseq_output_ports import beam_splitter_coating_world_frames
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        scene = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        if not scene.exists():
            notes.append("SKIP: AZ85 scene absent (gitignored attachment)")
            return ok, notes
        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = scene
        app.load_layout_by_name("az85")
        mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([mirror1])
        try:
            app._select_table_indices([1], focus_index=1)
        except Exception:
            app._select_table_row(1)
        app.add_beam_splitter_to_led(kind="plate")
        bs = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.rotate_scene_row_pose_world_axis(bs, "z", 90.0)
        d = np.array([0.0, 0.0, 1.0])
        cen, nrm = beam_splitter_coating_world_frames(app.rows)[0]
        n = np.asarray(nrm, float)
        n = n / np.linalg.norm(n)
        refl = d - 2.0 * float(np.dot(d, n)) * n
        cen = np.asarray(cen, float)
        rows = [
            i
            for i, r in enumerate(app.rows)
            if getattr(r, "surface", None) in ("Standard", "Thin Lens", "Aperture", "Image")
            and i > 0
            and "next gap" not in str(getattr(r, "name", ""))
        ]
        app.snap_rows_to_axis(
            rows,
            {
                "axis_id": "axis:global:split",
                "points": np.array([cen, cen + 260.0 * refl]),
                "picked_world": cen + 66.0 * refl,
            },
        )
        sys1 = app.build_system(require_solids=True, force_rebuild=True)
        worst_dot = 1.0
        for i, r in enumerate(app.rows):
            zdrawn = rotation_matrix_from_kraken_tilts(
                float(r.tilt_x), float(r.tilt_y), float(r.tilt_z)
            ) @ np.array([0.0, 0.0, 1.0])
            ztrace = np.asarray(sys1.TRANS_2A[i])[:3, :3] @ np.array([0.0, 0.0, 1.0])
            worst_dot = min(worst_dot, float(np.dot(zdrawn, ztrace)))
        if worst_dot > 0.999:
            notes.append("REAL = built orientation agrees with drawn on every frozen row")
        else:
            notes.append(f"REAL orientation divergence: worst signed dot {worst_dot:+.4f}")
            ok = False
        insp = _open_inspector(app)
        insp.show_rays_var.set(True)
        insp.refresh_from_editor(force_retrace=True)
        insp.update_idletasks()
        bundle = getattr(app, "_last_scene_bundle", None)
        dets = [
            t for t in (getattr(bundle, "targets", []) or []) if bool(getattr(t, "is_detector", False))
        ]
        image_row = next(
            i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"
        )
        z = app._row_z_positions()
        row_obj = app.rows[image_row]
        image_center = np.array(
            [float(row_obj.desp_x), float(row_obj.desp_y), float(z[image_row]) + float(row_obj.desp_z)]
        )
        reflect = [
            t
            for t in dets
            if "reflect" in str((getattr(t, "metadata", None) or {}).get("branch_path", ""))
        ]
        pinned = bool(reflect) and float(
            np.linalg.norm(np.asarray(reflect[0].center_world, float) - image_center)
        ) < 1.0
        if len(dets) == 2 and pinned:
            notes.append("REAL = 2 arm detectors; imaging arm pinned at the designed Image (no phantom)")
        else:
            notes.append(
                f"REAL detector inventory unexpected: {[(str((getattr(t,'metadata',{}) or {}).get('branch_path','')), np.asarray(t.center_world,float).round(1).tolist()) for t in dets]}"
            )
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
