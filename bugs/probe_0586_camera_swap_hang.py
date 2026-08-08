"""bugs/0586: does `replace_camera_from_folder` HANG headlessly, and where?

"Change the camera at will" is half the user's stated objective, and the camera half of the
bugs/0579 sweep has never executed -- the sweep was stopped before its six camera rows. A first
attempt timed out at 600 s with memory pressure at 0.00, so it is a genuine hang, not starvation.
The suspicion (bugs/0408): the vendor-folder import PROMPTS for the flange-to-sensor distance when
the datasheet lacks it, and a modal dialog with nobody to answer it waits forever.

This probe does not rely on signalling the right PID -- xvfb-run's process tree makes that
unreliable (two failed attempts). It arms ``faulthandler.dump_traceback_later(..., exit=True)``,
so the process dumps its OWN stack and dies if it is still running when the deadline passes. The
deepest frame names the blocker.

Run (one camera folder per invocation, cheap):
    taskset -c 10-13 nice -n 19 xvfb-run -a .devenv/state/venv/bin/python \
        bugs/probe_0586_camera_swap_hang.py attachment/Cameras/BC-GM25M12X1
"""
from __future__ import annotations

import faulthandler
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
DEADLINE_S = 75.0


def main() -> int:
    camera = Path(sys.argv[1] if len(sys.argv) > 1 else "attachment/Cameras/BC-GM25M12X1")
    if not camera.is_absolute():
        camera = PROJECT_ROOT / camera
    if not SCENE.exists() or not camera.is_dir():
        print(f"SKIP: scene or camera folder missing ({camera})")
        return 0

    faulthandler.enable()
    print(f"probe: {camera.name}; will dump its own stack and exit after {DEADLINE_S:.0f}s",
          flush=True)

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        _open_inspector(app)
        print("probe: scene loaded, inspector open -- calling replace_camera_from_folder",
              flush=True)
        # Arm the deadline around the CALL only, so a slow scene load is not misread as the hang.
        faulthandler.dump_traceback_later(DEADLINE_S, exit=True)
        imported = app.replace_camera_from_folder(str(camera), refresh_open_3d=False)
        faulthandler.cancel_dump_traceback_later()
        print(f"probe: RETURNED {getattr(imported, 'name', imported)!r}", flush=True)
        print(f"probe: status {app.status_var.get()!r}"[:200], flush=True)
        try:
            bounds = app._transformed_imported_step_mesh_for_label("camera").bounds
            print(f"probe: camera body bounds {[round(float(v), 3) for v in bounds]}", flush=True)
        except Exception as exc:
            print(f"probe: camera body unavailable ({type(exc).__name__})", flush=True)
    finally:
        faulthandler.cancel_dump_traceback_later()
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
