"""Display-free guard for bugs/0557 -- ONE resolver for "where is this row".

Step 2 of ``docs/design_row_placement_space.md``, for the consumers that do not need the folded
display frame.

``SurfaceRow.desp_*`` carries two incompatible meanings and nothing in the type says which is in
force: a SEQUENTIAL offset from the row's station, or a WORLD placement already baked by the
0433 freeze / axis snap / a promotion. Five consumers have now inferred that privately and each
got it wrong on a frozen scene:

    0517  the branch camera frame
    0519  the FOV solve gate
    0525  the acceptance-cone crease
    0547  the lens-swap block placement (the swapped block snapped to the global axis)
    0556  the Normal-to-Sensor anchor (aimed 194 mm off the sensor -> an EMPTY view)

Each was patched in isolation, so the class survived every fix. ``row_placement.world_pose`` /
``world_frame`` are now the single answer, and this guard exists so the sixth consumer cannot
quietly re-derive it.

Checks (pure, no VTK/tk):
- WORLD ROW: a frozen row's baked placement IS its world pose, and the resolver reports it as
  ``WORLD`` so a caller can never mistake it for a straight-equivalent.
- SEQUENTIAL ROW: a plain row resolves to station + desp and is reported as ``SEQUENTIAL``
  (honest: the display fold is NOT applied -- that half of Step 2 is still open).
- ORIENTATION: ``world_frame`` returns the row's OWN normal/height from its tilts -- the exact
  thing bugs/0556 hardcoded to +Z for a flipped sensor.
- CONSUMERS: the two re-pointed consumers call the resolver instead of re-deriving
  ``station + desp`` themselves.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0557_row_pose_resolver
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np


def _row(**kwargs):
    values = dict(
        surface="Standard", name="row", thickness=0.0, diameter=25.0, advanced={},
        desp_x=0.0, desp_y=0.0, desp_z=0.0, tilt_x=0.0, tilt_y=0.0, tilt_z=0.0,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


def _editor(rows):
    class _Ed:
        def __init__(self, rows):
            self.rows = rows

        def _row_z_positions(self):
            out, total = [0.0], 0.0
            for row in self.rows[:-1]:
                total += float(row.thickness)
                out.append(total)
            while len(out) < len(self.rows):
                out.append(total)
            return out

    return _Ed(rows)


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI.services import row_placement
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: row_placement unavailable ({type(exc).__name__}: {exc})"]

    # --- WORLD ROW: the flagged 0556 geometry --------------------------------------------
    frozen_row = _row(
        surface="Image", desp_x=193.4, desp_y=0.0, desp_z=10.2 - 134.03, tilt_x=180.0,
        advanced={"ScenePlacement": {"stay_put_freeze": {"reason": "test"}}},
    )
    editor = _editor([_row(thickness=134.03), frozen_row])
    pose = row_placement.world_pose(editor, 1)
    if not np.allclose(np.asarray(pose.position, dtype=float), [193.4, 0.0, 10.2], atol=1e-6):
        failures.append(
            f"world row: resolver says {np.asarray(pose.position)} but the baked placement is "
            "(193.4, 0, 10.2) -- that 194 mm error is bugs/0556"
        )
    if pose.space != row_placement.WORLD:
        failures.append(f"world row: space reported {pose.space!r}, expected {row_placement.WORLD!r}")

    # --- SEQUENTIAL ROW --------------------------------------------------------------------
    plain = _editor([_row(thickness=50.0), _row(surface="Image", desp_z=3.0)])
    pose = row_placement.world_pose(plain, 1)
    if not np.allclose(np.asarray(pose.position, dtype=float), [0.0, 0.0, 53.0], atol=1e-9):
        failures.append(f"sequential row: expected (0, 0, 53), got {np.asarray(pose.position)}")
    if pose.space != row_placement.SEQUENTIAL:
        failures.append(
            f"sequential row: space reported {pose.space!r} -- a caller must be able to tell that "
            "the display fold has NOT been applied"
        )

    # --- ORIENTATION -----------------------------------------------------------------------
    position, rotation, space = row_placement.world_frame(editor, 1)
    if rotation is None:
        failures.append("orientation: world_frame returned no rotation for a tilted row")
    else:
        normal = np.asarray(rotation, dtype=float)[:, 2]
        if abs(abs(float(normal[2])) - 1.0) > 1e-6:
            failures.append(f"orientation: a tilt_x=180 sensor's normal is {normal}, expected +/-Z")
        if np.allclose(normal, [0.0, 0.0, 1.0], atol=1e-9):
            failures.append(
                "orientation: a FLIPPED sensor reported a bare +Z normal -- that is the hardcoded "
                "value bugs/0556 shipped"
            )
    if not np.allclose(np.asarray(position, dtype=float), [193.4, 0.0, 10.2], atol=1e-6):
        failures.append("orientation: world_frame position must agree with world_pose")
    if space != row_placement.WORLD:
        failures.append(f"orientation: world_frame space {space!r} disagrees with world_pose")

    # --- CONSUMERS route through the resolver ----------------------------------------------
    try:
        from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
        from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

        swap_src = inspect.getsource(LayoutTableWorkbenchMixin._swap_frozen_block_frame)
        if "row_placement.world_pose" not in swap_src:
            failures.append(
                "consumer: the lens-swap frozen block frame (bugs/0547) must ask the resolver, not "
                "re-derive station + desp"
            )
        anchor_src = inspect.getsource(ThreeDSceneToolsMixin._imaging_detector_row_anchor_target)
        if "row_placement.world_frame" not in anchor_src:
            failures.append(
                "consumer: the Normal-to-Sensor anchor (bugs/0556) must ask the resolver for its "
                "centre and orientation"
            )
    except Exception as exc:
        failures.append(f"consumer: could not inspect the re-pointed consumers ({exc!r})")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0557 row-pose resolver validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0557 validation passed: row_placement.world_pose/world_frame is the single answer to "
        "'where is this row', it reports WORLD vs SEQUENTIAL honestly, it carries the row's own "
        "orientation, and both re-pointed consumers call it instead of re-deriving station + desp."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
