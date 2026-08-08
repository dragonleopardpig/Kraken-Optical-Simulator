"""Guard for bugs/0574 + 0575 + 0576 -- the three defects behind flag_20260806_182735
("changed FOV, lens body detached from surrogate, rays defocus at sensor").

A  the lens BODY rides its surrogate through a SOLVE, not only through a drag (bugs/0574).
   The drag has been guarded since phase 421 (validate_open3d_0524, "the STEP body must ride the
   assembly"); the solve had no equivalent, which is exactly why 0571 could ship with the barrel
   pinned. The assertion is the same one, restated for the solve, and it is checked against the
   drag as a control so a future divergence shows up as an inequality rather than as a number
   nobody can judge.

B  a frozen-fold image refusal never falls through to the inverted plain write (bugs/0575).
   apply_image_distance_frozen_aware returning False must be distinguishable: "not a frozen scene"
   (empty _frozen_image_write_refusal, the caller may do its plain write) versus "frozen, out of
   reach" (a refusal string, the caller must not).

C  best focus is measured in the frame the scene actually lives in (bugs/0576).
   On a 0433-frozen fold the straight-equivalent measure reported a 69 mm defocus as 3.06e-14, so
   the snap declined to move. Checked by SCANNING the sensor along its leg and reading the real
   traced spot RMS -- the estimator is judged against an observation, not against the other
   estimator.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0574_solve_carries_the_lens_body
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
LENS_FOLDER = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"

ATTACH_TOL_MM = 0.05          # the phase-421 drag tolerance, reused verbatim
SLIDE_MM = 28.4622            # the slide the user's 23x23 solve asks for on this scene


def _body_centre(app):
    try:
        mesh = app._transformed_imported_step_mesh_for_label("lens")
    except Exception:
        return None
    if mesh is None:
        return None
    b = np.asarray(mesh.bounds, dtype=float)
    return np.array([(b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0], dtype=float)


def _datum_mid(app):
    try:
        mid = app._lens_surrogate_datum_mid_world()
    except Exception:
        return None
    return None if mid is None else np.asarray(mid, dtype=float).reshape(3)


def _attach_err(before, after):
    """|body motion - surrogate motion|, the phase-421 assertion."""
    if any(v is None for v in before + after):
        return None
    (b0, d0), (b1, d1) = (before[0], before[1]), (after[0], after[1])
    return float(np.linalg.norm((b1 - b0) - (d1 - d0)))


def _snapshot(app):
    return (_body_centre(app), _datum_mid(app))


def _axial_spot_rms(app):
    """Real traced axial spot RMS at the detector, on the scene as it stands (world frame)."""
    try:
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
    except Exception:
        return None
    launches, ends = [], []
    for path in list(getattr(bundle, "ray_paths", None) or []):
        if str(getattr(path, "termination_reason", "")) != "target_termination":
            continue
        pts = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        launches.append(pts[0, :3])
        ends.append(pts[-1, :3])
    if len(ends) < 4:
        return None
    # Axial field picked RELATIVE TO THE OBJECT ROW -- this scene's object is not at the origin.
    try:
        stations = app._row_z_positions()
        row0 = app.rows[0]
        obj = np.array(
            [float(row0.desp_x), float(row0.desp_y), float(stations[0]) + float(row0.desp_z)],
            dtype=float,
        )
    except Exception:
        obj = np.zeros(3, dtype=float)
    launches = np.asarray(launches, dtype=float)
    offsets = np.linalg.norm(launches - obj, axis=1)
    nearest = float(np.min(offsets))
    keep = offsets <= nearest + max(1.0e-3, 0.02 * float(np.max(offsets) - nearest))
    arr = np.asarray(ends, dtype=float)[keep]
    if arr.shape[0] < 4:
        return None
    return float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean()))


def _check_b_pure(ok, notes):
    """bugs/0575: the frozen writer's refusal must be distinguishable from 'not frozen'."""
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin
    import inspect

    src = inspect.getsource(ParaxialToolsMixin.apply_image_distance_frozen_aware)
    if "_frozen_image_write_refusal" in src:
        notes.append("PASS: B1: the frozen image writer reports WHY it refused, not just that it did")
    else:
        ok[0] = False
        notes.append("FAIL: B1: apply_image_distance_frozen_aware has no refusal channel -- an "
                     "out-of-reach request is indistinguishable from an unfolded scene")

    caller = inspect.getsource(
        __import__("KrakenOS.UI.services.quick_estimation", fromlist=["QuickEstimationService"])
        .QuickEstimationService._apply_conjugate_pair
    )
    if "_frozen_image_write_refusal" in caller and "image_deferred" in caller:
        notes.append("PASS: B2: the folded solve keys on the refusal STRING and defers the sensor "
                     "to the traced focus rather than doing the inverted plain write")
    else:
        ok[0] = False
        notes.append("FAIL: B2: the folded solve still treats False as 'not frozen' -- bugs/0478's "
                     "inversion can re-enter through the refusal path")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = [True]

    _check_b_pure(ok, notes)

    if not SCENE.exists() or not LENS_FOLDER.exists():
        notes.append("SKIP: the Apo75 scene or the PYRITE lens folder is absent (gitignored attachment)")
        return ok[0], notes

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        app = KrakenLayoutEditor()
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        # bugs/0587: inside the comprehensive marathon a SECOND embedded inspector cannot be
        # opened ("Embedded 3D inspector unavailable"), and these guards used to die there --
        # invisible until 0587 wired them into the run list. Standalone they keep the full
        # strength (inspector open, rays measured); in-marathon they fall back to driving the
        # service directly, exactly as phase 448's guard does, and the ray-dependent assertions
        # SKIP rather than fail on a measurement that was never taken.
        inspector = None
        try:
            inspector = _open_inspector(app)
        except Exception as exc:
            notes.append(f"NOTE: no embedded inspector here ({type(exc).__name__}); "
                         f"ray-count checks will SKIP")
        if inspector is not None:
            qe = inspector._quick_estimation_service()
        else:
            from types import SimpleNamespace

            from KrakenOS.UI.services.quick_estimation import QuickEstimationService

            qe = QuickEstimationService(SimpleNamespace(editor=app))
        if inspector is None:
            # bugs/0587: this is a REAL-SCENE guard -- it swaps lenses and judges the result by
            # traced rays and best focus. Without an embedded inspector the preview bundle comes
            # back with ZERO landed rays (not an error), and the swap's auto-refocus then takes
            # its no-bundle fallback, so every downstream number describes the degraded context
            # rather than the product. Skipping is honest; asserting here would manufacture
            # failures (measured: "prism moved 0.7394 mm" was purely this). The full guard runs
            # standalone, which is how it is verified.
            notes.append("SKIP: real-scene checks need an embedded inspector; run this guard "
                         "standalone (python -m KrakenOS.UI.%s)" % __name__.rsplit(".", 1)[-1])
            return ok[0], notes
        app.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)

        # ---------------------------------------------------------------- C: the measure frame
        split = app._folded_image_conjugate_split() or {}
        far_row = int(split.get("far_gap_row", len(app.rows) - 2))
        geometry = app._frozen_image_fold_world_geometry(split)
        far_now = float(geometry["far"])
        const = float(app.rows[far_row].thickness) + far_now

        world = app._traced_bundle_best_focus_shift()
        if world is not None and abs(float(world)) <= 5.0:
            notes.append(f"PASS: C1: after the swap the sensor sits at the TRACED focus "
                         f"(residual {float(world):+.4g} mm; it was -71.04 before the fix)")
        else:
            ok[0] = False
            notes.append(f"FAIL: C1: the swap left the sensor off best focus (residual {world})")

        # The observation the estimator is judged against: scan the leg, read the real spot.
        best_far, best_rms = None, None
        for far in np.linspace(max(2.0, far_now - 40.0), min(const - 2.0, far_now + 40.0), 9):
            app.rows[far_row].thickness = const - float(far)
            app._invalidate_preview_scene_trace()
            rms = _axial_spot_rms(app)
            if rms is None:
                continue
            if best_rms is None or rms < best_rms:
                best_far, best_rms = float(far), float(rms)
        app.rows[far_row].thickness = const - far_now
        app._invalidate_preview_scene_trace()

        if best_far is None:
            notes.append("SKIP: C2: no usable axial bundle to scan on this run")
        elif abs(best_far - far_now) <= 6.0:
            notes.append(f"PASS: C2 (the observation): the scanned spot minimum is where the swap "
                         f"put the sensor (best far {best_far:.3f} vs sensor {far_now:.3f} mm, "
                         f"RMS {best_rms:.4f} mm; pre-fix the sensor was 69 mm away)")
        else:
            ok[0] = False
            notes.append(f"FAIL: C2: the real spot minimum is at far {best_far:.3f} mm but the "
                         f"sensor is at {far_now:.3f} mm")

        # ---------------------------------------------------------------- A: the SOLVE carry
        before = _snapshot(app)
        solved, message = qe.fov_solve(
            "object", "thickness", 23.0, 23.0, None
        )
        if not solved:
            ok[0] = False
            notes.append(f"FAIL: A0: the 23x23 solve was refused, cannot exercise the carry ({message})")
            return ok[0], notes
        notes.append(f"PASS: A0: the 23x23 object solve runs ({str(message)[:90]})")
        after = _snapshot(app)
        moved = None if after[1] is None or before[1] is None else float(
            np.linalg.norm(after[1] - before[1])
        )
        if moved is None or moved < 1.0:
            ok[0] = False
            notes.append(f"FAIL: A1 (non-vacuity): the solve did not move the surrogate ({moved})")
            return ok[0], notes
        notes.append(f"PASS: A1 (non-vacuity): the solve moved the lens surrogate {moved:.4f} mm")

        err = _attach_err(before, after)
        if err is None:
            notes.append("SKIP: A2: no lens STEP body on this scene")
        elif err <= ATTACH_TOL_MM:
            notes.append(f"PASS: A2 (the bug): the lens BODY rode its surrogate through the solve "
                         f"(attach_err {err:.6f} mm; it was {moved:.4f} mm -- fully pinned -- before the fix)")
        else:
            ok[0] = False
            notes.append(f"FAIL: A2: the lens body detached from its surrogate (attach_err {err:.6f} mm)")
    except Exception as exc:  # pragma: no cover - harness failure, not a product failure
        ok[0] = False
        notes.append(f"FAIL: harness error {type(exc).__name__}: {exc}")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok[0], notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Solve-carries-the-lens-body validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
