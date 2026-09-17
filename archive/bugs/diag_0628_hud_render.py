"""bugs/0628 visual verification -- the system-info HUD on the live 3D canvas.

Loads the Apo75 scene (hr25MCX camera registered), refreshes the inspector, prints
the HUD text, and saves a screenshot showing the top-left overlay.

Run:  taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u bugs/diag_0628_hud_render.py
"""

from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_Apo75.py")
OUT = Path("bugs/_0628_system_info_hud.png")


def main() -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
        _open_3d_inspector,
        _save_vtk_snapshot,
        _settle,
    )
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.system_info_hud import system_info_hud_text

    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        print(f"loaded {SCENE.name}; camera model: {app._current_camera_model()!r}")
        text = system_info_hud_text(app)
        print("HUD text:")
        for line in text.splitlines():
            print(f"  | {line}")

        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        actor = insp.__dict__.get("_system_info_hud_actor")
        print(f"HUD actor present: {actor is not None}")
        _save_vtk_snapshot(insp, OUT)
        print(f"saved {OUT}")
        if not text:
            print("FAIL: HUD text empty on a camera-coupled finite scene")
            return 1
        if actor is None:
            print("FAIL: HUD actor missing after refresh")
            return 1
        print("PASS")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
