"""Guard for bugs/0595 — the sensor square must draw ONE edge, not two z-fighting ones.

Flag `flag_20260809_100904_100`: *"the sensor square edge is now split to 2 colors."*
With Quick Estimation AND the detector coverage overlay both on, TWO identical-size
squares drew at the sensor footprint — QE's recommended-sensor rect (yellow, 1.0/0.9/0.2)
and the coverage overlay's vendor sensor square (orange, 0.98/0.45/0.05) — coplanar to
z-fighting, so the rim alternated colours. Same masquerade class as bugs/0033: when the
labelled coverage geometry draws, a coincident unlabelled copy must not.

The diagnosis took three recordings because the recorder stored only merged per-row
bounds; the per-actor detail added for this bug (`row_actor_detail`) plus the recorded
OPACITIES ruled out the first hypothesis (the row-8 "duplicate" is the bugs/0033
suppressed disk at opacity 0.0 — invisible, innocent).

Checks:
  A  CONTRACT — the scene refresh threads ``suppress_image_plane_duplicates`` from
     ``detector_coverage_active`` into the QE overlay, the inspector wrapper forwards it
     (the bugs/0319 mixin-wrapper trap), and the QE service gates its image-plane
     circle + rect on it.
  B  REAL (skipped without the fixture scene) — with Det + QE both on, ZERO visible
     yellow QE rects and at least one coverage square at the sensor; with Det off, the
     QE yellow rect returns (QE undamaged).

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0595_sensor_square_single_edge
"""

from __future__ import annotations

import inspect
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"

QE_YELLOW = (1.0, 0.9, 0.2)
COVERAGE_ORANGE = (0.98, 0.45, 0.05)


def _visible_colour_counts(inspector) -> "tuple[int, int]":
    yellow = orange = 0
    for actor in (inspector._actor_by_key or {}).values():
        try:
            prop = actor.GetProperty()
            if not actor.GetVisibility() or float(prop.GetOpacity()) < 0.5:
                continue
            colour = tuple(round(float(c), 2) for c in prop.GetColor())
        except Exception:
            continue
        if colour == QE_YELLOW:
            yellow += 1
        elif colour == COVERAGE_ORANGE:
            orange += 1
    return yellow, orange


def run_checks():
    notes: list[str] = []
    ok = True

    # ---- A: source contracts --------------------------------------------------------
    from KrakenOS.UI.services import open3d_scene_refresh, quick_estimation_overlay
    from KrakenOS.UI import open3d_inspector as inspector_module

    refresh_src = inspect.getsource(open3d_scene_refresh)
    if "suppress_image_plane_duplicates=detector_coverage_active" not in refresh_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0595): the refresh no longer threads detector_coverage_active "
            "into the QE overlay — the two coincident squares are back"
        )
    else:
        notes.append("PASS: A1: the refresh threads the suppression from detector_coverage_active")
    wrapper_src = inspect.getsource(inspector_module.Kraken3DInspector._add_quick_estimation_overlays)
    if "suppress_image_plane_duplicates" not in wrapper_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0319 wrapper trap): the inspector wrapper drops the kwarg, so the "
            "refresh's suppression never reaches the QE service"
        )
    else:
        notes.append("PASS: A2: the inspector wrapper forwards the kwarg")
    qe_src = inspect.getsource(quick_estimation_overlay.QuickEstimationOverlayService.add_overlays)
    if "suppress_image_plane_duplicates" not in qe_src:
        ok = False
        notes.append("FAIL: A (bugs/0595): the QE service ignores the suppression flag")
    else:
        notes.append("PASS: A3: the QE service gates its image-plane duplicates")

    if not SCENE.exists():
        notes.append(f"SKIP: B: fixture scene missing ({SCENE})")
        return ok, notes

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = None
    try:
        app = KrakenLayoutEditor()
        app.layout_files["_0595"] = SCENE
        app.load_layout_by_name("_0595")
        # bugs/0587 pattern: late in the comprehensive marathon a further embedded
        # inspector cannot be opened ("Embedded 3D inspector unavailable") -- phase 454
        # died here on the first baseline carrying it while the standalone run passed.
        # The A contract checks above are the marathon teeth; the real-fixture B section
        # SKIPs rather than fails on a measurement that was never taken.
        try:
            inspector = _open_inspector(app)
        except Exception as exc:
            notes.append(
                f"SKIP: B: embedded inspector unavailable here ({type(exc).__name__}); "
                "run standalone for the real-fixture checks"
            )
            return ok, notes
        inspector.show_rays_var.set(False)
        inspector.show_detector_overlays_var.set(True)
        inspector.quick_estimation_var.set(True)
        try:
            inspector._quick_estimation_service().set_enabled(True)
        except Exception:
            pass
        inspector.refresh_from_editor(force_retrace=True)
        for _ in range(4):
            app.update()
            inspector.update()
        yellow_on, orange_on = _visible_colour_counts(inspector)
        if yellow_on:
            ok = False
            notes.append(
                f"FAIL: B (bugs/0595): with Det + QE on, {yellow_on} QE yellow rect(s) still "
                "draw at the sensor — the two-tone edge is back"
            )
        elif not orange_on:
            ok = False
            notes.append(
                "FAIL: B (non-vacuity): the coverage sensor square did not draw — suppressing "
                "QE while coverage draws nothing would leave the sensor unmarked"
            )
        else:
            notes.append(
                f"PASS: B1: Det+QE on -> 0 QE yellow rects, {orange_on} coverage square actor(s)"
            )
        inspector.show_detector_overlays_var.set(False)
        inspector.refresh_from_editor()
        for _ in range(4):
            app.update()
            inspector.update()
        yellow_off, _orange_off = _visible_colour_counts(inspector)
        if not yellow_off:
            ok = False
            notes.append(
                "FAIL: B (bugs/0595): with Det OFF the QE yellow rect is gone — the suppression "
                "over-fires and Quick Estimation lost its sensor rectangle"
            )
        else:
            notes.append(f"PASS: B2: Det off -> QE's yellow rect returns ({yellow_off})")
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
    print("Sensor-square single-edge validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
