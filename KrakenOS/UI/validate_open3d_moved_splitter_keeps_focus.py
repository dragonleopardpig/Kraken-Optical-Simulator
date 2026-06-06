"""Guard for bugs/0023 -- moving a beam-splitter off the beam must not drag the
focus/detector off its real station.

Regression context
------------------
A promoted optical solid's output-port override (`build_optical_solid_output_port_pose_overrides`)
repositions downstream rows onto the solid's exit frame. Bug 0017 added a guard
to skip that for a straight-through *inferred* exit, but it required the exit to
be both codirectional AND laterally *centred* on the incoming axis. So when the
user shifted the beam-splitter cube sideways off the beam, the exit FACE moved
off-axis (still codirectional -- no fold), the lateral test failed, and the
override snapped the Image/detector onto the displaced face -- dragging the focus
~400 mm off its real station (cube in place: Image at z=665; cube -55 mm X: Image
yanked to [-55, 0, 265]). The rays then missed the detector entirely.

Fix: the skip is now direction-only (`_exit_frame_is_non_folding`). Only a real
FOLD (a change of propagation direction) relocates the beam and its downstream
detector; a non-folding exit never repositions downstream rows, regardless of the
solid's lateral position. The sensor is fixed; the beam focuses at the lens focus
whether or not the cube is in the path.

Checks (display-free):
A. `_exit_frame_is_non_folding` is True for a codirectional exit and False for a
   fold; the override builder uses it and no longer references the old
   lateral-centred predicate.
B. With the machine-vision rows and the cube shifted -55 mm in X, the override
   does NOT reposition the downstream Image row (it stays at its authored
   station). SKIP when the prescription is unavailable.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_moved_splitter_keeps_focus

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESCRIPTION = PROJECT_ROOT / "attachment" / "machine_vision_150mm_measured_test.py"
CUBE_ROW = 6


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    import KrakenOS.UI.nonseq_output_ports as nop
    from KrakenOS.UI.nonseq_output_ports import (
        _exit_frame_is_non_folding,
        build_optical_solid_output_port_pose_overrides,
    )

    incoming = np.array([0.0, 0.0, 1.0])

    # A1. A codirectional exit (forward == incoming) is non-folding, regardless of
    #     any lateral offset (identity rotation -> forward = +Z).
    if not _exit_frame_is_non_folding(np.eye(3), incoming):
        notes.append("FAIL: a codirectional exit was not recognised as non-folding")
        passed = False
    # A2. A 90-degree fold (forward = +X) must NOT be non-folding -> still repositions.
    fold_rotation = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])  # column 2 = +X
    if _exit_frame_is_non_folding(fold_rotation, incoming):
        notes.append("FAIL: a 90-degree folded exit was wrongly treated as non-folding")
        passed = False
    # A3. Source: the builder uses the direction-only skip, not the stale predicate.
    try:
        src = inspect.getsource(nop.build_optical_solid_output_port_pose_overrides)
    except Exception as exc:
        src = ""
        notes.append(f"FAIL: cannot read build_optical_solid_output_port_pose_overrides source: {exc!r}")
        passed = False
    if src and "_exit_frame_is_non_folding" not in src:
        notes.append("FAIL: override builder no longer skips on a non-folding exit")
        passed = False
    if src and "_exit_frame_is_on_axis_passthrough" in src:
        notes.append("FAIL: stale lateral-centred passthrough predicate still gates the skip")
        passed = False

    # B. A laterally-moved cube must not reposition the downstream Image.
    if not PRESCRIPTION.exists():
        notes.append("SKIP: bug-0023 repro prescription unavailable")
        return passed, notes
    try:
        from KrakenOS.UI.render_layout_snapshot import _load_layout_module, _rows_from_layout_info

        module = _load_layout_module(PRESCRIPTION)
        rows = _rows_from_layout_info({"surfaces": list(getattr(module, "SURFACES", []) or [])})
        if CUBE_ROW >= len(rows):
            notes.append("SKIP: prescription has no beam-splitter cube row")
            return passed, notes
        image_idx = len(rows) - 1

        # Sanity: with the cube in place, the non-folding straight-through exit
        # already must not reposition the Image (bug 0017 invariant).
        in_place = build_optical_solid_output_port_pose_overrides(rows)
        if image_idx in in_place:
            notes.append(f"FAIL: cube in place already repositions the Image (row {image_idx}) -- bug 0017 invariant broken")
            passed = False

        # Shift the cube -55 mm in X (the user's "beam splitter shifted out").
        rows[CUBE_ROW].desp_x = -55.0
        moved = build_optical_solid_output_port_pose_overrides(rows)
        if image_idx in moved:
            center = moved[image_idx].get("center")
            notes.append(
                f"FAIL: a laterally-moved beam-splitter repositioned the Image (row {image_idx}) "
                f"to {np.asarray(center).round(1).tolist() if center is not None else center} "
                "-- the focus/detector is dragged off its real station"
            )
            passed = False
        elif verbose:
            notes.append("cube shifted -55mm X: Image row not repositioned (focus stays on its station)")
    except Exception as exc:
        notes.append(f"FAIL: override geometry check raised {exc!r}")
        passed = False

    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0023: moving a beam-splitter off the beam keeps the focus/detector on station")
        return 0
    print("[FAIL] bugs/0023 moved-splitter focus guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
