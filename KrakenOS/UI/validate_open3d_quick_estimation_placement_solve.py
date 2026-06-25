#!/usr/bin/env python3
"""Display-free guard for the Quick Estimation PLACEMENT-mode solve (fixed lens).

The lens is FIXED (known focal length + real cardinal points ppa/ppp), so the conjugate
is 1 DOF: pin ONE of {object distance, image distance, magnification, object FOV} and the
rest are determined AND in focus. Apply is focus-consistent (no lens swap). Total track is
an output only (a track has two conjugate positions when the lens is fixed -- ambiguous).

What it checks (pure ``resolve_placement_system`` / ``placement_quantity_states`` + a
stubbed-lens ``apply_placement`` -- no editor paraxial, no display):
  A-D  each single pin (magnification / object distance / image distance / object FOV)
       recovers the known thin-lens system (f=50 -> s_o=150, s_i=75, m=0.5).
  E    non-zero cardinals (ppa=10, ppp=8) are honoured in both directions.
  F-G  under (no pin) / over (two pins -- only 1 DOF) are reported.
  H    a total-track pin is rejected (not a placement constraint, lens fixed).
  I    an object inside the front focal point is invalid (no real image).
  J    gray-out: one pin balances and locks the rest; total track is always locked
       (output); no pins leaves the four pinnables available.
  K    apply_placement writes object=150/image=75 into the rows and refuses under.
  L    service contract: placement_constraint_view + apply_placement.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_quick_estimation_placement_solve

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import types

from KrakenOS.UI.services.quick_estimation import (
    DESIGN_IMAGE_DISTANCE,
    DESIGN_MAGNIFICATION,
    DESIGN_OBJECT_DISTANCE,
    DESIGN_OBJECT_FOV_SEMI,
    DESIGN_TOTAL_TRACK,
    QuickEstimationService,
    placement_quantity_states,
    resolve_placement_system,
)


def _approx(a, b, tol=1e-4) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return False


def run_checks():
    failures = []
    F = 50.0

    def expect(name, pins, *, s_o, s_i, m, ppa=0.0, ppp=0.0, sensor_semi=None):
        r = resolve_placement_system(pins, focal_length=F, ppa=ppa, ppp=ppp, sensor_semi=sensor_semi)
        if r.get("status") != "balanced":
            failures.append(f"{name} FAIL: expected balanced, got {r.get('status')} ({r.get('message')})")
            return
        if not (_approx(r.get(DESIGN_OBJECT_DISTANCE), s_o) and _approx(r.get(DESIGN_IMAGE_DISTANCE), s_i) and _approx(r.get(DESIGN_MAGNIFICATION), m)):
            failures.append(f"{name} FAIL: got s_o={r.get(DESIGN_OBJECT_DISTANCE)} s_i={r.get(DESIGN_IMAGE_DISTANCE)} m={r.get(DESIGN_MAGNIFICATION)} (want {s_o}/{s_i}/{m})")

    def expect_status(name, pins, status, *, sensor_semi=None):
        r = resolve_placement_system(pins, focal_length=F, sensor_semi=sensor_semi)
        if r.get("status") != status:
            failures.append(f"{name} FAIL: expected {status}, got {r.get('status')} ({r.get('message')})")

    # A-D: thin-lens single-pin solves (f=50 -> s_o=150, s_i=75, m=0.5).
    expect("A magnification", {DESIGN_MAGNIFICATION: 0.5}, s_o=150.0, s_i=75.0, m=0.5)
    expect("B object distance", {DESIGN_OBJECT_DISTANCE: 150.0}, s_o=150.0, s_i=75.0, m=0.5)
    expect("C image distance", {DESIGN_IMAGE_DISTANCE: 75.0}, s_o=150.0, s_i=75.0, m=0.5)
    expect("D object FOV", {DESIGN_OBJECT_FOV_SEMI: 11.0}, s_o=150.0, s_i=75.0, m=0.5, sensor_semi=5.5)

    # E: real cardinals (ppa=10, ppp=8): m=0.5 -> s_o=140, s_i=83; and the inverse.
    expect("E mag w/ cardinals", {DESIGN_MAGNIFICATION: 0.5}, s_o=140.0, s_i=83.0, m=0.5, ppa=10.0, ppp=8.0)
    rE = resolve_placement_system({DESIGN_OBJECT_DISTANCE: 140.0}, focal_length=F, ppa=10.0, ppp=8.0)
    if not (rE.get("status") == "balanced" and _approx(rE.get(DESIGN_MAGNIFICATION), 0.5) and _approx(rE.get(DESIGN_IMAGE_DISTANCE), 83.0)):
        failures.append(f"E FAIL: object-distance inverse with cardinals -> {rE.get('status')} m={rE.get(DESIGN_MAGNIFICATION)} s_i={rE.get(DESIGN_IMAGE_DISTANCE)}")

    # F-G: DOF accounting.
    expect_status("F under no-pin", {}, "under")
    expect_status("G over two-pins", {DESIGN_MAGNIFICATION: 0.5, DESIGN_OBJECT_DISTANCE: 150.0}, "over")
    # H: total track is not a placement pin.
    expect_status("H over total-track", {DESIGN_TOTAL_TRACK: 225.0}, "over")
    # I: object inside the front focal point.
    expect_status("I invalid inside-focal", {DESIGN_OBJECT_DISTANCE: 30.0}, "invalid")

    # J: gray-out states.
    def state_of(states, q):
        return (states.get(q) or {}).get("state")

    sJ = placement_quantity_states({DESIGN_MAGNIFICATION: 0.5}, focal_length=F)
    if state_of(sJ, DESIGN_MAGNIFICATION) != "pinned":
        failures.append("J FAIL: pinned magnification should read pinned")
    for q in (DESIGN_OBJECT_DISTANCE, DESIGN_IMAGE_DISTANCE, DESIGN_OBJECT_FOV_SEMI, DESIGN_TOTAL_TRACK):
        if state_of(sJ, q) != "locked":
            failures.append(f"J FAIL: {q} should lock once one constraint balances the fixed lens (got {state_of(sJ, q)})")
    sJ0 = placement_quantity_states({}, focal_length=F)
    if state_of(sJ0, DESIGN_TOTAL_TRACK) != "locked":
        failures.append("J FAIL: total track is an output -- always locked in placement")
    if any(state_of(sJ0, q) != "available" for q in (DESIGN_OBJECT_DISTANCE, DESIGN_IMAGE_DISTANCE, DESIGN_MAGNIFICATION, DESIGN_OBJECT_FOV_SEMI)):
        failures.append("J FAIL: with no pins the four placement pins should be available")

    # K: apply_placement mutates rows (stub the fixed-lens cardinals).
    rows = [types.SimpleNamespace(thickness=10.0, diameter=11.0),
            types.SimpleNamespace(thickness=0.0, diameter=11.0),
            types.SimpleNamespace(thickness=10.0, diameter=11.0)]
    svc = QuickEstimationService(types.SimpleNamespace(editor=types.SimpleNamespace(rows=rows)))
    svc._placement_lens_cardinals = lambda: (50.0, 0.0, 0.0)
    ok, _msg = svc.apply_placement({DESIGN_MAGNIFICATION: 0.5})
    if not ok:
        failures.append("K FAIL: apply_placement should succeed on a single pin")
    elif not (_approx(rows[0].thickness, 150.0) and _approx(rows[-2].thickness, 75.0)):
        failures.append(f"K FAIL: apply_placement must write object=150/image=75 (got {rows[0].thickness}/{rows[-2].thickness})")
    ok_bad, _ = svc.apply_placement({})
    if ok_bad:
        failures.append("K FAIL: apply_placement must refuse an unpinned (under-constrained) system")

    # L: service contract.
    for method in ("placement_constraint_view", "apply_placement"):
        if not hasattr(QuickEstimationService, method):
            failures.append(f"L FAIL: QuickEstimationService must expose {method}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] Quick Estimation placement-mode solve (fixed lens)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Quick Estimation placement-mode solve (fixed-lens 1-DOF + focus-consistent apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
