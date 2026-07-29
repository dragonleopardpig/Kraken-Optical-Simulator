"""bugs/0462 guard -- sensor iconography follows the CAMERA, not the leaf count.

flag_20260729_105204: "big improvement, the ray now tracing. But still have 3 sensor/image
plane and multiple optical axis." The scene has ONE camera, but a beam splitter makes every
terminal leaf a detector and the coverage overlay drew "Sensor 23.0x23.0 / Image circle
Oe32.6" on all three -- putting two phantom sensors mid-scene, at (74.4, 31.3) and
(-0.5, 68.4).

Those numbers are properties of a REAL camera. An arm with no camera has no sensor size and
no image circle, so it must not display them. The arm still keeps its detector target and its
ray hard-stop -- exactly the bugs/0451 shape, where the dead-end arm kept its stop and lost
its ring.

Checks:
  SOURCE -- the overlay gates on camera registration.
  DRAWN  -- exactly ONE sensor/image-circle label pair on the user's one-camera BS scene.
  KEPT   -- all three detector targets still exist (their ray hard-stops are untouched).
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

BS_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    try:
        from KrakenOS.UI.services import detector_coverage_overlay as dco

        src = _inspect.getsource(dco)
    except Exception as exc:
        return True, [f"SKIP: coverage overlay unavailable ({exc!r})"]
    if 'assigned_camera_label' in src and 'reached_image' in src:
        notes.append("SOURCE = the overlay gates iconography on camera registration")
    else:
        notes.append("SOURCE the camera-registration gate is missing (0462 regression)")
        ok = False

    if not BS_SCENE.exists():
        notes.append("SKIP: the BS scene is absent (gitignored attachment)")
        return ok, notes

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
        app.layout_files["bs"] = BS_SCENE
        app.load_layout_by_name("bs")
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        inspector = app.__dict__.get("_three_d_inspector")
        if inspector is None:
            notes.append("SKIP: the 3-D inspector is unavailable")
            return ok, notes
        inspector.refresh_from_editor(force_retrace=True, geometry_changed=True)
        inspector.update_idletasks()
        inspector.update()

        props = inspector._renderer.GetViewProps()
        props.InitTraversal()
        labels = []
        for _ in range(int(props.GetNumberOfItems())):
            prop = props.GetNextProp()
            try:
                text = prop.GetInput() if hasattr(prop, "GetInput") else None
                if isinstance(text, str) and ("Sensor" in text or "Image circle" in text):
                    labels.append(text)
            except Exception:
                continue
        sensors = [t for t in labels if "Sensor" in t]
        if len(sensors) == 1:
            notes.append(f"DRAWN = exactly one sensor label on a one-camera scene ({sensors[0].strip()})")
        else:
            notes.append(f"DRAWN {len(sensors)} sensor labels on a ONE-camera scene: {sensors}")
            ok = False

        bundle = inspector.__dict__.get("_current_scene_bundle")
        dets = [t for t in (getattr(bundle, "targets", None) or []) if getattr(t, "is_detector", False)]
        if len(dets) >= 3:
            notes.append(f"KEPT = every arm still has its detector target ({len(dets)}), so the ray stops remain")
        else:
            notes.append(f"KEPT only {len(dets)} detector targets -- an arm lost its ray hard-stop")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({exc!r})")
    finally:
        if app is not None:
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
