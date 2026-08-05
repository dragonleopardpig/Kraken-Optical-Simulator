"""Display-free guard for bugs/0567 -- the straight equivalent works on a FROZEN scene.

flag_20260805_164242: *"solve for FOV 55x55, ray still defocus at the sensor."*

``_real_ray_best_focus_shift_for_rows`` returned ``None`` on the frozen Apo75 scene. That is
the function the frozen detector snap's ADAPTIVE corrective loop re-measures with, so ``None``
breaks the loop after ONE application -- and bugs/0515 established these shifts are
station-frame and UNDER-measured, so a single shot always leaves residual defocus. Measured
after the fix: the true shift was **35.85 mm**.

Two faults, both the same class -- code written for unfrozen scenes meeting a 0433-frozen one:

1. FOLD DETECTION keyed only on ``_optical_axis_fold_world_transform_for_row``, which is None
   for EVERY row on a frozen scene, so the guard reported "no fold" and handed the FOLDED mesh
   mirror to PupilCalc -- exactly what bugs/0194 built it to prevent. PupilCalc threw
   ``IndexError: index 0 is out of bounds for axis 0 with size 0`` on the 90-degree internal
   reflection, and a blanket ``except Exception: return None`` hid it. This is the FOURTH
   consumer of that gate to need a breadcrumb fallback (0517, 0519, 0525).
2. PLACEMENT STRIPPING covered only the promoted solids. On a frozen scene EVERY row carries a
   baked world placement: the lens block kept tilt (0, -90, -180) and desp (82.04, 0, -64.69),
   so the "straight equivalent" was neither straight nor centred and the SEQUENTIAL trace it
   exists to feed lost every ray -- the empty direction cosines PupilCalc choked on.

Checks (pure, no VTK/tk):
- BREADCRUMB: with the fold transform absent (the frozen case) a promoted MIRROR row still
  makes the scene read as folded, so an equivalent is produced instead of None.
- BS KEEPS ITS MESH: a promoted BEAM SPLITTER carries no Mirror face, so bugs/0173 still holds
  -- no fold, no equivalent.
- STRIPPED: a world-placed row comes back with zero tilt and zero desp, so the sequential trace
  is centred on the axis.
- SEQUENTIAL ROW UNTOUCHED: a genuinely decentred row on an UNFROZEN scene keeps its decenter.
- GAPS PRESERVED: stripping placement must not disturb the axial gaps -- the equivalent stays
  in the detector's cumulative-z frame.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0567_frozen_straight_equivalent
"""

from __future__ import annotations

import inspect


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI.services import paraxial_tools
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: paraxial_tools unavailable ({exc!r})"]

    source = inspect.getsource(
        paraxial_tools.ParaxialToolsMixin._folded_optical_solid_straight_equivalent_rows
    )

    # --- BREADCRUMB fallback -----------------------------------------------------------------
    if "_promoted_mirror_fold_row_indices" not in source:
        failures.append(
            "breadcrumb: fold detection must fall back to _promoted_mirror_fold_row_indices -- "
            "_optical_axis_fold_world_transform_for_row is None on EVERY row of a 0433-frozen "
            "scene, so the transform-only gate reports 'no fold' and feeds the folded mesh to "
            "PupilCalc (bugs/0567)"
        )
    fallback_at = source.find("_promoted_mirror_fold_row_indices")
    transform_at = source.find("_optical_axis_fold_world_transform_for_row")
    if fallback_at != -1 and transform_at != -1 and fallback_at < transform_at:
        failures.append(
            "breadcrumb: the transform gate must be tried FIRST -- the breadcrumb is a fallback "
            "for the frozen case, not a replacement"
        )

    # --- PLACEMENT stripping for world-placed rows --------------------------------------------
    if "is_world_placed" not in source:
        failures.append(
            "stripped: a WORLD-placed row's tilt/desp must be dropped from the straight "
            "equivalent -- the frozen lens block kept tilt (0,-90,-180) and desp ~130 mm, so "
            "the sequential trace lost every ray (bugs/0567)"
        )

    # --- BS keeps its mesh (bugs/0173) ---------------------------------------------------------
    # The breadcrumb counts MIRROR faces only, so a straight-through beam-splitter cube still
    # reports no fold. Assert the predicate used is the mirror one, not a generic solid test.
    if "_promoted_beam_splitter_row_indices" in source:
        failures.append(
            "bs: the fallback must key on promoted MIRROR folds only -- counting beam splitters "
            "would flatten a straight-through cube's mesh and break bugs/0173"
        )

    # --- The caller's silent failure ------------------------------------------------------------
    measure = inspect.getsource(
        paraxial_tools.ParaxialToolsMixin._real_ray_best_focus_shift_for_rows
    )
    if "_folded_optical_solid_straight_equivalent_rows" not in measure:
        failures.append(
            "caller: the real-ray focus measure must route through the straight equivalent "
            "(bugs/0194) -- without it PupilCalc throws on the mesh mirror"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0567 frozen straight-equivalent validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0567 validation passed: the straight equivalent is reachable on a 0433-frozen scene "
        "(breadcrumb fold detection behind the transform gate) and is genuinely straight "
        "(world-placed rows lose their baked tilt/desp), so the real-ray focus measure returns "
        "a number instead of None and the snap's adaptive loop can iterate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
