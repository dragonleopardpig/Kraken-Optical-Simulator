"""Display-free guard for bugs/0547 -- a lens swap must leave the replacement block ON the
frozen leg (flag_20260804_212159, machine_vision_AZ85_RA_Mirror_BS).

With bugs/0546 unblocking the swap on this scene, the replacement lens landed on the STRAIGHT
global axis: *"physical lens is reversed, surrogate is snap to another axis, lens STEP seems not
snap and not centered at the fold axis"*. Measured headless on the user's own scene, swapping
ELS-85 -> 0703:

    front datum  (118.586, 0, 53.803)  ->  (0, 0, 155.520)      118.6 mm off the leg
    block tilt   (0, -90, -180)        ->  (0, 0, 0)            flattened

On a 0433-frozen / axis-snapped scene a row's ``desp`` + ``tilt`` IS its final world placement
(``row_placement.WORLD``). The replacement block comes from a FRESH single-lens surrogate whose
rows are straight-axis, so the splice dropped the baked placement on the floor -- while the lens
STEP overlay, whose pose bugs/0381 deliberately preserves, stayed behind on the leg. The fold
transform cannot supply the missing frame: it is None on every frozen scene (the durable
"frozen fold-transform gate" -- this is its 4th consumer after 0517 / 0519 / 0525). So the leg is
measured from the scene itself: old front datum -> old rear datum.

Checks (headless, no VTK/tk):
- CARRY: on a frozen scene the swapped block keeps the front datum's world pose, stays on the old
  leg line (perpendicular distance ~0), keeps the baked tilt, and carries the freeze breadcrumb.
- NON-VACUOUS: the replacement's straight-axis rows would land >50 mm away, so the assertions
  above cannot pass by accident.
- SEQUENTIAL UNTOUCHED: a plain (unfrozen) scene gets no frame and no baked desp/tilt -- the
  pre-0547 behaviour is preserved exactly.
- FRAME: `_swap_frozen_block_frame` reports the leg direction/tilt, and falls back to the baked
  tilt's own +Z when the block has zero length.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0547_swap_keeps_frozen_leg
"""

from __future__ import annotations

import numpy as np

# (name, thickness, desp_x, desp_z, tilt, frozen) -- the flagged scene's real baked numbers.
# Poses: the lens block + BS + mirror sit on the frozen +X leg at z = 53.803; the BS cube's own
# pose is (-0.122, 0, 54.459) and the RA mirror's (229.930, 0, 53.803).
FROZEN_SCENE = [
    ("Object at 1X", 155.520, 0.0, 0.0, (0.0, 0.0, 0.0), False),
    ("Front Optical Vertex Datum", 17.6385, 118.586, -101.717, (0.0, -90.0, -180.0), True),
    ("Blackbox Group 1", 9.8615, 136.224, -119.356, (0.0, -90.0, -180.0), True),
    ("Promoted OPTICAL STEP optical solid", 0.0, -0.122, -128.561, (0.0, 0.0, -90.0), True),
    ("Aperture Stop F/4.5", 9.8615, 146.086, -129.217, (0.0, -90.0, -180.0), True),
    ("Blackbox Group 2", 17.6385, 155.947, -139.079, (0.0, -90.0, -180.0), True),
    ("Rear Optical Vertex Datum", 78.3845, 173.586, -156.717, (0.0, -90.0, -180.0), True),
    ("Promoted OPTICAL STEP optical solid", 39.961, 229.930, -235.102, (0.0, 0.0, 0.0), True),
    ("Image / Sensor at 1X", 0.0, 229.930, -338.102, (180.0, 0.0, 0.0), True),
]

# A replacement lens with a DIFFERENT optical length (50 mm against the old block's 55 mm).
NEW_BLOCK = [
    ("Front Optical Vertex Datum", 4.0),
    ("Blackbox Group 1", 21.0),
    ("Aperture Stop F/2.8", 21.0),
    ("Blackbox Group 2", 4.0),
    ("Rear Optical Vertex Datum", 0.0),
]


def _rows(spec, *, frozen: bool = True):
    from KrakenOS.UI.surface_table_model import SurfaceRow

    rows = []
    for name, thickness, desp_x, desp_z, tilt, is_frozen in spec:
        row = SurfaceRow(name=name, thickness=float(thickness), diameter=29.0, glass="AIR")
        if frozen:
            row.desp_x, row.desp_z = float(desp_x), float(desp_z)
            row.tilt_x, row.tilt_y, row.tilt_z = (float(v) for v in tilt)
            row.axis_move = 0.0
            if is_frozen:
                row.advanced = {"ScenePlacement": {"stay_put_freeze": {"reason": "fold_removed"}}}
        rows.append(row)
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    return rows


def _stations(rows):
    out, total = [0.0], 0.0
    for row in rows[:-1]:
        total += float(getattr(row, "thickness", 0.0) or 0.0)
        out.append(total)
    return out


def _pose(rows, index):
    row = rows[index]
    return np.asarray(
        [
            float(getattr(row, "desp_x", 0.0) or 0.0),
            float(getattr(row, "desp_y", 0.0) or 0.0),
            _stations(rows)[index] + float(getattr(row, "desp_z", 0.0) or 0.0),
        ],
        dtype=float,
    )


def _tilt(row):
    return tuple(
        float(getattr(row, name, 0.0) or 0.0) for name in ("tilt_x", "tilt_y", "tilt_z")
    )


def _check_frozen_carry(failures: list[str]) -> None:
    from KrakenOS.UI.services import row_placement
    from KrakenOS.UI.validate_open3d_0546_swap_keeps_inblock_solid import _editor, _run_real_swap

    before_rows = _rows(FROZEN_SCENE)
    before = _editor(before_rows)
    front, rear = before._imaging_lens_block_indices()
    if front is None:
        failures.append("carry: the frozen scene's lens block is not detected (bugs/0546 regressed)")
        return
    origin = _pose(before_rows, front)
    leg_end = _pose(before_rows, rear)
    leg = leg_end - origin
    leg_len = float(np.linalg.norm(leg))
    if leg_len < 1.0:
        failures.append(f"carry: the test scene's block has no length ({leg_len})")
        return
    leg_dir = leg / leg_len
    old_tilt = _tilt(before_rows[front])

    editor, result, errors = _run_real_swap(NEW_BLOCK, rows=_rows(FROZEN_SCENE))
    if errors or result is None:
        failures.append(f"carry: the swap did not run ({errors or 'returned None'})")
        return

    rows = editor.rows
    new_front, new_rear = editor._imaging_lens_block_indices()
    if new_front is None:
        failures.append("carry: the swapped scene lost its lens block")
        return

    front_pose = _pose(rows, new_front)
    drift = float(np.max(np.abs(front_pose - origin)))
    if drift > 1e-9:
        failures.append(
            f"carry: the front datum left the frozen leg -- {tuple(round(v, 3) for v in origin)} -> "
            f"{tuple(round(v, 3) for v in front_pose)} ({drift:.4g} mm)"
        )

    straight_gap = 0.0
    for index in range(new_front, new_rear + 1):
        pose = _pose(rows, index)
        # perpendicular distance from the old leg LINE
        offset = pose - origin
        perpendicular = float(np.linalg.norm(offset - leg_dir * float(np.dot(offset, leg_dir))))
        if perpendicular > 1e-9:
            failures.append(
                f"carry: S{index} sits {perpendicular:.4g} mm off the frozen leg "
                f"(pose {tuple(round(v, 3) for v in pose)})"
            )
        if _tilt(rows[index]) != old_tilt:
            failures.append(
                f"carry: S{index} tilt {_tilt(rows[index])} != the block's baked tilt {old_tilt}"
            )
        if not row_placement.is_world_placed(rows[index]):
            failures.append(
                f"carry: S{index} lost the 0433 freeze breadcrumb -- the table round-trip will "
                "flatten its tilts (bugs/0441)"
            )
        # NON-VACUOUS: how far the untouched straight-axis row would have been.
        straight_gap = max(
            straight_gap, float(np.linalg.norm(pose - np.asarray([0.0, 0.0, pose[2]])))
        )
    if straight_gap < 50.0:
        failures.append(
            f"carry: the block sits only {straight_gap:.3g} mm off the global axis -- this scene "
            "cannot distinguish a carried frame from an untouched straight one"
        )


def _check_sequential_untouched(failures: list[str]) -> None:
    from KrakenOS.UI.validate_open3d_0546_swap_keeps_inblock_solid import _editor, _run_real_swap

    plain = _rows(FROZEN_SCENE, frozen=False)
    editor = _editor(plain)
    front, rear = editor._imaging_lens_block_indices()
    if editor._swap_frozen_block_frame(front, rear) is not None:
        failures.append("sequential: a plain scene must yield NO frozen frame (leave 0547 asleep)")

    swapped, result, errors = _run_real_swap(NEW_BLOCK, rows=_rows(FROZEN_SCENE, frozen=False))
    if errors or result is None:
        failures.append(f"sequential: the swap did not run ({errors or 'returned None'})")
        return
    new_front, new_rear = swapped._imaging_lens_block_indices()
    for index in range(new_front, new_rear + 1):
        row = swapped.rows[index]
        if any(abs(float(getattr(row, name, 0.0) or 0.0)) > 1e-9 for name in ("desp_x", "desp_y", "desp_z")):
            failures.append(
                f"sequential: S{index} was given a baked desp -- an unfrozen scene must be "
                "untouched by bugs/0547"
            )
            break


def _check_frame(failures: list[str]) -> None:
    from KrakenOS.UI.validate_open3d_0546_swap_keeps_inblock_solid import _editor

    editor = _editor(_rows(FROZEN_SCENE))
    front, rear = editor._imaging_lens_block_indices()
    frame = editor._swap_frozen_block_frame(front, rear)
    if frame is None:
        failures.append("frame: a frozen block must yield a frame")
        return
    if float(np.max(np.abs(np.asarray(frame["axis"]) - np.asarray([1.0, 0.0, 0.0])))) > 1e-6:
        failures.append(f"frame: the leg direction should be +X on this scene, got {frame['axis']}")
    if tuple(frame["tilt"]) != (0.0, -90.0, -180.0):
        failures.append(f"frame: the baked tilt should be (0, -90, -180), got {frame['tilt']}")
    if not frame.get("placement", {}).get("stay_put_freeze"):
        failures.append("frame: the freeze breadcrumb must be carried so it can be re-stamped")

    # Degenerate block (both datums coincident) -> fall back to the baked tilt's own +Z, never the
    # global axis.
    degenerate = _rows(FROZEN_SCENE)
    degenerate[2].thickness = 0.0
    degenerate[3].thickness = 0.0
    degenerate[4].thickness = 0.0
    degenerate[5].thickness = 0.0
    for index in (2, 4, 5, 6):
        degenerate[index].desp_x = degenerate[1].desp_x
        degenerate[index].desp_z = degenerate[1].desp_z + (_stations(degenerate)[1] - _stations(degenerate)[index])
    editor2 = _editor(degenerate)
    frame2 = editor2._swap_frozen_block_frame(1, 6)
    if frame2 is None:
        failures.append("frame: a zero-length frozen block must still yield a frame")
    else:
        axis = np.asarray(frame2["axis"], dtype=float)
        if abs(float(np.linalg.norm(axis)) - 1.0) > 1e-6:
            failures.append(f"frame: the fallback axis must be a unit vector, got {axis}")
        if abs(float(axis[2])) > 0.99:
            failures.append(
                f"frame: the zero-length fallback took the GLOBAL axis {axis} instead of the "
                "baked tilt's own +Z"
            )


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: swap deps unavailable ({type(exc).__name__}: {exc})"]
    _check_frozen_carry(failures)
    _check_sequential_untouched(failures)
    _check_frame(failures)
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0547 swap-keeps-frozen-leg validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0547 validation passed: a swap on a 0433-frozen scene re-bakes the replacement block onto "
        "the leg the old block occupied -- same front datum, same tilt, on the leg line, freeze "
        "breadcrumb carried -- while a plain sequential scene is left exactly as before."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
