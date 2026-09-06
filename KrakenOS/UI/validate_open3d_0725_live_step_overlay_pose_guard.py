"""Guard for bugs/0725 -- a transient (unpromoted) STEP overlay must never move the optics.

Live flags 20260906_235409_571 ("rays haywired") and 20260907_000220_381 ("sensor displaced
seriously"), build 49362db2. The 3D window's Trace Now builds its preview with
``include_live_step_overlays=True``, which INSERTS the imported optical STEP body into the
traced row list. On om05a that body is the whole vendor assembly (61 698 cells): inserting it
shifted every later row index and made it a station of the follower walk, so the detector
target jumped from (272.63, -1.76, -25.0) to (0, 0, 589.14) -- the unfolded axis, 600 mm out.
Measured consequences: 1672 of 3225 rays "missed the image", only 24 reached it, and the trace
took 524 s instead of 55 s.

The invariant belongs to the scene, not to the overlay: adding a DISPLAY body must never move
an optical element. ``_live_step_overlay_injection_moves_optics`` compares the follower-walk
pose of every pre-existing row before and after the injection (mapping shifted indices) and
the caller drops the overlay from the trace when anything moves, saying so.

Checks (display-free, synthetic rows + a stubbed walk):
  A  a benign injection (every existing row keeps its pose) is allowed -- returns "".
  B  a harmful injection is refused with a reason naming the row and the shift.
  C  index mapping: rows after the insert point are compared against their SHIFTED index, so
     a pure renumbering with unchanged poses is still allowed; and a row that loses its pose
     entirely (the om05a Image row) is refused.
  D  a walk that raises is refused, not risked.
  E  wiring pins: every insertion path in _live_step_overlay_trace_rows consults the guard and
     falls back to the untouched rows; the refusal is reported (never silent).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0725_live_step_overlay_pose_guard
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import three_d_scene_tools as tst
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    guard = ThreeDSceneToolsMixin._live_step_overlay_injection_moves_optics

    class _Editor:
        def __init__(self):
            self.debug: list[str] = []

        def append_debug(self, message):
            self.debug.append(str(message))

    def rows_of(*names):
        return [SimpleNamespace(name=n) for n in names]

    original = rows_of("Object", "Mirror", "Lens", "Filter", "Image / Sensor")
    injected = rows_of("Object", "Mirror", "Live OPTICAL STEP", "Lens", "Filter", "Image / Sensor")

    def stub_walk(poses_by_name):
        def _walk(system, rows):
            out = {}
            for index, row in enumerate(list(rows)):
                pose = poses_by_name.get(str(row.name))
                if pose is not None:
                    out[index] = {"center": np.asarray(pose, dtype=float), "rotation": np.eye(3)}
            return out

        return _walk

    base_poses = {
        "Object": (0.0, 0.0, 0.0),
        "Mirror": (0.0, 0.0, 50.0),
        "Lens": (100.0, 0.0, 50.0),
        "Filter": (150.0, 0.0, 50.0),
        "Image / Sensor": (272.63, -1.76, -25.0),
        "Live OPTICAL STEP": (10.0, 20.0, 30.0),
    }

    saved_walk = tst.optical_solid_output_port_pose_overrides
    try:
        # ---- A / C: benign injection, indices shifted but poses identical -----------------
        tst.optical_solid_output_port_pose_overrides = stub_walk(base_poses)
        reason = guard(_Editor(), original, injected, 2, 1)
        ok(
            reason == "",
            f"A1: an injection that leaves every existing row's pose untouched is allowed "
            f"(reason={reason!r})",
        )
        ok(
            reason == "",
            "C1: rows after the insert point are compared against their SHIFTED index -- a pure "
            "renumbering is not a move",
        )

        # ---- B: a harmful injection ------------------------------------------------------
        # the AFTER walk (the longer, injected list) is the one that moves a row
        moved = dict(base_poses)
        moved["Filter"] = (150.0, 0.0, 62.0)

        def _walk_moved(system, rows):
            table = base_poses if len(list(rows)) == len(original) else moved
            out = {}
            for index, row in enumerate(list(rows)):
                pose = table.get(str(row.name))
                if pose is not None:
                    out[index] = {"center": np.asarray(pose, dtype=float), "rotation": np.eye(3)}
            return out

        tst.optical_solid_output_port_pose_overrides = _walk_moved
        reason_moved = guard(_Editor(), original, injected, 2, 1)
        ok(
            "Filter" in reason_moved and "12.000 mm" in reason_moved,
            f"B1: a row that moves is refused, with the row and the distance named ({reason_moved!r})",
        )

        # ---- C2: the om05a signature -- the Image row loses its pose ----------------------
        lost = {k: v for k, v in base_poses.items() if k != "Image / Sensor"}

        def _walk_lost(system, rows):
            out = {}
            for index, row in enumerate(list(rows)):
                name = str(row.name)
                pose = base_poses.get(name) if len(list(rows)) == len(original) else lost.get(name)
                if pose is not None:
                    out[index] = {"center": np.asarray(pose, dtype=float), "rotation": np.eye(3)}
            return out

        tst.optical_solid_output_port_pose_overrides = _walk_lost
        reason_lost = guard(_Editor(), original, injected, 2, 1)
        ok(
            "Image / Sensor" in reason_lost and "lost" in reason_lost,
            f"C2: the om05a failure -- the Image row losing its traced pose is refused ({reason_lost!r})",
        )

        # ---- D: an unusable walk ----------------------------------------------------------
        def _boom(system, rows):
            raise RuntimeError("walk exploded")

        tst.optical_solid_output_port_pose_overrides = _boom
        reason_boom = guard(_Editor(), original, injected, 2, 1)
        ok(
            bool(reason_boom) and "could not be compared" in reason_boom,
            f"D1: a walk that raises refuses the injection rather than risking it ({reason_boom!r})",
        )
    finally:
        tst.optical_solid_output_port_pose_overrides = saved_walk

    # ---- E: wiring pins -------------------------------------------------------------------
    source = inspect.getsource(ThreeDSceneToolsMixin._live_step_overlay_trace_rows)
    guard_calls = source.count("_live_step_overlay_injection_moves_optics(")
    refusals = source.count("_note_live_step_overlay_injection_refused(reason)")
    ok(
        guard_calls >= 3 and refusals >= 3 and source.count("return self.rows, []") >= 2,
        f"E1: every insertion path consults the guard and falls back to the untouched rows "
        f"({guard_calls} guard calls, {refusals} refusals)",
    )
    note_source = inspect.getsource(ThreeDSceneToolsMixin._note_live_step_overlay_injection_refused)
    ok(
        "append_debug" in note_source and "status_var" in note_source,
        "E2: the refusal is reported to the debug log and the status line -- never a silent skip",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0725 live-STEP-overlay pose-guard validation PASSED")
        return 0
    print("0725 live-STEP-overlay pose-guard validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
