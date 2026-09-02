"""Guard for bugs/0693 -- STEP-body offset writers convert WORLD deltas into the
frame the offset is APPLIED in.

flag_20260902_115321 ("rotated RA mirror under the prism assembly, whole axis
rotated as well, but the lens surrogate displaced from lens body"): the lens and
camera overlays align in the PLACEMENT frame and are then folded to world, so
`*_step_placement_offset_xyz` translates PRE-fold. The fold-carry's body seater
(`_seat_step_body_world_center`) wrote its world residual raw into that offset;
on the om05a production rotation (station checks Left/Right vs Top/Bottom -> the
leg swings -x -> -z about the incoming beam) the correction came out rotated and
the lens body landed 17.1 mm off its surrogate axis. Reproduced byte-exact by
bugs/0693_repro_rotation.py (offset (15.5581, 0.2335, 9.2197) = the flag).

Checks (display-free, unbound mixin methods on stubs):
  A  `_seat_step_body_world_center` writes R.T @ (goal - current), not the raw
     world residual (and stays byte-identical when R is identity).
  B  `_shift_step_offset` converts its world delta the same way.
  C  `_step_offset_world_rotation`: lens reads the front-datum fold transform;
     camera prefers its branch transform; optical/led stay identity; a missing
     transform degrades to identity.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0693_step_offset_frame
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin

ROT_Y90 = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])


class _Stub:
    """Editor stub: records offset writes, serves a controllable frame rotation."""

    def __init__(self, rotation):
        self._rotation = np.asarray(rotation, dtype=float)
        self.written = None

    def _step_body_world_center(self, label):
        return np.zeros(3)

    def _step_placement_offset_xyz(self, label):
        return (0.0, 0.0, 0.0)

    def _set_step_placement_offset_xyz(self, label, value):
        self.written = np.asarray(value, dtype=float).reshape(3)

    def _step_offset_world_rotation(self, label):
        return self._rotation


def _check_writers(ok, notes) -> None:
    goal = np.array([1.0, 2.0, 3.0])
    stub = _Stub(ROT_Y90)
    ParaxialToolsMixin._seat_step_body_world_center(stub, "lens", goal)
    want = ROT_Y90.T @ goal
    ok(
        stub.written is not None and np.allclose(stub.written, want, atol=1e-12),
        f"A1: seater writes R.T @ residual ({np.round(stub.written, 3) if stub.written is not None else None} vs want {np.round(want, 3)})",
    )
    stub_id = _Stub(np.eye(3))
    ParaxialToolsMixin._seat_step_body_world_center(stub_id, "lens", goal)
    ok(
        stub_id.written is not None and np.allclose(stub_id.written, goal, atol=1e-12),
        "A2: identity frame stays byte-identical (straight scenes untouched)",
    )
    stub2 = _Stub(ROT_Y90)
    ParaxialToolsMixin._shift_step_offset(stub2, "camera", goal)
    ok(
        stub2.written is not None and np.allclose(stub2.written, want, atol=1e-12),
        f"B: _shift_step_offset converts its world delta ({np.round(stub2.written, 3) if stub2.written is not None else None})",
    )


def _check_frame_lookup(ok, notes) -> None:
    fold = np.eye(4)
    fold[:3, :3] = ROT_Y90
    branch = np.eye(4)
    branch[:3, :3] = ROT_Y90.T

    class _Frames(ParaxialToolsMixin):
        # subclass so `_step_offset_world_rotation` reaches its sibling
        # `_step_body_anchor_world_transform` through the same mixin
        def __init__(self, camera_branch=None, fold_transform=None):
            self._branch = camera_branch
            self._fold = fold_transform

        def _lens_front_datum_row_index(self):
            return 3

        def _image_plane_row_index(self):
            return 9

        def _camera_branch_world_transform(self):
            return self._branch

        def _optical_axis_fold_world_transform_for_row(self, index):
            return self._fold

    r = ParaxialToolsMixin._step_offset_world_rotation(_Frames(fold_transform=fold), "lens")
    ok(np.allclose(r, ROT_Y90), "C1: lens frame = the front-datum fold rotation")
    r = ParaxialToolsMixin._step_offset_world_rotation(
        _Frames(camera_branch=branch, fold_transform=fold), "camera"
    )
    ok(np.allclose(r, ROT_Y90.T), "C2: camera prefers its branch transform")
    r = ParaxialToolsMixin._step_offset_world_rotation(_Frames(fold_transform=fold), "optical")
    ok(np.allclose(r, np.eye(3)), "C3: optical draws straight in world -> identity")
    r = ParaxialToolsMixin._step_offset_world_rotation(_Frames(), "lens")
    ok(np.allclose(r, np.eye(3)), "C4: a missing transform degrades to identity")


def _check_carry_anchor_wiring(ok, notes) -> None:
    """D (mirror2 follow-up): the fold-carry captures a leg-anchor walk frame and maps
    carried rows by T_after @ inv(T_before), with the 0488 rigid transform as fallback --
    source-pinned like 0487/0491/0496 (the om05a rotation repro is the behavioural proof:
    mirror2 lands ON the swung leg instead of 18.7 mm off it)."""
    import inspect

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    before_src = inspect.getsource(ScenePlacementMixin._fold_slide_carry_before)
    apply_src = inspect.getsource(ScenePlacementMixin._fold_slide_carry_apply)
    ok(
        "leg_anchor" in before_src
        and "point_on_emitted_leg(tree, int(row_index), point)" in before_src,
        "D1: the before-capture derives a leg-anchor walk frame via the SAME membership "
        "primitive the bodies use",
    )
    ok(
        "anchor_origins[0], anchor_origins[1], rotation" in apply_src
        and "self._fold_carry_transform_point(pose, fold_before, fold_after, rotation)" in apply_src,
        "D2: the apply pivots the rigid carry on the anchor walk-frame ORIGINS (roll-"
        "invariant, arc-exact) and keeps the emission-origin fallback",
    )
    ok(
        "anchor_rotation" not in apply_src
        and "self._fold_carry_rotate_row_tilts(follower, rotation)" in apply_src,
        "D3: carried tilts turn ONLY with the rigid leg rotation -- the walk frame's "
        "roll convention must never reach an orientation (it folded the sensor leg UP)",
    )


def _check_world_axis_rotation_conjugation(ok, notes) -> None:
    """E (bugs/0698, flag 075132): `rotate_step_world_axis` must conjugate the
    world delta into the body's PRE-FOLD frame (R.T @ D @ R) and convert the
    pivot residual the same way -- composing raw made the green (Y) arc rotate
    the folded camera about world Z, and the pivot compensation dragged the
    body sideways. Source-pinned like D."""
    import inspect

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    src = inspect.getsource(ScenePlacementMixin.rotate_step_world_axis)
    ok(
        "self._step_offset_world_rotation(label)" in src
        and "frame_rotation.T" in src
        and "@ frame_rotation" in src,
        "E1: the world-axis delta is conjugated into the placement frame "
        "(R.T @ D_world @ R)",
    )
    ok(
        "frame_rotation.T @ (current_center - rotated_center)" in src,
        "E2: the in-place pivot residual converts world -> placement frame before "
        "landing in the offset",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for check in (_check_writers, _check_frame_lookup, _check_carry_anchor_wiring,
                  _check_world_axis_rotation_conjugation):
        try:
            check(ok, notes)
        except Exception as exc:
            notes.append(f"FAIL: {check.__name__} raised {type(exc).__name__}: {exc}")
    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("step-offset frame validation PASSED")
        return 0
    print("step-offset frame validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
