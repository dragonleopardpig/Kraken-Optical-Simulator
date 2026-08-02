"""bugs/0508 B -- render before/after snapshots of the glued-BS assembly drag.

Replaces the in-app eyeball where the scene renders headless: load the AZ85 BS
scene, snapshot, commit a BS-row drag (now the assembly/station gesture), refresh,
snapshot again. Inspect the PNGs: LED housing + BS + object leg move together,
frozen chain (lens/mirror/camera) stays, rays still land on the sensor.

Run:
    timeout 900 xvfb-run -a .devenv/state/venv/bin/python -u bugs/probe_0508b_snapshot.py <outdir>
"""
from __future__ import annotations

import sys
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    _open_3d_inspector,
    _save_vtk_snapshot,
)

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT.mkdir(parents=True, exist_ok=True)

app = KrakenLayoutEditor(headless=True)
try:
    app.layout_files["probe"] = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
    app.load_layout_by_name("probe")
    insp = _open_3d_inspector(app)
    for preset in ("top", "xz", "iso"):
        try:
            insp.set_camera_preset(preset)
            print(f"camera preset: {preset}", flush=True)
            break
        except Exception:
            continue
    _save_vtk_snapshot(insp, OUT / "0508b_before.png")
    print("SNAP before", flush=True)
    app.translate_scene_row_pose_vector(3, (-30.0, 0.0, 0.0))
    insp.refresh_from_editor(force_retrace=True)
    try:
        app.update_idletasks()
        app.update()
    except Exception:
        pass
    _save_vtk_snapshot(insp, OUT / "0508b_after.png")
    print("SNAP after", flush=True)
finally:
    try:
        app.destroy()
    except Exception:
        pass
