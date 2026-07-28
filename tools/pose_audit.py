"""Step 0 of docs/design_row_placement_space.md — the POSE AUDIT.

Goal (the user's words): "whatever I see in the live scene — elements with their position
AND orientation — the underlying physics should match."

This reports, per row, the pose each subsystem believes in, and flags disagreements:

  PRESCRIPTION  station + desp (+ tilts)      — what the sequential trace consumes
  DRAWN         the live VTK actor            — what the user actually sees
  BODY          the STEP overlay mesh centre  — what the CAD shows

Read-only: it changes nothing. It exists because three fixes were reverted on 2026-07-28
for being written before a reproduction existed. Nothing else should be written on
bugs/0457 until this reproduces the -48.8 the live app draws.

Usage:
    DISPLAY=:N .devenv/state/venv/bin/python tools/pose_audit.py [scene.py]

Default scene: attachment/machine_vision_AZ85_RA_Mirror_BS.py (the 0457 repro).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

DEFAULT_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
POSITION_TOL_MM = 1.0
ANGLE_TOL_DEG = 1.0


def _fmt(vec) -> str:
    if vec is None:
        return "        --            "
    return "(" + ", ".join(f"{float(v):8.2f}" for v in vec) + ")"


def _prescription_pose(app, index: int):
    """Position + tilts as the sequential trace reads them."""
    z = app._row_z_positions()
    row = app.rows[index]
    position = np.array(
        [float(row.desp_x), float(row.desp_y), float(z[index]) + float(row.desp_z)], dtype=float
    )
    tilts = []
    for name in ("tilt_x", "tilt_y", "tilt_z", "TiltX", "TiltY", "TiltZ"):
        value = getattr(row, name, None)
        if value is not None:
            tilts.append(float(value))
        if len(tilts) == 3:
            break
    return position, (np.array(tilts, dtype=float) if len(tilts) == 3 else None)


def _drawn_poses(inspector) -> dict:
    """Per-row DRAWN pose straight off the VTK actors -- centre AND orientation.

    The recorder's snapshot carries bounds only, which cannot express orientation, so the
    actors are read directly (0448 was a TILT divergence; a position-only audit would
    have missed it)."""
    out: dict[int, tuple] = {}
    actor_by_key = getattr(inspector, "_actor_by_key", None) or {}
    row_actor_map = getattr(inspector, "_row_actor_map", None) or {}
    for row_index, keys in row_actor_map.items():
        try:
            index = int(row_index)
        except Exception:
            continue
        centers, orientations = [], []
        for key in keys or []:
            actor = actor_by_key.get(key)
            if actor is None:
                continue
            try:
                b = [float(v) for v in actor.GetBounds()]
                if any(b[i] > b[i + 1] for i in (0, 2, 4)):
                    continue
                centers.append([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2])
                orientations.append([float(v) for v in actor.GetOrientation()])
            except Exception:
                continue
        if centers:
            out[index] = (
                np.asarray(centers, dtype=float).mean(axis=0),
                np.asarray(orientations, dtype=float).mean(axis=0) if orientations else None,
            )
    return out


def _body_centers(app) -> dict:
    out = {}
    for label in ("lens", "camera", "led"):
        try:
            mesh = app._transformed_imported_step_mesh_for_label(label)
            if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
                continue
            b = np.asarray(mesh.bounds, dtype=float).reshape(6)
            out[label] = np.array(
                [(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2], dtype=float
            )
        except Exception:
            continue
    return out


def main(argv: list[str]) -> int:
    scene = Path(argv[1]) if len(argv) > 1 else DEFAULT_SCENE
    if not scene.exists():
        print(f"scene not found: {scene}")
        return 2

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    disagreements: list[str] = []
    try:
        app.layout_files["audit"] = scene
        app.load_layout_by_name("audit")

        inspector = None
        try:
            app.open_3d_view()
            app.update_idletasks()
            app.update()
            inspector = app.__dict__.get("_three_d_inspector")
        except Exception as exc:
            print(f"[warn] could not open the 3-D view: {exc!r}")
        if inspector is not None:
            # open_3d_view alone does not populate the actor registry -- force the build
            # the live app performs, or the audit reports an empty scene (it did).
            for attempt in (
                lambda: inspector.refresh_from_editor(force_retrace=True, geometry_changed=True),
                lambda: inspector.refresh_from_editor(force_retrace=True),
                lambda: inspector.refresh_from_editor(),
            ):
                try:
                    attempt()
                    inspector.update_idletasks()
                    inspector.update()
                    if getattr(inspector, "_row_actor_map", None):
                        break
                except Exception:
                    continue

        drawn = _drawn_poses(inspector) if inspector is not None else {}
        bodies = _body_centers(app)

        print(f"\nPOSE AUDIT — {scene.name}")
        print(f"  rows={len(app.rows)}  drawn_row_actors={len(drawn)}  bodies={len(bodies)}\n")
        print(f"  {'row':>4} {'surface':<11} {'PRESCRIPTION':^30} {'DRAWN':^30}  delta")
        for index, row in enumerate(app.rows):
            presc, _tilts = _prescription_pose(app, index)
            drawn_pose = drawn.get(index)
            drawn_pos = None if drawn_pose is None else drawn_pose[0]
            delta = "" if drawn_pos is None else f"{float(np.linalg.norm(drawn_pos - presc)):8.2f} mm"
            flag = ""
            if drawn_pos is not None and float(np.linalg.norm(drawn_pos - presc)) > POSITION_TOL_MM:
                flag = "   <== DISAGREE"
                disagreements.append(
                    f"row {index} ({getattr(row, 'surface', '?')}): drawn {np.round(drawn_pos, 2).tolist()} "
                    f"vs prescription {np.round(presc, 2).tolist()}"
                )
            print(
                f"  {index:>4} {str(getattr(row, 'surface', ''))[:11]:<11} "
                f"{_fmt(presc)} {_fmt(drawn_pos)} {delta}{flag}"
            )

        for index, (pos, orient) in sorted(drawn.items()):
            if index >= len(app.rows) and orient is not None:
                print(f"  {index:>4} (synthesised)  drawn={_fmt(pos)} orientation={_fmt(orient)}")

        print("\n  STEP bodies:")
        for label, center in bodies.items():
            print(f"    {label:<8} {_fmt(center)}")

        print()
        if not drawn:
            print("RESULT: INCONCLUSIVE — no row actors were built, so DRAWN could not be read.")
            print("        The audit cannot see the bug in this environment; run it where the")
            print("        live viewer paints (that divergence is itself finding #1).")
            return 3
        if disagreements:
            print(f"RESULT: {len(disagreements)} DISAGREEMENT(S) — drawn != prescription:")
            for line in disagreements:
                print(f"  - {line}")
            return 1
        print("RESULT: CLEAN — every drawn row agrees with the prescription it is traced from.")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
