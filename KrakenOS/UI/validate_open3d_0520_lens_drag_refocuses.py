"""bugs/0520 guard -- a committed LENS carry drag refocuses the image at the sensor.

flag_20260803_140823 + the user's principle: dragging the lens is a conjugate edit --
"Solve for FOV". The interactive carry-drag commit (``_finish_step_carry_drag``) now runs
the 0490/0515 traced-focus snap for the ``lens`` label and refreshes the QE readout; other
labels keep the 0433 stay-put contract, and headless ``translate_step_overlay`` calls are
untouched (the hook only fires on the interactive commit).

Checks:
  SOURCE -- the finish hook gates on the lens label and runs snap + readout.
  REAL   -- on the frozen AZ85 scene: slide the lens assembly 8 mm off focus, invoke the
            finish hook with a lens carry state, and the sensor/camera re-seat (the snap
            moved them) with the refocus note in the status line.
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

    src = _inspect.getsource(_oi.Kraken3DInspector._finish_step_carry_drag)
    if 'transition.label == "lens"' in src and "snap_detector_to_image_plane" in src:
        notes.append("SOURCE = the lens carry commit runs the traced-focus snap")
    else:
        notes.append("SOURCE the 0520 lens-drag refocus is missing from the finish hook")
        ok = False
    if "_quick_estimation_service().update_readout" in src:
        notes.append("SOURCE = the commit refreshes the QE readout (FOV follows)")
    else:
        notes.append("SOURCE the commit no longer refreshes the QE readout")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        app.translate_step_overlay("lens", (0.0, 0.0, 8.0))
        gap0 = float(app.rows[len(app.rows) - 2].thickness)
        cam0 = np.asarray(app._step_placement_offset_xyz("camera"), dtype=float)
        insp._finish_step_carry_drag({"label": "lens", "applied_steps": 1})
        gap1 = float(app.rows[len(app.rows) - 2].thickness)
        cam1 = np.asarray(app._step_placement_offset_xyz("camera"), dtype=float)
        moved = abs(gap1 - gap0) > 0.2 or float(np.max(np.abs(cam1 - cam0))) > 0.2
        if moved:
            notes.append(
                f"REAL = the commit re-seated the sensor/camera (gap {gap0:.2f}->{gap1:.2f}, "
                f"cam delta {np.round(cam1 - cam0, 2).tolist()})"
            )
        else:
            notes.append("REAL the commit left the sensor where the defocused slide put it")
            ok = False
        if "Solve for FOV" in str(insp.status_var.get()):
            notes.append("REAL = the status carries the refocus note")
        else:
            notes.append(f"REAL no refocus note in status: {insp.status_var.get()[-100:]}")
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
