"""bugs/0551 generality sweep -- the escaped-ray display tail across the REAL scenes.

The fix changes ONE scene-relative number (``_ESCAPED_TAIL_SCENE_RADIUS_FACTOR``, 1.25 ->
0.40), so it must be judged on more than the scene that flagged it. For every layout given,
this traces once and reports, for the old factor and the new one:

* TRACED max |x| -- what the physics actually produced (never changes; display-only fix)
* DRAWN  max |x| -- what the renderer puts on screen
* the OVERSHOOT, drawn - traced: how far past the physics the display runs

A scene is HEALTHY when the overshoot is small; the bug is a large positive overshoot. The
fix must shrink big overshoots WITHOUT changing scenes that were already fine (small scenes
sit on the 75 mm floor, which neither factor moves).

HARNESS LIMIT: only the FIRST scene in a process gets an embedded 3-D inspector ("3D inspector
did not open" on the rest), so sweep additional scenes one per process:

    for s in attachment/machine_vision_*.py; do xvfb-run -a python bugs/diag_0551_escape_tail_sweep.py "$s"; done

NOTE the stronger argument lives in the GUARD (validate_open3d_0551_escape_tail_bounded): the
tail is `max(75, min(radius*f, 600))`, monotone in f, so lowering f cannot lengthen ANY scene's
tail at any size. This sweep corroborates that on real geometry; it does not carry the proof.

Run:  xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0551_escape_tail_sweep.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Each scene costs a full app launch + two 3-D traces (~4 min), so the default list is short
# and every line is flushed as it is produced -- a sweep that runs out of time still leaves the
# scenes it finished (the first attempt was piped through `tail` and a timeout lost everything).
# Pass scene paths as arguments to sweep others.
SCENES = sys.argv[1:] or [
    "attachment/machine_vision_AZ85_RA_Mirror_BS.py",
    "attachment/machine_vision_AZ85_RA_Mirror.py",
    "attachment/machine_vision_150mm_test.py",
]

FACTORS = (("old 1.25", 1.25), ("new 0.40", 0.40))


def _drawn_max_abs_x(insp) -> float | None:
    best = None
    try:
        props = insp._renderer.GetViewProps()
        props.InitTraversal()
        for _ in range(int(props.GetNumberOfItems())):
            prop = props.GetNextProp()
            try:
                if not bool(prop.GetVisibility()):
                    continue
                mapper = prop.GetMapper()
                data = mapper.GetInput() if mapper is not None else None
                if data is None or int(getattr(data, "GetNumberOfLines", lambda: 0)()) <= 0:
                    continue
                bounds = [float(v) for v in prop.GetBounds()]
                if any(bounds[i] > bounds[i + 1] for i in (0, 2, 4)):
                    continue
                value = max(abs(bounds[0]), abs(bounds[1]))
                best = value if best is None else max(best, value)
            except Exception:
                continue
    except Exception:
        return None
    return best


def _traced_max_abs_x(insp) -> float | None:
    bundle = insp.__dict__.get("_current_scene_bundle")
    best = None
    for path in list(getattr(bundle, "ray_paths", None) or []):
        pts = getattr(path, "points_world", None)
        if pts is None:
            continue
        try:
            value = max(abs(float(p[0])) for p in pts)
        except Exception:
            continue
        best = value if best is None else max(best, value)
    return best


def main() -> int:
    _flush = lambda: sys.stdout.flush()
    from KrakenOS.UI import scene_projector
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import three_d_scene_tools

    shipped = float(scene_projector._ESCAPED_TAIL_SCENE_RADIUS_FACTOR)
    original = scene_projector.bounded_ray_points_for_scene_display
    factor = {"value": shipped}

    def scaled(points, center, radius, **kwargs):
        # The tail is `radius * shipped`, so scaling the radius by (want / shipped)
        # reproduces any factor without touching the shipped constant.
        return original(points, center, float(radius) * (factor["value"] / shipped), **kwargs)

    scene_projector.bounded_ray_points_for_scene_display = scaled
    three_d_scene_tools.bounded_ray_points_for_scene_display = scaled

    print(f"shipped factor = {shipped}")
    print(f"\n{'scene':<46}{'factor':>10}{'traced':>10}{'drawn':>10}{'overshoot':>11}")
    failures: list[str] = []
    try:
        for scene in SCENES:
            path = Path(scene)
            if not path.exists():
                print(f"{path.name:<46}  (missing, skipped)")
                continue
            app = KrakenLayoutEditor()
            try:
                app.layout_files["sweep"] = path
                app.load_layout_by_name("sweep")
                insp = _open_3d_inspector(app)
                app._three_d_inspector = insp
                measured = {}
                for label, value in FACTORS:
                    factor["value"] = value
                    app._invalidate_preview_scene_trace()
                    insp.refresh_from_editor(
                        sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True
                    )
                    _settle(insp)
                    traced = _traced_max_abs_x(insp)
                    drawn = _drawn_max_abs_x(insp)
                    over = None if (traced is None or drawn is None) else drawn - traced
                    measured[label] = (traced, drawn, over)
                    print(
                        f"{path.name if label == FACTORS[0][0] else '':<46}"
                        f"{label:>10}"
                        f"{('-' if traced is None else f'{traced:.1f}'):>10}"
                        f"{('-' if drawn is None else f'{drawn:.1f}'):>10}"
                        f"{('-' if over is None else f'{over:+.1f}'):>11}"
                    )
                    _flush()
                old = measured.get("old 1.25", (None, None, None))
                new = measured.get("new 0.40", (None, None, None))
                if old[2] is not None and new[2] is not None:
                    # The fix must never make the overshoot WORSE on any scene.
                    if new[2] > old[2] + 1e-6:
                        failures.append(
                            f"{path.name}: overshoot grew {old[2]:+.1f} -> {new[2]:+.1f}"
                        )
                    # And it must never shorten a ray below what the physics traced.
                    if new[1] is not None and new[0] is not None and new[1] < new[0] - 1e-6:
                        failures.append(
                            f"{path.name}: drawn {new[1]:.1f} < traced {new[0]:.1f} -- the fix "
                            "must bound the display TAIL, never clip real traced geometry"
                        )
            except Exception as exc:
                print(f"{path.name:<46}  (failed: {type(exc).__name__}: {exc})")
            finally:
                try:
                    app.destroy()
                except Exception:
                    pass
    finally:
        scene_projector.bounded_ray_points_for_scene_display = original
        three_d_scene_tools.bounded_ray_points_for_scene_display = original

    print()
    if failures:
        print("GENERALITY CHECK FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("GENERALITY CHECK PASSED: no scene's overshoot grew, and no scene draws short of its trace.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
