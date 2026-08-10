"""Guard for bugs/0597 — Normal to Sensor must SHOW THE SENSOR, never un-hide the world.

Flag `flag_20260810_083640_360`: *"Enabling Normal to Sensor: components not hidden."* On the
folded Apo75 scene with rays ON and the Det overlay OFF, three defects composed:

  1. the illumination-anchor resolver handed back a synthetic branch-detector plane 226.6 mm
     up the straight axis (the bugs/0556/0589 class, through yet another door);
  2. the bugs/0589 drawn-actor cross-check could not engage because this scene draws NO
     Image-row geometry at all — `_drawn_sensor_center_world` returned None;
  3. the isolation around the phantom plane therefore hid everything, and the bugs/0589
     "never a blank canvas" fallback restored the ENTIRE scene — rays, LED plate and all.

Fix: (a) when nothing is drawn to cross-check against, adopt the terminal Image row's
`row_placement.world_frame` — the same resolver the frozen display seats rows with — position
AND orientation; (b) when the isolation still keeps nothing (no geometry lives at the sensor
plane), DRAW the detector overlays (coverage + labelled sensor square) for this view and
re-apply the band filter, falling back to restore-all only when even that cannot draw.

Checks:
  A  CONTRACT — the view adopts `row_placement.world_frame` when nothing is drawn, and draws
     the detector overlays before falling back to restore-all.
  B  REAL (skipped without the fixture) — on the flagged state (rays ON, Det OFF):
     the view returns True, a MINORITY of actors stays visible (components hidden), and at
     least one visible actor sits within the isolation band of the resolver-true sensor plane.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0597_sensor_view_draws_the_sensor
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import open3d_inspector as inspector_module

    view_src = inspect.getsource(inspector_module.Kraken3DInspector.view_normal_to_sensor)
    if "world_frame" not in view_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0597): the view no longer adopts row_placement.world_frame when "
            "nothing is drawn — a synthetic-anchor scene aims at the phantom again"
        )
    else:
        notes.append("PASS: A1: the view adopts the row_placement frame when nothing is drawn")
    if "_add_detector_coverage_overlays" not in view_src or "_add_scene_detector_overlays" not in view_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0597): the view no longer draws the detector overlays before the "
            "restore-all fallback — an empty sensor plane un-hides the world again"
        )
    else:
        notes.append("PASS: A2: the view draws the detector overlays before restore-all")

    if not SCENE.exists():
        notes.append(f"SKIP: B: fixture scene missing ({SCENE})")
        return ok, notes

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector
    from KrakenOS.UI.services import row_placement

    app = None
    try:
        app = KrakenLayoutEditor()
        app.layout_files["_0597"] = SCENE
        app.load_layout_by_name("_0597")
        inspector = _open_inspector(app)
        inspector.show_rays_var.set(True)
        inspector.show_detector_overlays_var.set(False)  # the flagged state: Det OFF
        inspector.refresh_from_editor(force_retrace=True)
        for _ in range(4):
            app.update()
            inspector.update()
        total_before = len(inspector._actor_by_key or {})
        result = inspector.view_normal_to_sensor()
        if not result:
            ok = False
            notes.append("FAIL: B: view_normal_to_sensor returned False on the fixture scene")
            return ok, notes
        position, rotation, _space = row_placement.world_frame(app, len(app.rows) - 1)
        centre = np.asarray(position, dtype=float).reshape(3)
        normal = np.asarray(rotation[:, 2], dtype=float) if rotation is not None else np.asarray([0.0, 0.0, 1.0])
        normal = normal / max(float(np.linalg.norm(normal)), 1e-12)
        visible = 0
        on_plane = 0
        total = 0
        for actor in (inspector._actor_by_key or {}).values():
            total += 1
            try:
                if not actor.GetVisibility():
                    continue
                visible += 1
                b = np.asarray(actor.GetBounds(), dtype=float).reshape(6)
                corners = np.array(
                    [(b[i], b[2 + j], b[4 + k]) for i in (0, 1) for j in (0, 1) for k in (0, 1)],
                    dtype=float,
                )
                if float(np.max(np.abs((corners - centre) @ normal))) <= 3.5:
                    on_plane += 1
            except Exception:
                continue
        if visible == 0:
            ok = False
            notes.append("FAIL: B (bugs/0589): the view left NOTHING visible — a blank canvas")
        elif visible >= max(4, total // 2):
            ok = False
            notes.append(
                f"FAIL: B (bugs/0597): {visible}/{total} actors still visible — the components "
                "were not hidden (the restore-all fallback fired)"
            )
        elif on_plane == 0:
            ok = False
            notes.append(
                f"FAIL: B (bugs/0597): {visible} visible actors but NONE within the isolation "
                "band of the resolver-true sensor plane — the view is showing something else"
            )
        else:
            notes.append(
                f"PASS: B: components hidden ({visible}/{total} visible, was {total_before} "
                f"before the view), {on_plane} on the true sensor plane"
            )
    except Exception as exc:  # pragma: no cover - harness failure, not a product failure
        ok = False
        notes.append(f"FAIL: harness error {type(exc).__name__}: {exc}")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Sensor-view-draws-the-sensor validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
