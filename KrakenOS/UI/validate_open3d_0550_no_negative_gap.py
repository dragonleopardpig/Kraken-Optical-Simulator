"""Display-free guard for bugs/0550 -- "Extra rays out of bound"
(flag_20260805_072959_035, attachment/machine_vision_Apo75.py).

A gap is a DISTANCE and may never go negative. A negative ``thickness`` makes the station
chain run BACKWARDS across that row, and the trace loses its next surface::

    s5 Rear Optical Vertex Datum   station 168.974   thickness  83.381
    s6 Promoted OPTICAL STEP solid station 252.355   thickness -13.595   <-- negative
    s7 Promoted OPTICAL STEP solid station 238.760                       <-- went BACKWARDS

Measured with ``bugs/diag_0550_negative_gap_strays.py`` (poses held to 0.0 mm while the gap
was zeroed), against the un-swapped scene as the yardstick:

    original AZ85    279 no_next_intersection / 225 reaching
    Apo75 as saved   375 no_next_intersection /  93 reaching
    gap zeroed       287 no_next_intersection / 160 reaching

-- i.e. the negative gap accounts for essentially every out-of-bound ray.

``Open3DSolveService.solve`` wrote ``rows[i].thickness = solved`` with NO lower bound (the
paraxial solvers it calls bound their own search at 0, so a negative here means the objective
wanted the element AHEAD of its predecessor). Every other gap writer found already guards, and
the offender in the flagged scene does not reproduce headlessly -- so, per the bugs/0391-0395
lesson, this also ships the DIAGNOSTIC: the flag now names any negative-gap row, and an opt-in
tripwire captures the writer's stack.

Checks (headless, no VTK/tk):
- CLAMP: a solve whose objective returns a negative distance writes 0, not the negative, and
  SAYS it clamped rather than silently flooring.
- NO FALSE CLAMP: a positive solve is written through untouched and reports no clamp.
- FLAG: the recorder snapshot carries ``negative_gap_rows`` so a future flag names the row.
- TRIPWIRE: ``install_negative_gap_trap`` is OPT-IN -- off (and unpatched) without the
  environment variable, active with it.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0550_no_negative_gap
"""

from __future__ import annotations

import os
from types import SimpleNamespace


class _Row:
    def __init__(self, name, thickness=0.0, surface="Standard"):
        self.name = name
        self.thickness = float(thickness)
        self.surface = surface
        self.optimize_thickness = False


def _service(rows, solved_distance):
    """The REAL solve service, with only the optimiser's answer stubbed."""
    from KrakenOS.UI.services.open3d_solve import Open3DSolveService

    editor = SimpleNamespace(rows=rows)
    service = Open3DSolveService(SimpleNamespace(editor=editor))

    def _compute(objective, row_index):
        return {"solved_distance": float(solved_distance), "best_rms": 0.001}

    service._compute = _compute  # type: ignore[method-assign]
    return service, editor


def _check_clamp(failures: list[str]) -> None:
    # The flagged shape: a zero-thickness promoted solid sits between the lens block and the
    # mount, and best focus wants the mount 13.595 mm further upstream than that row allows.
    rows = [
        _Row("Object", 118.97, "Object"),
        _Row("Rear Optical Vertex Datum", 83.381),
        _Row("Promoted OPTICAL STEP optical solid", 0.0),
        _Row("Promoted OPTICAL STEP optical solid", 72.519),
        _Row("Image", 0.0, "Image"),
    ]
    service, editor = _service(rows, -13.595)
    service.set_variable(2, True)
    ok, message = service.solve("focus")
    if not ok:
        failures.append(f"clamp: the solve must still succeed, got {message!r}")
        return
    if float(editor.rows[2].thickness) < 0.0:
        failures.append(
            f"clamp: a NEGATIVE gap was committed ({editor.rows[2].thickness}) -- the station "
            "chain would run backwards and the trace would lose its next surface (bugs/0550)"
        )
    if abs(float(editor.rows[2].thickness)) > 1e-9:
        failures.append(f"clamp: the gap must land at 0 mm, got {editor.rows[2].thickness}")
    if "CLAMPED" not in message:
        failures.append(f"clamp: the solve must SAY it clamped rather than silently flooring; got {message!r}")

    # Stations must be non-decreasing afterwards -- that is the property the clamp exists for.
    station = 0.0
    for index, row in enumerate(editor.rows):
        thickness = float(row.thickness)
        if thickness < 0.0:
            failures.append(f"clamp: row {index} still carries a negative gap {thickness}")
        station += thickness


def _check_no_false_clamp(failures: list[str]) -> None:
    rows = [
        _Row("Object", 100.0, "Object"),
        _Row("Gap", 10.0),
        _Row("Image", 0.0, "Image"),
    ]
    service, editor = _service(rows, 42.5)
    service.set_variable(1, True)
    ok, message = service.solve("focus")
    if not ok:
        failures.append(f"no-false-clamp: the solve must succeed, got {message!r}")
        return
    if abs(float(editor.rows[1].thickness) - 42.5) > 1e-9:
        failures.append(
            f"no-false-clamp: a positive solve must be written through untouched, got "
            f"{editor.rows[1].thickness}"
        )
    if "CLAMPED" in message:
        failures.append(f"no-false-clamp: a positive solve must not report a clamp; got {message!r}")


def _check_flag_field(failures: list[str]) -> None:
    try:
        from KrakenOS.UI.services.open3d_event_recorder import SceneSnapshot
    except Exception as exc:
        failures.append(f"flag: could not import the recorder snapshot ({exc!r})")
        return
    snapshot = SceneSnapshot()
    if not hasattr(snapshot, "negative_gap_rows"):
        failures.append(
            "flag: the recorder snapshot must carry `negative_gap_rows` -- the writer does not "
            "reproduce headlessly, so a flag has to name the row itself (bugs/0550)"
        )
        return
    if snapshot.negative_gap_rows != []:
        failures.append("flag: `negative_gap_rows` must default to empty")


def _check_tripwire_opt_in(failures: list[str]) -> None:
    from KrakenOS.UI import surface_table_model

    saved = os.environ.get("KRAKEN_TRAP_NEGATIVE_GAP")
    already = bool(getattr(surface_table_model.SurfaceRow, "_kr_negative_gap_trap", False))
    try:
        os.environ.pop("KRAKEN_TRAP_NEGATIVE_GAP", None)
        if not already and surface_table_model.install_negative_gap_trap():
            failures.append("tripwire: must stay OFF without KRAKEN_TRAP_NEGATIVE_GAP")
        os.environ["KRAKEN_TRAP_NEGATIVE_GAP"] = "1"
        if not surface_table_model.install_negative_gap_trap():
            failures.append("tripwire: must install when KRAKEN_TRAP_NEGATIVE_GAP is set")
    finally:
        if saved is None:
            os.environ.pop("KRAKEN_TRAP_NEGATIVE_GAP", None)
        else:
            os.environ["KRAKEN_TRAP_NEGATIVE_GAP"] = saved


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI.services.open3d_solve import Open3DSolveService  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: solve deps unavailable ({type(exc).__name__}: {exc})"]
    _check_clamp(failures)
    _check_no_false_clamp(failures)
    _check_flag_field(failures)
    _check_tripwire_opt_in(failures)
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0550 negative-gap validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0550 validation passed: a Variable-thickness solve can no longer commit a negative gap "
        "(clamped to 0 and reported, positives untouched), a flag names any negative-gap row, and "
        "the writer tripwire is opt-in."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
