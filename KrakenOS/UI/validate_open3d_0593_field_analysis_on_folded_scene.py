"""Guard for bugs/0593 — the field-aberration suite must MEASURE on a folded scene.

Flags `flag_20260809_094851_598` and `flag_20260809_131200_465` ("none of the overlays
work"): on the 0433-frozen folded Apo75 scene every field-aberration overlay returned None
and drew nothing, with numpy's "Mean of empty slice" as the only evidence. Root cause: BOTH
of the sampler's instruments were sequential — `Kos.PupilCalc` probes a chain whose row
order is not beam order (the splitter is row 6 yet physically first), and the analysis
chunk traces specs with no built solids, so even the axial ray landed nothing.

The fix is the WORLD-ORDER launch: geometric launch bundles, traced through the REAL
solids-built system (`_trace_preview_bundles`), landing by terminal-segment intersection
with the detector plane resolved by `row_placement.world_frame`, self-calibrated by tracing
(acceptance ring probes + entrance-pupil edge bisection), with dominant-cluster rejection
of ghost families.

Checks (display-free):
  A  the fixture is genuinely a world-placed chain (else the guard is vacuous);
  B  the field scan yields data: >= half the fields land, focus finite, image heights
     strictly increasing, ZERO numpy empty-slice warnings;
  C  all three overlay specs are non-None and the best-focus surface is placed in WORLD
     (centroid within 2 mm of the traced anchor) — measuring in a substitute frame and
     drawing in world was the rejected straight-equivalent failure mode;
  D  CONTRACT: the sampler carries the world-order branch gated on the placement predicate
     (a revert to PupilCalc-only fails here even without the fixture);
  E  the spot RMS map produces a real multi-field map (the phase-317 quantity, whose
     sequential-probe version was environment-sensitive).

The scene fixture is the user's real attachment scene (`feedback_general_not_special_case`:
validate on the real scenes); absent (a fresh GitHub checkout), A/B/C/E SKIP and D still
bites.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0593_field_analysis_on_folded_scene
"""

from __future__ import annotations

import inspect
import warnings
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"


def run_checks():
    notes: list[str] = []
    ok = True

    # ---- D: source contract (independent of the fixture) ---------------------------
    from KrakenOS.UI.services.geometric_analysis import GeometricAnalysisMixin

    sampler_src = inspect.getsource(GeometricAnalysisMixin._build_geometric_image_samples_full)
    if "_world_placed_chain_rows" not in sampler_src or "_world_order_trace_landings" not in sampler_src:
        ok = False
        notes.append(
            "FAIL: D (bugs/0593): the sampler lost its world-order branch — folded scenes "
            "are back on the sequential PupilCalc probe that lands nothing"
        )
    else:
        notes.append("PASS: D: the sampler routes world-placed chains to the world-order launch")
    try:
        landings_src = inspect.getsource(GeometricAnalysisMixin._world_order_trace_landings) + inspect.getsource(
            GeometricAnalysisMixin._world_detector_plane
        )
    except AttributeError:
        landings_src = ""  # the world-order machinery is gone entirely -> the check below FAILs
    if "world_frame" not in landings_src:
        ok = False
        notes.append(
            "FAIL: D (bugs/0593): landings no longer use the row_placement resolver — the "
            "hand-rolled detector plane is how five consumers each got a frozen scene wrong"
        )
    else:
        notes.append("PASS: D: landings intersect the row_placement-resolved detector plane")

    if not SCENE.exists():
        notes.append(f"SKIP: A/B/C/E: fixture scene missing ({SCENE})")
        return ok, notes

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    import KrakenOS as Kos

    app = None
    try:
        app = KrakenLayoutEditor()
        app.layout_files["_0593"] = SCENE
        app.load_layout_by_name("_0593")
        wavelength = float(app._current_wavelength())

        # ---- A: the fixture is a world-placed chain --------------------------------
        world_rows = app._world_placed_chain_rows()
        if not world_rows:
            ok = False
            notes.append(
                "FAIL: A (non-vacuity): the fixture scene has no world-placed rows — the "
                "world-order branch never engages and B/C/E prove nothing"
            )
            return ok, notes
        notes.append(f"PASS: A: rows {world_rows} carry world placement (folded/frozen chain)")

        # ---- B: the scan measures ---------------------------------------------------
        service = app._analysis_plot_service()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            sampled = service._sample_field_curvature_distortion(app.build_system(), wavelength)
        empty_warns = sum(
            1
            for w in caught
            if "empty slice" in str(w.message) or "invalid value" in str(w.message)
        )
        if not sampled:
            ok = False
            notes.append("FAIL: B (bugs/0593): the field scan measured NOTHING on the folded scene")
            return ok, notes
        axis_results, _field_type, _field_limit = sampled
        y_axis = axis_results.get("Y") or {}
        fields = np.asarray(y_axis.get("fields", []), dtype=float)
        focus = np.asarray(y_axis.get("focus", []), dtype=float)
        heights = np.asarray(y_axis.get("image_height", []), dtype=float)
        if fields.size < 11:
            ok = False
            notes.append(
                f"FAIL: B: only {fields.size} field samples landed (the mis-aimed launch "
                "starved beyond ~1/3 field; a healthy scan lands the full sweep)"
            )
        elif not np.all(np.isfinite(focus)):
            ok = False
            notes.append("FAIL: B: the focus curve carries non-finite samples")
        elif heights.size >= 3 and not np.all(np.diff(np.abs(heights)) > -1.0e-6):
            ok = False
            notes.append("FAIL: B: image heights are not monotonic in field — the landing frame is wrong")
        elif empty_warns:
            ok = False
            notes.append(f"FAIL: B: {empty_warns} numpy empty-slice warnings — the silent-NaN mode is back")
        else:
            notes.append(
                f"PASS: B: {fields.size} fields land, focus finite "
                f"(span {np.max(focus) - np.min(focus):.4g} mm), heights monotonic, 0 warnings"
            )

        # ---- C: the three overlays produce, placed in WORLD ------------------------
        system = app.build_system(require_solids=True)
        rays = Kos.raykeeper(system)
        max_radius = max((max(r.diameter / 2.0, 0.5) for r in app.rows), default=1.0)
        app._trace_preview_rays(
            system, rays, wavelength, max_radius, allow_full_pupil=True,
            sampling_mode=app._preview_2d_sampling_mode(),
        )
        bundle = app._build_scene_bundle(system, rays, max_radius)
        anchor = app._best_focus_surface_anchor_target(bundle)
        specs = {
            "best_focus": app.best_focus_surface_overlay_spec(system, bundle, wavelength=wavelength),
            "distortion": app.distortion_grid_overlay_spec(system, bundle, wavelength=wavelength),
            "astigmatism": app.astigmatism_surfaces_overlay_spec(system, bundle, wavelength=wavelength),
        }
        missing = [name for name, spec in specs.items() if not spec]
        if missing:
            ok = False
            notes.append(f"FAIL: C (bugs/0593): overlay spec(s) still None on the folded scene: {missing}")
        else:
            notes.append("PASS: C1: best-focus, distortion and astigmatism specs all produce")
        best_focus = specs.get("best_focus")
        if best_focus and anchor is not None:
            points = np.asarray(best_focus.get("points", []), dtype=float)
            centre = np.asarray(getattr(anchor, "center_world"), dtype=float)
            if points.ndim == 2 and points.size:
                drift = float(np.linalg.norm(points.mean(axis=0) - centre))
                if not np.isfinite(points).all():
                    ok = False
                    notes.append("FAIL: C: the best-focus surface carries non-finite points")
                elif drift > 2.0:
                    ok = False
                    notes.append(
                        f"FAIL: C (the bugs/0576 class): the bowl is {drift:.2f} mm from the "
                        "traced anchor — measured in one frame, drawn in another"
                    )
                else:
                    notes.append(f"PASS: C2: the bowl is placed in world ({drift:.3f} mm from the anchor)")

        # ---- E: the spot RMS map (the phase-317 quantity) --------------------------
        spot = app._compute_spot_field_map_spec(system, anchor, wavelength, None)
        circles = len((spot or {}).get("circles", []) or [])
        if circles < 2:
            ok = False
            notes.append(f"FAIL: E: the spot RMS map is not a multi-field map (circles={circles})")
        else:
            notes.append(f"PASS: E: the spot RMS map produces {circles} field circles")
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
    print("Folded-scene field-analysis validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
