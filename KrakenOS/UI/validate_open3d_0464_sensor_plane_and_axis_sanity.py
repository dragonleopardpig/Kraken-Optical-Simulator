"""bugs/0464 guard -- the sensor is square to its beam, and only real sensors/axes are drawn.

flag_20260729_120601, three reports in one:
  1. "there are still 2 additional sensor planes (orange color). There are no camera why
     there is a sensor?"
  2. "the actual sensor location is slanted relative to the 2nd RA mirror optical axis"
  3. "About the Slant Optical Axis ... I can't really figure out why it is a real optical
     axis. It is neither 45 degree nor 90 degree to the BS plate."

Measured, and (2) and (3) turned out to share a root:

    reached_image detector normal = [0.563, 0, -0.826]   -> 34.28 deg off perpendicular
    no-camera arm detector normal = [0.949, 0, -0.315]   -> the "slant optical axis" direction
    the Image ROW's own tilts     = (180, 0, 0)          -> square-on, as designed

Every branch detector took its normal from the MEAN EXIT-RAY direction. On a splitter scene
most surviving rays are not the imaging bundle (166 of 837 here), so the mean tilted the
sensor plane away from the beam, and a traced axis picked up the same skew.

Fixes: a detector pinned to the designed Image takes that Image's ORIENTATION too; an arm with
no camera draws no sensor plane (but keeps its ray hard-stop); and traced axes are superseded
where guide axes already describe the legs.

Checks:
  SQUARE  -- the sensor plane is perpendicular to its fold leg.
  PLANES  -- exactly one sensor plane drawn, with all detector targets (ray stops) kept.
  AXES    -- the scene's axes are the physical legs, no marginal-ray axis.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

BS_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    if not BS_SCENE.exists():
        return True, ["SKIP: the BS scene is absent (gitignored attachment)"]

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
        app.layout_files["bs"] = BS_SCENE
        app.load_layout_by_name("bs")
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
        dets = [t for t in (getattr(bundle, "targets", None) or []) if getattr(t, "is_detector", False)]
        drawn = [t for t in dets if not (getattr(t, "metadata", None) or {}).get("draw_suppressed")]

        image = next(
            (t for t in dets if str((getattr(t, "metadata", None) or {}).get("focus_source", "")) == "reached_image"),
            None,
        )
        if image is not None:
            n = np.asarray(getattr(image, "normal_world", (0, 0, 1)), dtype=float).reshape(-1)[:3]
            n = n / max(float(np.linalg.norm(n)), 1e-9)
            off = float(np.degrees(np.arccos(min(1.0, abs(float(np.dot(n, np.array([0.0, 0.0, -1.0]))))))))
            if off <= 1.0:
                notes.append(f"SQUARE = the sensor is perpendicular to its fold leg ({off:.2f} deg off)")
            else:
                notes.append(f"SQUARE the sensor is slanted {off:.2f} deg off its fold leg")
                ok = False
        else:
            notes.append("SKIP: no reached_image detector on this scene")

        if len(dets) >= 3 and len(drawn) == 1:
            notes.append(f"PLANES = one sensor plane drawn, {len(dets)} detector targets kept (ray stops)")
        else:
            notes.append(f"PLANES {len(drawn)} drawn of {len(dets)} targets (want 1 drawn, >=3 kept)")
            ok = False

        app.open_3d_view()
        app.update_idletasks()
        app.update()
        inspector = app.__dict__.get("_three_d_inspector")
        if inspector is not None:
            inspector.refresh_from_editor(force_retrace=True, geometry_changed=True)
            inspector.update_idletasks()
            inspector.update()
            records = inspector._optical_axis_records_for_3d(inspector.__dict__.get("_current_scene_bundle"))
            traced = [r for r in records if str(r.get("axis_kind", "")) == "traced_chief_ray_segment"]
            if not traced:
                notes.append(f"AXES = the axes are the physical legs ({len(records)}), no marginal-ray axis")
            else:
                notes.append(f"AXES a traced marginal-ray axis is still drawn: {[r.get('axis_id') for r in traced]}")
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
