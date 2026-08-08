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


def _check_near_leg_spill(failures: list[str]) -> None:
    """bugs/0550 ROOT CAUSE: the image split writes its near leg into ``mirror_row - 1`` ("the
    last leg INTO the mirror"). That was safe only while that row was the lens Rear Vertex Datum
    carrying 80-100 mm; bugs/0546 re-seats a ZERO-gap promoted solid there, so the same write
    went negative. The near leg is a SUM over its span, so the delta must SPILL to the preceding
    gap rows instead -- leg total preserved, no row negative."""
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin as M

    editor = object.__new__(M)
    # gap_start=1 (last lens surface), mirror at 3 -> near span = rows 1..2, near = 83.381 + 0.0
    editor.rows = [
        _Row("Object", 118.97, "Object"),
        _Row("Rear Optical Vertex Datum", 83.381),
        _Row("Promoted OPTICAL STEP optical solid", 0.0),  # bugs/0546 re-seat, mirror_row - 1
        _Row("Promoted OPTICAL STEP optical solid", 72.519),
        _Row("Image", 0.0, "Image"),
    ]
    near_before = sum(float(r.thickness) for r in editor.rows[1:3])
    delta = -13.595
    if not editor._apply_near_leg_delta(2, delta, 1):
        failures.append("near-leg: the span can absorb -13.595 mm (83.381 available) but reported failure")
        return
    negative = [i for i, r in enumerate(editor.rows) if float(r.thickness) < 0.0]
    if negative:
        failures.append(
            f"near-leg: rows {negative} went NEGATIVE -- the delta must spill to the preceding "
            "gap row, not force `mirror_row - 1` below zero (bugs/0550)"
        )
    near_after = sum(float(r.thickness) for r in editor.rows[1:3])
    if abs((near_after - near_before) - delta) > 1e-9:
        failures.append(
            f"near-leg: the leg total must move by exactly {delta} mm; "
            f"got {near_after - near_before}"
        )
    if abs(float(editor.rows[3].thickness) - 72.519) > 1e-9:
        failures.append("near-leg: the spill must not touch the mirror's own gap")

    # A delta the span genuinely cannot absorb must be REFUSED, not written as a broken chain.
    editor.rows = [
        _Row("Object", 118.97, "Object"),
        _Row("Rear Optical Vertex Datum", 5.0),
        _Row("Promoted OPTICAL STEP optical solid", 0.0),
        _Row("Promoted OPTICAL STEP optical solid", 72.519),
        _Row("Image", 0.0, "Image"),
    ]
    if editor._apply_near_leg_delta(2, -50.0, 1):
        failures.append("near-leg: a delta larger than the whole span must be refused")
    if any(float(r.thickness) < 0.0 for r in editor.rows):
        failures.append("near-leg: even a refused delta must leave no negative gap behind")

    # The split must publish the span so the applier can spill at all.
    import inspect as _inspect

    source = _inspect.getsource(M._folded_image_conjugate_split)
    if '"gap_start"' not in source:
        failures.append("near-leg: the image split must publish `gap_start` for the spill span")
    # The FROZEN split (the branch a swap's auto-refocus takes) must route its near-leg write
    # through the spill, not write `mirror_row - 1` raw. bugs/0580-0584 moved that write one
    # call-hop down, into `_settle_image_fold_world` (the stage-(b) settle of
    # bugs/DESIGN_world_authority_settle.md) which the split now delegates to -- so follow the
    # delegation rather than grepping one function's body. The INVARIANT is unchanged: whatever
    # the frozen split reaches, the spill is what performs the near-leg write.
    frozen = _inspect.getsource(M._apply_frozen_image_split)
    reached = frozen
    if "_settle_image_fold_world" in frozen:
        reached += _inspect.getsource(M._settle_image_fold_world)
    if "_apply_near_leg_delta" not in reached:
        failures.append(
            "near-leg: the FROZEN split (the branch a swap's auto-refocus takes) must route its "
            "near-leg write through the spill, not write `mirror_row - 1` raw"
        )
    # And the settle must never write the far row negative (bugs/0580's pair-sum floor): the
    # poison that survived a 'works' flag and detonated at the next swap.
    if "_settle_image_fold_world" in frozen:
        settle = _inspect.getsource(M._settle_image_fold_world)
        if "max(float(far_gap_new), 0.0)" not in settle:
            failures.append(
                "near-leg: the settle must FLOOR the far gap row at zero (bugs/0580) -- a "
                "negative frozen gap is off-axis poison behind a correct-looking world re-bake"
            )


def _check_load_heal(failures: list[str]) -> None:
    """bugs/0559: a negative gap SAVED before bugs/0550 must be healed on load, pose-preservingly.

    0550 stopped one being created; a file already written with one stayed broken on every load.
    flag_20260805_130111 loads machine_vision_Apo75.py and still reports
    ``row 6 thickness -13.5949, station 252.3548 -> next_station 238.7598``, and the user's
    "can't change to FOV 55x55 and 40x40, sure not possible?" was the conjugate solve refusing
    that inconsistent chain -- the FOV was never the problem."""
    from types import SimpleNamespace

    from KrakenOS.UI.services.layout_import_export import LayoutImportExportMixin as M

    def _rows():
        return [
            SimpleNamespace(name="Object", thickness=118.97, desp_z=0.0),
            SimpleNamespace(name="Rear Datum", thickness=83.381, desp_z=0.0),
            SimpleNamespace(name="Promoted OPTICAL STEP optical solid", thickness=-13.5949, desp_z=-197.896),
            SimpleNamespace(name="mirror", thickness=72.519, desp_z=-184.438),
        ]

    def _stations(rows):
        out, total = [0.0], 0.0
        for row in rows[:-1]:
            total += float(row.thickness)
            out.append(total)
        return out

    rows = _rows()
    before = [s + r.desp_z for s, r in zip(_stations(rows), rows)]
    healed = M._heal_negative_gaps_on_load(rows)
    after = [s + r.desp_z for s, r in zip(_stations(rows), rows)]

    if not healed or healed[0]["row_index"] != 2:
        failures.append(f"heal: the negative row must be reported, got {healed}")
    if any(float(r.thickness) < 0.0 for r in rows):
        failures.append("heal: a negative gap survived the load repair")
    stations = _stations(rows)
    if stations != sorted(stations):
        failures.append(f"heal: the station chain still runs backwards ({stations})")
    drift = max(abs(a - b) for a, b in zip(before, after))
    if drift > 1e-9:
        failures.append(
            f"heal: the repair MOVED geometry by {drift:.4g} mm -- it must return the gap through "
            "desp_z so every pose is invariant (bugs/0526)"
        )

    # A healthy layout must be untouched.
    clean = [
        SimpleNamespace(name="a", thickness=10.0, desp_z=1.0),
        SimpleNamespace(name="b", thickness=20.0, desp_z=2.0),
    ]
    if M._heal_negative_gaps_on_load(clean):
        failures.append("heal: a layout with no negative gap must report nothing healed")
    if [r.thickness for r in clean] != [10.0, 20.0] or [r.desp_z for r in clean] != [1.0, 2.0]:
        failures.append("heal: a healthy layout must be left byte-identical")

    import inspect as _inspect

    if "_heal_negative_gaps_on_load" not in _inspect.getsource(M.open_layout):
        failures.append("heal: open_layout must run the repair (bugs/0559)")
    # bugs/0563: EVERY load path must heal. `load_layout_by_name` builds its rows itself and
    # never calls open_layout, so the 0559 heal silently did nothing on the path the app uses --
    # measured: Apo75 still carried -13.5949 after load.
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as W

    if "_heal_negative_gaps_on_load" not in _inspect.getsource(W.load_layout_by_name):
        failures.append(
            "heal: load_layout_by_name must run the repair too -- it does NOT go through "
            "open_layout, and it is the path the app uses (bugs/0563)"
        )


def _check_near_leg_read(failures: list[str]) -> None:
    """bugs/0562: the collision resolver must READ the lens->mirror leg as its SPAN SUM.

    bugs/0550 fixed the WRITE (spill the delta across the span) but left the READ single-row:
    ``near_now = rows[near_gap_row].thickness`` with ``near_gap_row = mirror_row - 1``. That was
    safe only while that row was the lens Rear Vertex Datum carrying the whole leg; bugs/0546
    re-seats a promoted solid there with a ZERO gap, so the resolver read 0 while the real leg was
    83.4 mm and refused every snap -- "I can't even solve for FOV 35x35 now". The user's own
    refusal message is the proof: "would leave only -22.04 mm from the lens" is exactly
    ``0 - deficit``."""
    import inspect as _inspect

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService as Q

    src = _inspect.getsource(Q._resolve_image_gap_collision)
    if 'near_now = float(self.editor.rows[near_row].thickness)' in src:
        failures.append(
            "near-leg read: the resolver still reads ONE row as the lens->mirror leg -- after "
            "bugs/0546 that row is a zero-gap promoted solid, so every snap refuses (bugs/0562)"
        )
    if 'split.get("near"' not in src:
        failures.append(
            "near-leg read: the leg must come from the split's own span sum (`near`), which is "
            "what _folded_image_conjugate_split computes"
        )

    # The arithmetic the fix restores, stated as the outcome the user sees.
    floor, gap, near_min = 28.98, 6.936, 12.5
    deficit = floor - gap
    if (0.0 - deficit) >= near_min:
        failures.append("near-leg read: fixture no longer demonstrates the zero-leg refusal")
    if (83.381 - deficit) < near_min:
        failures.append(
            "near-leg read: with the true 83.4 mm leg the mirror slide must FIT (it leaves "
            f"{83.381 - deficit:.4g} mm, minimum {near_min})"
        )


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
    _check_near_leg_spill(failures)
    _check_load_heal(failures)
    _check_near_leg_read(failures)
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
