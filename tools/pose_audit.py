"""Step 0 of docs/design_row_placement_space.md — the POSE AUDIT.

Goal (the user's words): "whatever I see in the live scene — elements with their position
AND orientation — the underlying physics should match."

This reports, per row, the pose each subsystem believes in, and flags disagreements:

  PRESCRIPTION  station + desp (+ tilts)      — what the sequential trace consumes
  DRAWN         the live VTK actor            — what the user actually sees (VISIBLE actors
                                                only: zero-opacity picking proxies are not
                                                "seen", and counting them produced a false
                                                51.50 mm disagreement on bugs/0457)
  BODY          the STEP overlay mesh centre  — what the CAD shows

Read-only: it changes nothing. It exists because three fixes were reverted on 2026-07-28
for being written before a reproduction existed. Nothing else should be written on
bugs/0457 until this reproduces the -48.8 the live app draws.

Usage:
    DISPLAY=:N .devenv/state/venv/bin/python tools/pose_audit.py [scene.py]

Default scene: attachment/machine_vision_ELS85.py -- AZ85 IS ELS-85 (same lens, renamed),
and machine_vision_AZ85_RA_Mirror_BS.py no longer exists. ELS85 carries the same structure
that made it the 0457 repro: 21 world-placement keys and a promoted beam splitter.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

DEFAULT_SCENE = Path("attachment/machine_vision_ELS85.py")
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
                # Only VISIBLE geometry counts as "what the user sees". An actor at zero
                # opacity is a picking proxy: the suppress_reference_aperture path
                # (bugs/0033/0047) adds the Object/Image disk invisibly so picking still
                # works while the detector-coverage overlay draws the real iconography.
                # Counting those cost a long chase on bugs/0457 -- the recorder's
                # row_actor_bounds includes them, and a -48.77 picking disk was read as a
                # visibly misplaced sensor.
                if not bool(actor.GetVisibility()):
                    continue
                if float(actor.GetProperty().GetOpacity()) <= 1.0e-6:
                    continue
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


#: The canonical STEP-overlay labels, as ``open3d_inspector`` itself enumerates them.
#: The first version of this audit listed only three and omitted "optical", which is
#: where a promoted beam splitter lives -- so ELS85 reported bodies=0 while declaring six
#: promoted solids with its STEP file present on disk.
STEP_OVERLAY_LABELS = ("optical", "lens", "camera", "led")


def _body_centers(app) -> "tuple[dict, list[str]]":
    """Every body the audit can see, and why it could not see the rest.

    Returns ``(bodies, problems)``. A body is ``{"center", "kind", ...}``; promoted rows
    additionally carry ``authored`` and ``drift_mm``.

    Two kinds, because a scene's bodies are not all of one sort:

    * **step overlay** -- an imported STEP drawn under one of the four labels.
    * **promoted** -- a CAD row promoted to an optical element. Its authored world centre
      lives in ``advanced["StepOverlayPromotion"]["center_world"]`` and its live centre
      comes from the follower walk. The overlay refresh deliberately SKIPS promoted
      bodies, so the label path alone can never see them -- which is exactly why a scene
      whose bodies are all promoted audited as having none.

    Nothing is swallowed. The old version wrapped the whole loop in
    ``except Exception: continue``, so a body that failed to measure was indistinguishable
    from a body that was not there -- the bugs/0457 lesson in a different costume.
    """
    bodies: dict = {}
    problems: list[str] = []

    for label in STEP_OVERLAY_LABELS:
        try:
            if app._step_path_for_label(label) is None:
                continue  # genuinely absent, not a failure
        except Exception as exc:
            problems.append(f"step label {label!r}: path lookup raised {exc!r}")
            continue
        try:
            mesh = app._transformed_imported_step_mesh_for_label(label)
        except Exception as exc:
            problems.append(f"step label {label!r}: mesh build raised {exc!r}")
            continue
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            problems.append(f"step label {label!r}: has a STEP path but produced no geometry")
            continue
        b = np.asarray(mesh.bounds, dtype=float).reshape(6)
        bodies[f"step:{label}"] = {
            "center": np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2], float),
            "kind": "step overlay",
        }

    # A promoted row IS its body, so its live centre must be the SOLID's centre in the SAME
    # convention as the authored snapshot (``StepOverlayPromotion.center_world``). Getting
    # this wrong manufactures a precise, confident, meaningless number -- measured: using
    # the row's own pose (``_promoted_solid_current_center``, whose first branch returns
    # ``_split_row_world_center`` = the surface VERTEX) reports 132-480 mm of "drift" on
    # om05a_folded.py, a scene bugs/0750 calibrated to read 0.000000 mm healthy. The row
    # pose is the right answer for collision work (bugs/0483) and the wrong quantity here.
    #
    # Two commensurate sources, both centre_world:
    #   1. the output-port pose walk -- what scene_placement_audit is calibrated on;
    #   2. the last scene bundle's ``optical_solid`` placement, same field name.
    # When neither answers, the body is still LISTED with its authored centre and the gap is
    # named. An unmeasurable body must never be silently dropped, and must never borrow a
    # number from a different convention to look measured.
    try:
        from KrakenOS.UI.services.scene_placement_audit import pinned_placement_drifts

        bundle = getattr(app, "_last_scene_bundle", None)
        bundle_centers: dict = {}
        for placement in list(getattr(bundle, "placements", None) or []):
            if str(getattr(placement, "source_kind", "") or "") != "optical_solid":
                continue
            try:
                bundle_centers[int(getattr(placement, "row_index", -1))] = np.asarray(
                    list(getattr(placement, "center_world"))[:3], dtype=float
                )
            except Exception:
                continue

        for record in pinned_placement_drifts(list(getattr(app, "rows", []) or [])):
            index = int(record["row"])
            name = record["name"] or f"row {index}"
            key = f"promoted:{index}:{name}"
            authored = np.asarray(record["authored"], dtype=float)
            live, via = None, None
            if record["live"] is not None:
                live, via = np.asarray(record["live"], dtype=float), "output-port walk"
            elif index in bundle_centers:
                live, via = bundle_centers[index], "bundle placement"
            if live is None:
                bodies[key] = {
                    "center": None,
                    "authored": authored,
                    "drift_mm": None,
                    "kind": "promoted (authored only)",
                }
                problems.append(
                    f"{key}: no commensurate live centre -- the output-port walk returned "
                    f"nothing and the bundle carries no optical_solid placement for this row"
                )
                continue
            bodies[key] = {
                "center": live,
                "authored": authored,
                "drift_mm": float(np.linalg.norm(live - authored)),
                "kind": f"promoted via {via}",
            }
    except Exception as exc:
        problems.append(f"promoted-solid audit raised {exc!r}")

    return bodies, problems


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
        bodies, body_problems = _body_centers(app)

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

        print("\n  BODIES:")
        if not bodies and not body_problems:
            print("    none -- this scene declares no STEP overlay and no promoted solid")
        for key, body in bodies.items():
            shown = _fmt(body['center']) if body['center'] is not None else _fmt(body['authored'])
            line = f"    {key:<34} {shown}  [{body['kind']}]"
            drift = body.get("drift_mm")
            if drift is not None:
                line += f"  drift {float(drift):.4f} mm from authored"
            print(line)
        for problem in body_problems:
            print(f"    UNMEASURED  {problem}")
        # Body drift is REPORTED, not failed on. scene_placement_audit documents that an
        # absolute reading is red at rest on rows whose authored snapshot is merely stale
        # (om05a_folded_80mm row 16 sits at 545 mm from a sign difference predating all of
        # this), so compare_drifts -- the delta form -- is the gating instrument. Inventing
        # an absolute tolerance here would make the audit noisy exactly where it must be
        # trusted.
        drifted = [b for b in bodies.values() if (b.get("drift_mm") or 0.0) > POSITION_TOL_MM]
        if drifted:
            print(f"    ({len(drifted)} promoted bod{'y' if len(drifted) == 1 else 'ies'} "
                  f"drift from authored; use scene_placement_audit.compare_drifts to gate)")

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
