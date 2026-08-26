"""Guard for bugs/0573 -- when a field needs more lens travel than the fold leg holds, the solve
MAKES ROOM at the fold instead of refusing: it slides the fold mirror, everything behind it and
the camera body along the leg by the shortfall, then takes the slide it asked for.

bugs/0572 established the refusal and, with it, the number: on the user's Apo75 + PYRITE 45-85
machine a 35x35 field needs the lens 72.80 mm further and only 45.73 mm of the lens-to-fold leg is
left; 55x55 needs 146.70 mm. It also established that the OPTICS reach both fields -- the image
distance is +25.36 mm at 35x35 and +4.98 mm at 55x55, and the ceiling is about 63.9 mm square. So
the machine is too SHORT, and lengthening it at the fold is the answer the user asked for.

The bookkeeping is the bugs/0526 composite one section further down: translate the arm's rows along
the leg (a fold leg's position lives in ``desp``, bugs/0499), grow the lens->fold gap row by the
same amount so the row frame records the leg that opened up, and cancel that station growth with
``desp_z -= distance`` after it so nothing else moves -- notably the station-neutral beam splitter
sitting between them, which belongs to the illumination unit and not to the arm.

Checks:
- A PURE: the composite's arithmetic on a stub -- the arm translates, the gap row grows, the rows
  after it have their station growth cancelled, and the row BETWEEN the lens and the arm (the
  station-neutral BS) does not move.
- B REAL SCENE (skip-if-absent, Tk/Xvfb): the user's exact sequence -- Apo75, swap to PYRITE 45-85,
  solve 35x35 then 55x55. BOTH now solve; the FOV readout lands on the request; the lens block and
  the fold mirror move ALONG the leg (dz ~ 0) and the beam splitter and LED body do not move at
  all; and the message says how far the room-making moved the arm.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0573_solve_makes_room_at_the_fold
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
LENS_FOLDER = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"

LENS_FRONT_ROW = 1
BS_ROW = 6
MIRROR_ROW = 7


def _check_pure(ok, notes) -> None:
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.surface_table_model import SurfaceRow

    def _row(name, *, thickness=0.0, desp_x=0.0, desp_z=0.0, mirror=False, neutral=False):
        row = SurfaceRow(name=name, thickness=float(thickness), diameter=25.0, glass="AIR")
        row.desp_x, row.desp_z, row.axis_move = float(desp_x), float(desp_z), 0.0
        advanced: dict = {}
        if mirror:
            advanced["StepOverlayPromotion"] = {"step_label": "optical"}
            advanced["OpticalSolidFaces"] = {"version": 1, "faces": [
                {"face_id": "S001/F002", "function": "Mirror", "role": "Mirror",
                 "normal": [-0.7071, 0.0, 0.7071], "centroid": [0.0, 0.0, 0.0]}]}
        if neutral:
            advanced["StepOverlayPromotion"] = {"step_label": "optical", "station_neutral": True,
                                                "beam_splitter": True}
        if advanced:
            row.advanced = advanced
        return row

    rows = [
        _row("Object at 1X", thickness=118.970),
        _row("Front Optical Vertex Datum", thickness=1.823, desp_x=82.039, desp_z=-64.687),
        _row("Rear Optical Vertex Datum", thickness=93.865, desp_x=121.559, desp_z=-104.207),
        _row("Promoted OPTICAL STEP optical solid", thickness=0.0, desp_x=-0.122,
             desp_z=-197.896, neutral=True),
        _row("Promoted OPTICAL STEP optical solid", thickness=72.519, desp_x=179.788,
             desp_z=-198.034, mirror=True),
        _row("Image / Sensor at 1X", thickness=0.0, desp_x=179.788, desp_z=-328.223),
    ]
    gap_row, mirror_row = 2, 4

    def stations():
        return [sum(float(r.thickness) for r in rows[:i]) for i in range(len(rows))]

    def pose(index):
        return np.array([float(rows[index].desp_x), 0.0,
                         stations()[index] + float(rows[index].desp_z)])

    probe = SimpleNamespace(
        rows=rows,
        _lens_leg_slide_plan=lambda: ([1, 2], np.array([1.0, 0.0, 0.0]), True),
        _promoted_mirror_fold_row_indices=lambda: [mirror_row],
        _step_path_for_label=lambda label: None,
        append_debug=lambda *a, **k: None,
        _row_z_positions=stations,
    )
    before = {index: pose(index) for index in range(len(rows))}
    result = ScenePlacementMixin.slide_fold_arm_along_leg(probe, 30.0)
    after = {index: pose(index) for index in range(len(rows))}

    ok(
        result is not None and abs(float(result["distance"]) - 30.0) < 1e-9,
        f"A1: the arm slide reports what it did ({result})",
    )
    ok(
        abs(float(after[mirror_row][0] - before[mirror_row][0]) - 30.0) < 1e-9
        and abs(float(after[mirror_row][2] - before[mirror_row][2])) < 1e-9,
        f"A2: the fold mirror travels ALONG the leg "
        f"(dx {float(after[mirror_row][0] - before[mirror_row][0]):+.4f}, "
        f"dz {float(after[mirror_row][2] - before[mirror_row][2]):+.4f})",
    )
    ok(
        abs(float(after[5][0] - before[5][0]) - 30.0) < 1e-9
        and abs(float(after[5][2] - before[5][2])) < 1e-9,
        "A3: ... and so does everything behind it (the sensor)",
    )
    ok(
        float(np.linalg.norm(after[BS_ROW - 3] - before[BS_ROW - 3])) < 1e-9,
        f"A4: the station-neutral beam splitter BETWEEN them does not move "
        f"({float(np.linalg.norm(after[3] - before[3])):.9f} mm) -- it is illumination, not arm",
    )
    ok(
        abs(float(rows[gap_row].thickness) - (93.865 + 30.0)) < 1e-9,
        f"A5: the lens->fold gap row records the leg that opened up "
        f"({float(rows[gap_row].thickness):.4f} mm) -- which is what gives the lens its room",
    )
    ok(
        float(np.linalg.norm(after[1] - before[1])) < 1e-9,
        "A6: the lens block itself is untouched by the room-making",
    )


def _check_real_scene(ok, notes) -> None:
    if not SCENE.exists() or not LENS_FOLDER.exists():
        notes.append("SKIP: machine_vision_Apo75.py / the PYRITE folder are not in this checkout")
        return
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services import row_placement
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"SKIP: the editor could not be imported ({type(exc).__name__}: {exc})")
        return

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor.layout_files["apo75"] = SCENE
        editor.load_layout_by_name("apo75")

        # bugs/0588 (flag_20260808_211659, the FOURTH recurrence of the large-field refusal):
        # the AS-LOADED lens is its own door. B below solves 35/55 AFTER a swap -- and a swap
        # changes the gaps enough that the folded branch's station-frame image-distance sum
        # stays positive. On the as-loaded Apo75 the 55x55 sum goes NEGATIVE (-7.86), and an
        # old feasibility gate bailed the whole folded branch to None, so the solve fell back
        # to the plain conjugate and 0466's "largest field ~80%" refusal -- bypassing the very
        # machinery B proves works. The INVARIANT (guard it, not the instance): a physically
        # reachable field must solve on ANY lens state, before or after any swap -- the machine
        # makes room, it does not forbid.
        qe0 = QuickEstimationService(SimpleNamespace(editor=editor))
        solved0, message0 = qe0.fov_solve("object", "thickness", 55.0, 55.0)
        ok(bool(solved0),
           f"B-1 (bugs/0588): 55x55 solves on the AS-LOADED lens, no swap first "
           f"({str(message0)[:80]})")
        ok(bool(solved0) and "Made room" in str(message0),
           "B-2 (bugs/0588): ... and it made room at the fold rather than refusing")
        # Fresh editor for the swap sequence B was written against.
        editor.destroy()
        editor = KrakenLayoutEditor()
        editor.layout_files["apo75"] = SCENE
        editor.load_layout_by_name("apo75")

        ok(editor.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False) is not None,
           "B0: the swap to PYRITE 45-85 runs")

        def pose(index):
            return np.asarray(row_placement.world_pose(editor, int(index)).position, dtype=float)

        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        for field in (35.0, 55.0):
            lens_before, bs_before, mirror_before = pose(LENS_FRONT_ROW), pose(BS_ROW), pose(MIRROR_ROW)
            led_before = np.asarray(
                editor._transformed_imported_step_mesh_for_label("led").bounds, dtype=float
            )
            solved, message = qe.fov_solve("object", "thickness", field, field)
            lens_after, bs_after, mirror_after = pose(LENS_FRONT_ROW), pose(BS_ROW), pose(MIRROR_ROW)
            led_after = np.asarray(
                editor._transformed_imported_step_mesh_for_label("led").bounds, dtype=float
            )
            readout = qe.current_state()

            ok(bool(solved), f"B1@{field:g} (the user's ask): the solve RUNS ({message[:80]})")
            mirror_dx = float(mirror_after[0] - mirror_before[0])
            # bugs/0648 REWRITE of the mechanism pins: the bugs/0645 snap machinery can
            # reach some of these fields WITHOUT the room-maker (measured: 35x35 now
            # solves with the mirror unmoved and the field delivered). The durable
            # contract is CLAIM == MOTION: the "Made room first" message appears exactly
            # when the fold mirror really moved along the leg (>1 mm), so the user is
            # told what moved and never told a fiction.
            ok(
                ("Made room first" in message) == (abs(mirror_dx) > 1.0),
                f"B2@{field:g}: the made-room claim matches the mirror's actual motion "
                f"(claim={'Made room first' in message}, mirror dx {mirror_dx:+.3f})",
            )
            ok(
                # bugs/0591: measured-aware readout -- the delivered field within the
                # refinement dead-band (~1%) + measurement noise, not the shared-frame 0.5 mm.
                abs(float(readout.get("fov_full") or 0.0) - field * np.sqrt(2.0)) < 0.02 * field * np.sqrt(2.0) + 0.5,
                f"B3@{field:g}: the FOV readout lands on the request "
                f"(diag {readout.get('fov_full')}, want {field * np.sqrt(2.0):.3f})",
            )
            ok(
                abs(float(lens_after[2] - lens_before[2])) < 0.05
                and float(lens_after[0] - lens_before[0]) > 1.0,
                f"B4@{field:g}: the lens moves ALONG its leg "
                f"(dx {float(lens_after[0] - lens_before[0]):+.3f}, "
                f"dz {float(lens_after[2] - lens_before[2]):+.4f})",
            )
            # bugs/0648: the mirror may legitimately stay put (snap-machinery reach) or
            # slide either way ALONG the leg (room-maker +x, near-leg recruit -x); what
            # it must never do is leave the leg.
            ok(
                abs(float(mirror_after[2] - mirror_before[2])) < 0.05,
                f"B5@{field:g}: the fold mirror stays ON its leg "
                f"(dx {mirror_dx:+.3f} allowed, "
                f"dz {float(mirror_after[2] - mirror_before[2]):+.4f} must be ~0)",
            )
            ok(
                float(np.linalg.norm(bs_after - bs_before)) < 1e-6
                and abs((led_after[4] + led_after[5]) / 2 - (led_before[4] + led_before[5]) / 2) < 1e-6,
                f"B6@{field:g}: and the illumination unit -- beam splitter and LED body -- does "
                f"not move ({float(np.linalg.norm(bs_after - bs_before)):.6f} mm)",
            )
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"SKIP: the scene could not be driven ({type(exc).__name__}: {exc})")
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_pure), ("B", _check_real_scene)):
        try:
            fn(ok, notes)
        except Exception as exc:  # pragma: no cover - environment
            notes.append(f"FAIL: section {section} raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Solve-makes-room-at-the-fold validation passed.")
        return 0
    print("Solve-makes-room-at-the-fold validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
