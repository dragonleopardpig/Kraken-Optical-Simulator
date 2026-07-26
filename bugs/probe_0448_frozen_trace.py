"""bugs/0448 -- rays-on on the frozen/snapped AZ85+BS scene (flag_20260726_181751).

Two defects:

(a) FRAGMENTED rays: the engine has TWO tilt conventions -- the drawn/NS-mesh path
    composes Rz(-tz)@Ry@Rx while the analytic-surface trace's TRANS matrices compose
    Rx@Ry@Rz(-tz). A 0433-baked row stores its world pose in the MESH convention; for
    the folded (0,-90,-180) family the traced surface faced exactly OPPOSITE the drawn
    one (signed dot -1), so rays refracted through backwards surfaces and the display
    fragmented. Fix: the system builder re-expresses a baked NON-SOLID row's rotation
    in the trace convention (trace_convention_tilts_from_rotation_matrix); solids keep
    their angles (their trace geometry is the mesh, already consistent).

(b) PHANTOM coverage rings: the imaging (reflect) arm reaches the sequential Image
    with ~1% of its rays (the launch-aiming seam vignettes the rest); its synthesized
    branch detector took a garbage mid-chain focus -- a phantom Sensor/Image-circle
    ring AND a phantom hard-stop plane. Fix: a vignette-dominated reaching leaf is
    pinned to the DESIGNED Image (normal from the surviving rays); high-reach leaves
    (0097/0099/two-arm) are untouched.

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0448_frozen_trace.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


def _trace_rot(tx: float, ty: float, tz: float) -> np.ndarray:
    """The analytic-trace convention (TRANS_2A local->world): Rx(tx)@Ry(ty)@Rz(-tz)."""
    a, b, c = np.deg2rad([tx, ty, -tz])
    rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    rz = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    return rx @ ry @ rz


def main() -> int:
    from KrakenOS.UI.optical_solid_metadata import (
        rotation_matrix_from_kraken_tilts,
        trace_convention_tilts_from_rotation_matrix,
    )

    # (a0) The two conventions REALLY diverge for the baked family (the pinned bug):
    zm = rotation_matrix_from_kraken_tilts(0.0, -90.0, -180.0) @ np.array([0.0, 0.0, 1.0])
    zt = _trace_rot(0.0, -90.0, -180.0) @ np.array([0.0, 0.0, 1.0])
    check(
        "conventions diverge for (0,-90,-180): drawn +X vs raw-trace -X",
        bool(np.allclose(zm, (1, 0, 0), atol=1e-9) and np.allclose(zt, (-1, 0, 0), atol=1e-9)),
        f"drawn={zm.round(3).tolist()} raw_trace={zt.round(3).tolist()}",
    )
    # (a1) The decomposition round-trips exactly (incl. the gimbal family).
    worst = 0.0
    for t in [(0, -90, -180), (0, 90, 180), (180, 0, 0), (45, 30, 60), (12.3, -89.999, 45)]:
        r_mesh = rotation_matrix_from_kraken_tilts(*t)
        t2 = trace_convention_tilts_from_rotation_matrix(r_mesh)
        worst = max(worst, float(np.abs(r_mesh - _trace_rot(*t2)).max()))
    check("trace-convention decomposition round-trips (worst < 1e-12)", worst < 1e-12, f"worst={worst:.2e}")

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import beam_splitter_coating_world_frames
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([mirror1])
        try:
            app._select_table_indices([1], focus_index=1)
        except Exception:
            app._select_table_row(1)
        app.add_beam_splitter_to_led(kind="plate")
        bs = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.rotate_scene_row_pose_world_axis(bs, "z", 90.0)  # the user's re-aim: fold +Z -> +X
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

        # (a2) BUILT-system orientation agrees with the DRAWN one on every row
        # (SIGNED dot -- the pre-fix state was exactly -1 on the baked chain rows).
        sys1 = app.build_system(require_solids=True, force_rebuild=True)
        worst_dot = 1.0
        for i, r in enumerate(app.rows):
            zm = rotation_matrix_from_kraken_tilts(
                float(r.tilt_x), float(r.tilt_y), float(r.tilt_z)
            ) @ np.array([0.0, 0.0, 1.0])
            t2 = np.asarray(sys1.TRANS_2A[i])[:3, :3]
            zt = t2 @ np.array([0.0, 0.0, 1.0])
            worst_dot = min(worst_dot, float(np.dot(zm, zt)))
        check(
            "frozen+snapped: BUILT orientation agrees with DRAWN on every row (signed)",
            worst_dot > 0.999,
            f"worst signed dot={worst_dot:+.4f}",
        )

        # (b) rays on: exactly TWO branch detectors -- the imaging (reflect) arm PINNED
        # at the designed Image with a sensor-facing normal, and the 0090 transmit arm;
        # no vignette-focus mid-chain phantom.
        insp = _open_inspector(app)
        insp.show_rays_var.set(True)
        insp.refresh_from_editor(force_retrace=True)
        insp.update_idletasks()
        bundle = getattr(app, "_last_scene_bundle", None)
        dets = [t for t in (getattr(bundle, "targets", []) or []) if bool(getattr(t, "is_detector", False))]
        det_info = [
            (
                str((getattr(t, "metadata", None) or {}).get("branch_path", "")),
                np.asarray(getattr(t, "center_world", (0, 0, 0)), float),
                str((getattr(t, "metadata", None) or {}).get("focus_source", "")),
            )
            for t in dets
        ]
        check("rays on: exactly 2 branch detectors (imaging arm + 0090 second arm)", len(dets) == 2, str([(b, c.round(1).tolist()) for b, c, _ in det_info]))
        image_row = next(
            i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"
        )
        z = app._row_z_positions()
        img_row_obj = app.rows[image_row]
        image_center = np.array(
            [float(img_row_obj.desp_x), float(img_row_obj.desp_y), float(z[image_row]) + float(img_row_obj.desp_z)]
        )
        reflect = [e for e in det_info if "reflect" in e[0]]
        check(
            "imaging arm detector PINNED at the designed Image (no mid-chain phantom)",
            bool(reflect) and float(np.linalg.norm(reflect[0][1] - image_center)) < 1.0 and reflect[0][2] == "reached_image",
            f"det={reflect[0][1].round(1).tolist() if reflect else None} image={image_center.round(1).tolist()}",
        )
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- traced orientation follows the drawn pose; phantom ring pinned to the Image")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
