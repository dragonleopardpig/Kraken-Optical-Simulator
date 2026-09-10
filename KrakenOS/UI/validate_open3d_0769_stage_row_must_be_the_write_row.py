"""Guard for bugs/0769 -- a camera stage declared on the wrong row must SAY so.

`om05a_folded.py` carried `camera_focus_stage: None` and could not book any image-side
correction. Declaring a stage on the RA mirror row did not help either, and the reason was
invisible: `_image_write_locked_by_vendor_hardware` exempts the stage only when the stage's row
IS the row the solve writes (`_folded_image_leg_write_row`). On that scene the write row is the
last row before Image; a stage on the mirror row therefore fell through to the bare "the sensor
carries the vendor camera body" line -- the same message a scene with no stage at all gets --
Motor 1 was skipped, and 7.31 mm of residual was reported with nothing pointing at the cause.

The fix is a message, not a guess: the code must not silently re-point the stage at whatever row
it happens to write, because that row may be a vendor body (measured: pointing the stage at
om05a_folded's last row, a desp-placed LED panel, satisfied the FIRST ORDER to -5e-13 while the
TRACE stayed 7.31 mm out -- a desp-placed body's thickness moves the station sum without moving
the sensor in the folded world).

Checks (display-free, pure):
  A  a stage on the WRONG row is refused with a reason naming both rows;
  B  a stage on the RIGHT row is exempted, exactly as bugs/0756 intended;
  C  no stage at all still gets the original bare message (unchanged for every other scene);
  D  the code does not silently substitute the write row for the declared one.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0769_stage_row_must_be_the_write_row
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


class _Row:
    def __init__(self, name="", advanced=None):
        self.name = name
        self.advanced = advanced or {}


def _service(stage_row):
    """A service whose editor has a glued camera STEP and, optionally, a declared stage."""
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    class _QE(QuickEstimationService):
        def _camera_focus_stage(self):
            if stage_row is None:
                return None
            return {"row": stage_row, "min_mm": -10.0, "max_mm": 10.0}

    editor = SimpleNamespace(
        _step_path_for_label=lambda label: "/tmp/camera.step" if label == "camera" else None,
        rows=[],
    )
    return _QE(SimpleNamespace(editor=editor))


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    rows = [_Row(f"r{i}") for i in range(24)]
    WRITE_ROW = 22

    wrong = _service(15)._image_write_locked_by_vendor_hardware(rows, WRITE_ROW)
    ok(bool(wrong), "A1: a stage declared on the wrong row is still a refusal (it cannot book)")
    ok(
        "15" in wrong and "22" in wrong,
        f"A2: and the reason names BOTH rows -- declared and written (got {wrong!r})",
    )
    ok(
        "cannot book" in wrong,
        "A3: and says the stage cannot book it, not merely that a camera is glued",
    )

    right = _service(WRITE_ROW)._image_write_locked_by_vendor_hardware(rows, WRITE_ROW)
    ok(
        right == "",
        f"B1: a stage on the write row is exempted (bugs/0756 intact) -- got {right!r}",
    )

    none_stage = _service(None)._image_write_locked_by_vendor_hardware(rows, WRITE_ROW)
    ok(
        none_stage == "the sensor carries the vendor camera body (glued camera STEP)",
        f"C1: with NO stage the original message is unchanged -- got {none_stage!r}",
    )
    ok(
        none_stage != wrong,
        "C2: and 'no stage' is now distinguishable from 'stage on the wrong row' -- being "
        "indistinguishable is what hid this for an afternoon",
    )

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    src = inspect.getsource(QuickEstimationService._image_write_locked_by_vendor_hardware)
    ok(
        "_folded_image_leg_write_row" not in src,
        "D1: the lock does not silently re-point the stage at the write row -- that row may be "
        "a vendor body, and on om05a_folded it satisfied the first order while the trace stayed "
        "7.31 mm out",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0769 stage-row-must-be-the-write-row validation PASSED")
        return 0
    print("0769 stage-row-must-be-the-write-row validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
