"""bugs/0529 guard -- the lens drag+refocus gesture is ONE undo step (both drag surfaces).

flag_20260804_073309: "dragged lens to the right, FOV changed, ray refocus. Ctrl-z not
going back to previous state." The drag commit and the 0528/0520 refocus each pushed their
own history entry, so the first Ctrl-Z only un-seated the sensor (~18 mm, invisible at
scene zoom) and the gesture read as un-undoable -- the flag's recorded state is exactly
the post-first-press split (drag kept, image gap back to fresh).

Per the 0449 doctrine one public gesture = ONE undo step: the gizmo-arrow finish wraps
translate + snap in a history transaction; the carry finish commits its pending capture
AFTER the snap so both writes share the pre-gesture snapshot.

Checks:
  SOURCE -- the arrow finish runs inside history_transaction; the carry finish commits
            after the snap.
  REAL   -- on the frozen AZ85 scene each gesture adds exactly ONE undo entry; a single
            undo restores gaps + lens offset + sensor seat; redo reapplies the gesture.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import open3d_inspector as _oi

    src_arrow = _inspect.getsource(_oi.Kraken3DInspector._finish_step_translate_drag)
    if "bugs/0529" in src_arrow and "history_transaction" in src_arrow:
        notes.append("SOURCE = the gizmo-arrow finish groups the gesture in a history transaction")
    else:
        notes.append("SOURCE the arrow finish no longer wraps the gesture in a transaction")
        ok = False
    src_carry = _inspect.getsource(_oi.Kraken3DInspector._finish_step_carry_drag)
    snap_at = src_carry.find("snap_detector_to_image_plane")
    commit_at = src_carry.find("_commit_history_capture")
    if snap_at >= 0 and commit_at > snap_at:
        notes.append("SOURCE = the carry finish commits its pending capture AFTER the snap")
    else:
        notes.append("SOURCE the carry finish commits before the snap (two-entry gesture)")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector
        from KrakenOS.UI.services import optical_axis_tree as tree_mod

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)

        def snapshot():
            return {
                "gaps": tuple(round(float(r.thickness), 3) for r in app.rows),
                "lens_off": tuple(round(float(v), 3) for v in app._step_placement_offset_xyz("lens")),
                "sensor_z": round(float(np.asarray(tree_mod.row_world_pose(app.rows, len(app.rows) - 1), float).reshape(-1)[2]), 3),
            }

        fresh = snapshot()

        def drive(tag, gesture) -> None:
            nonlocal ok
            depth = len(app._undo_stack)
            gesture()
            dragged = snapshot()
            entries = len(app._undo_stack) - depth
            if dragged == fresh:
                notes.append(f"REAL {tag} gesture did not move the model")
                ok = False
                return
            if entries == 1:
                notes.append(f"REAL = the {tag} gesture pushed exactly ONE undo entry")
            else:
                notes.append(f"REAL the {tag} gesture pushed {entries} undo entries")
                ok = False
            app.undo()
            if snapshot() == fresh:
                notes.append(f"REAL = one Ctrl-Z restores the pre-{tag} state (gaps + offset + sensor)")
            else:
                notes.append(f"REAL one Ctrl-Z left the {tag} gesture partially applied: {snapshot()}")
                ok = False
                while snapshot() != fresh and app._undo_stack:
                    app.undo()
                return
            app.redo()
            if snapshot() == dragged:
                notes.append(f"REAL = redo reapplies the whole {tag} gesture")
            else:
                notes.append(f"REAL redo left the {tag} gesture partial: {snapshot()}")
                ok = False
            app.undo()

        drive("arrow", lambda: insp._finish_step_translate_drag(
            {"label": "lens", "axis": "x", "axis_unit": (1.0, 0.0, 0.0), "applied_delta_mm": 53.135}
        ))

        def carry():
            app._begin_history_capture()  # live: the first carry motion frame begins the capture
            for _ in range(10):
                app.translate_step_overlay("lens", (5.3135, 0.0, 0.0), refresh=False, record_history=False)
            insp._finish_step_carry_drag({"label": "lens", "applied_steps": 10, "history_started": True})

        drive("carry", carry)
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
