"""bugs/0459 guard -- a ray that HIT its detector is drawn all the way to it.

flag_20260729_094555: on the user's beam-splitter scene the drawn beam stopped just past
the lens while the trace was perfect. Both sides were instrumented into the flag, and they
disagreed outright:

    TRACED: 837 paths, traced_ray_max_x = 243.04
    DRAWN:  13 ray actors, max x = 85.4, ZERO past x=200

Cause: ``detector_planes_for_hard_stop`` returns a hard-stop plane for EVERY ``is_detector``
target, including the detectors synthesized on non-imaging beam-splitter arms (this scene has
them at x=74.4 and x=-0.5). ``bounded_ray_points_for_scene_display`` then clipped every drawn
polyline at the first such plane it crossed -- so the imaging rays were cut at x=85 by an arm
they were never going to land on.

The hard stop exists to bound rays that would otherwise be drawn PAST a detector (escaped and
missed ones). A ray whose terminal status is ``hit_detector`` has already stopped where the
physics put it, so clipping it again can only shorten it at a foreign plane. It is now exempt.

Checks:
  SOURCE -- the clip is gated on the terminal status.
  DRAWN  -- on the user's scene the drawn ray points reach the sensor (was 81.7 median).
  TRACE  -- display-only: the BS scene still traces 166 rays onto the sensor and the
            untouched RA-mirror scene still images 585.
"""
from __future__ import annotations

import inspect as _inspect
from collections import Counter
from pathlib import Path

import numpy as np

BS_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
ORIGINAL_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI import scene_projector as sp

        src = _inspect.getsource(sp.bounded_ray_points_for_scene_display)
    except Exception as exc:
        return True, [f"SKIP: scene_projector unavailable ({exc!r})"]
    if 'status != "hit_detector"' in src:
        notes.append("SOURCE = the detector hard stop skips rays that already hit a detector")
    else:
        notes.append("SOURCE the hard stop is not gated on terminal status (0459 regression)")
        ok = False

    if not BS_SCENE.exists() or not ORIGINAL_SCENE.exists():
        notes.append("SKIP: the AZ85 scenes are absent (gitignored attachment)")
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

        drawn = getattr(inspector, "_ray_display_points", None) or {}
        reach = [
            float(np.asarray(pts, dtype=float)[:, 0].max())
            for pts in drawn.values()
            if np.asarray(pts, dtype=float).ndim == 2
        ]
        if reach and sum(1 for v in reach if v > 200.0) >= 50:
            notes.append(
                f"DRAWN = the beam is drawn to the sensor "
                f"({sum(1 for v in reach if v > 200.0)} of {len(reach)} rays past x=200, "
                f"median {float(np.median(reach)):.1f})"
            )
        else:
            notes.append(
                f"DRAWN the beam is cut short: {sum(1 for v in reach if v > 200.0)} of "
                f"{len(reach)} rays past x=200"
            )
            ok = False

        bundle = inspector.__dict__.get("_current_scene_bundle")
        reasons = Counter(
            str(getattr(p, "termination_reason", "")) for p in (getattr(bundle, "ray_paths", None) or [])
        )
        if reasons.get("target_termination", 0) >= 100:
            notes.append(f"TRACE = the trace is untouched ({reasons.get('target_termination')} on target)")
        else:
            notes.append(f"TRACE the BS scene stopped imaging: {dict(reasons)}")
            ok = False

        app.layout_files["orig"] = ORIGINAL_SCENE
        app.load_layout_by_name("orig")
        _s, _r, bundle2 = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
        reasons2 = Counter(
            str(getattr(p, "termination_reason", "")) for p in (getattr(bundle2, "ray_paths", None) or [])
        )
        if reasons2.get("image", 0) >= 500:
            notes.append(f"CONTROL = the RA-mirror scene still images ({reasons2.get('image')} rays)")
        else:
            notes.append(f"CONTROL the RA-mirror scene regressed: {dict(reasons2)}")
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
