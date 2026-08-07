"""Guard for bugs/0580 + 0581 + 0582 -- the morning-of-2026-08-07 recording (8-flag arc, flags
072907/073042/073242/073438): a pinned FOV solve must leave LEGAL bookkeeping, and the machine
must survive the next lens swap with every element still on its leg.

The recorded sequence, replayed exactly: load Apo75 -> swap PYRITE -> fov_solve 55x55 +
image pin ("far", 30) -> swap ELS-85 -> fov_solve 23x23 (no pin) -> remove defocus.

What used to happen: the pin's far-row write was raw, booking rows[7].thickness = -5.0269 (a
negative frozen gap -- the known off-axis poison) while the world re-bake made the scene LOOK
right. The next swap detonated it: the normaliser re-pinned the station-neutral BS row, the
evaporating bookkeeping sheared the followers, and the RA prism ended 5.03 mm OFF its leg with
the user manually dragging elements to repair it (flags 073438, 074450, 075626, 075933).

Checks, each on the REAL scene at every stage of the replay:
  A LEGAL    no row thickness is ever negative, and station-neutral rows stay at 0 (bugs/0435,
             0569's doctrine: no conjugate write lands on a station-neutral row).
  B ON-LEG   the RA prism stays ON its fold leg (world z within tolerance of its seat), and the
             ELS swap does not move it (bugs/0581: no shear back to a stale seat).
  C ALIVE    rays land on the sensor at every stage (never 0 -- the wrecked states traced dead).
  D HONEST   remove-defocus either moves the sensor or refuses with a message; never silent.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0580_pinned_solve_survives_swap
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
PYRITE = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"
ELS85 = PROJECT_ROOT / "attachment" / "Lens" / "ELS-85-4.5V16K"

PRISM_ROW = 7
LEG_Z_TOL_MM = 1.0


def _ray_hits(app) -> int:
    try:
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
    except Exception:
        return -1
    return sum(
        1
        for p in list(getattr(bundle, "ray_paths", None) or [])
        if str(getattr(p, "termination_reason", "")) == "target_termination"
    )


def _prism_world(app):
    from KrakenOS.UI.services import row_placement

    return np.asarray(row_placement.world_pose(app, PRISM_ROW).position, dtype=float)


def _neutral_rows(app):
    from KrakenOS.UI.services.paraxial_tools import row_is_station_neutral

    return [i for i, r in enumerate(app.rows) if row_is_station_neutral(r)]


def _stage_checks(app, tag, ok, notes, leg_z, *, min_rays=1):
    thicknesses = [float(getattr(r, "thickness", 0.0) or 0.0) for r in app.rows]
    worst = min(thicknesses)
    if worst < -1e-6:
        ok[0] = False
        notes.append(f"FAIL: A[{tag}]: negative thickness {worst:.4f} at row {thicknesses.index(worst)}")
    else:
        notes.append(f"PASS: A[{tag}]: no negative gap (min thickness {worst:+.4f})")
    bad_neutral = [i for i in _neutral_rows(app) if abs(thicknesses[i]) > 1e-6]
    if bad_neutral:
        ok[0] = False
        notes.append(f"FAIL: A[{tag}]: station-neutral row(s) {bad_neutral} carry thickness")
    prism = _prism_world(app)
    if abs(float(prism[2]) - leg_z) > LEG_Z_TOL_MM:
        ok[0] = False
        notes.append(f"FAIL: B[{tag}]: prism z {prism[2]:.4f} is off its leg (seat {leg_z:.4f})")
    else:
        notes.append(f"PASS: B[{tag}]: prism on its leg (z {prism[2]:.4f})")
    hits = _ray_hits(app)
    if hits < min_rays:
        ok[0] = False
        notes.append(f"FAIL: C[{tag}]: only {hits} rays land (want >= {min_rays})")
    else:
        notes.append(f"PASS: C[{tag}]: {hits} rays land")
    return prism


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = [True]
    for path, what in ((SCENE, "scene"), (PYRITE, "PYRITE lens"), (ELS85, "ELS-85 lens")):
        if not path.exists():
            notes.append(f"SKIP: the {what} is absent (gitignored attachment)")
            return True, notes

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        app = KrakenLayoutEditor()
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        inspector = _open_inspector(app)
        qe = inspector._quick_estimation_service()
        leg_z = float(_prism_world(app)[2])

        app.swap_imaging_lens_from_folder(str(PYRITE), refresh=False)
        _stage_checks(app, "pyrite swap", ok, notes, leg_z)

        solved, _msg = qe.fov_solve("object", "thickness", 55.0, 55.0, None)
        pin_ok, pin_msg = app._apply_folded_image_split("far", 30.0)
        app._sync_table()  # the inspector layer's post-command sync, replayed faithfully
        if not (solved and pin_ok):
            ok[0] = False
            notes.append(f"FAIL: the 55x55 + far=30 pin did not apply ({_msg} / {pin_msg})")
            return ok[0], notes
        notes.append("PASS: the 55x55 solve + far=30 pin applies")
        prism_after_pin = _stage_checks(app, "55x55+pin", ok, notes, leg_z)

        app.swap_imaging_lens_from_folder(str(ELS85), refresh=False)
        prism_after_swap = _stage_checks(app, "ELS swap", ok, notes, leg_z)
        moved = float(np.linalg.norm(prism_after_swap - prism_after_pin))
        if moved > 0.5:
            ok[0] = False
            notes.append(f"FAIL: B2 (bugs/0581): the ELS swap moved the prism {moved:.4f} mm "
                         f"(it sheared back to a stale seat)")
        else:
            notes.append(f"PASS: B2 (bugs/0581): the ELS swap left the prism seated ({moved:.4f} mm)")

        solved23, msg23 = qe.fov_solve("object", "thickness", 23.0, 23.0, None)
        app._sync_table()
        if not solved23:
            # bugs/0582's contiguity refusal would land here -- on a healthy replay the solve
            # must APPLY (the object side always fits; the image side may defer to the budget).
            ok[0] = False
            notes.append(f"FAIL: the 23x23 solve was refused on a healthy scene ({msg23})")
        else:
            notes.append(f"PASS: the 23x23 solve applies ({str(msg23)[:70]})")
        _stage_checks(app, "23x23", ok, notes, leg_z)

        before = _prism_world(app).copy()
        moved_flag = False
        try:
            moved_flag = bool(app.snap_detector_to_image_plane())
        except Exception as exc:
            ok[0] = False
            notes.append(f"FAIL: D: remove defocus raised {type(exc).__name__}: {exc}")
        status = str(app.status_var.get() or "")
        if moved_flag or status.strip():
            notes.append(f"PASS: D: remove defocus is honest (moved={moved_flag}; '{status[:70]}')")
        else:
            ok[0] = False
            notes.append("FAIL: D: remove defocus did nothing and said nothing")
        drift = float(np.linalg.norm(_prism_world(app) - before))
        if drift > 0.5:
            ok[0] = False
            notes.append(f"FAIL: D2: remove defocus moved the PRISM {drift:.4f} mm")
        else:
            notes.append("PASS: D2: remove defocus never moves the prism")
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
    print("Pinned-solve-survives-swap validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
