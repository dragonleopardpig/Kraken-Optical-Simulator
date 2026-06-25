#!/usr/bin/env python3
"""Display-free guard for the Quick Estimation DESIGN-mode solve ("what lens do I
need?"): invert the first-order conjugate relations for the FOCAL LENGTH from a set
of pinned constraints, with a degrees-of-freedom accountant.

Design mode treats the lens as UNKNOWN, so it is a THIN-LENS first-order target
(principal planes ppa = ppp = 0). The conjugate geometry is 2 DOF:

    s_o = f (1 + 1/m)     s_i = f (1 + m)     T = s_o + s_i     (m = |mag| > 0)

solved by a magnification constraint (magnification OR object FOV via the fixed
sensor) + a scale constraint (object/image distance or total track), or by two
lengths (which jointly give m and the scale). The DOF accountant and the solve are
the SAME code path, so the UI's "balanced / pin one more / release one" indicator
can never disagree with the computed lens.

What it checks (pure function ``resolve_design_system`` -- no editor, no display):
  A-E  every valid 2-pin combination recovers the known thin-lens system
       (f=50, m=0.5 -> s_o=150, s_i=75, T=225).
  F    an object-FOV pin folds to a magnification through the fixed sensor.
  G-H  under-constrained inputs (one pin) report "under".
  I-J  over-constrained inputs (3 lengths / magnification + 2 lengths) report "over".
  K    a magnification that conflicts with the FOV pin reports "over".
  L    an object-FOV pin without a sensor reports "invalid".
  M-N  non-physical geometry / magnification <= 0 report "invalid".
  O    the balanced solution satisfies the thin-lens forward relations (consistency).
  P    contract: the service exposes solve_design + the DESIGN_* quantity vocabulary.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_quick_estimation_focal_solve

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from KrakenOS.UI.services.quick_estimation import (
    DESIGN_IMAGE_DISTANCE,
    DESIGN_MAGNIFICATION,
    DESIGN_OBJECT_DISTANCE,
    DESIGN_OBJECT_FOV_SEMI,
    DESIGN_TOTAL_TRACK,
    QuickEstimationService,
    design_quantity_states,
    resolve_design_system,
)


def _approx(a, b, tol=1e-6) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return False


def run_checks():
    failures = []

    def expect_balanced(name, pins, sensor_semi, *, f, s_o, s_i, m, tt):
        r = resolve_design_system(pins, sensor_semi=sensor_semi)
        if r.get("status") != "balanced":
            failures.append(f"{name} FAIL: expected balanced, got {r.get('status')} ({r.get('message')})")
            return
        for key, want in (
            ("focal_length", f), (DESIGN_OBJECT_DISTANCE, s_o), (DESIGN_IMAGE_DISTANCE, s_i),
            (DESIGN_MAGNIFICATION, m), (DESIGN_TOTAL_TRACK, tt),
        ):
            if not _approx(r.get(key), want, tol=1e-4):
                failures.append(f"{name} FAIL: {key}={r.get(key)} expected {want}")

    def expect_status(name, pins, sensor_semi, status):
        r = resolve_design_system(pins, sensor_semi=sensor_semi)
        if r.get("status") != status:
            failures.append(f"{name} FAIL: expected {status}, got {r.get('status')} ({r.get('message')})")

    # Known thin-lens system: f=50, m=0.5 -> s_o=150, s_i=75, T=225.
    F, SO, SI, M, TT = 50.0, 150.0, 75.0, 0.5, 225.0
    expect_balanced("A magnification+object_distance", {DESIGN_MAGNIFICATION: M, DESIGN_OBJECT_DISTANCE: SO}, None, f=F, s_o=SO, s_i=SI, m=M, tt=TT)
    expect_balanced("B magnification+image_distance", {DESIGN_MAGNIFICATION: M, DESIGN_IMAGE_DISTANCE: SI}, None, f=F, s_o=SO, s_i=SI, m=M, tt=TT)
    expect_balanced("C magnification+total_track", {DESIGN_MAGNIFICATION: M, DESIGN_TOTAL_TRACK: TT}, None, f=F, s_o=SO, s_i=SI, m=M, tt=TT)
    expect_balanced("D object+image distance", {DESIGN_OBJECT_DISTANCE: SO, DESIGN_IMAGE_DISTANCE: SI}, None, f=F, s_o=SO, s_i=SI, m=M, tt=TT)
    expect_balanced("E object_distance+total_track", {DESIGN_OBJECT_DISTANCE: SO, DESIGN_TOTAL_TRACK: TT}, None, f=F, s_o=SO, s_i=SI, m=M, tt=TT)

    # F: object FOV folds to magnification via the fixed sensor (semi=5.5 -> m=5.5/11=0.5).
    rF = resolve_design_system({DESIGN_OBJECT_FOV_SEMI: 11.0, DESIGN_OBJECT_DISTANCE: SO}, sensor_semi=5.5)
    if rF.get("status") != "balanced" or not _approx(rF.get("focal_length"), F, tol=1e-4):
        failures.append(f"F FAIL: FOV->mag fold expected f={F}, got {rF.get('status')} f={rF.get('focal_length')}")
    elif not _approx(rF.get(DESIGN_OBJECT_FOV_SEMI), 11.0, tol=1e-4):
        failures.append(f"F FAIL: object_fov_semi readout = {rF.get(DESIGN_OBJECT_FOV_SEMI)} expected 11.0")

    # G-H: under-constrained.
    expect_status("G under magnification-only", {DESIGN_MAGNIFICATION: M}, None, "under")
    expect_status("H under one-length", {DESIGN_OBJECT_DISTANCE: SO}, None, "under")

    # I-J: over-constrained.
    expect_status("I over three-lengths", {DESIGN_OBJECT_DISTANCE: SO, DESIGN_IMAGE_DISTANCE: SI, DESIGN_TOTAL_TRACK: TT}, None, "over")
    expect_status("J over magnification+two-lengths", {DESIGN_MAGNIFICATION: M, DESIGN_OBJECT_DISTANCE: SO, DESIGN_IMAGE_DISTANCE: SI}, None, "over")

    # K: magnification conflicts with FOV (sensor_semi=10 -> m_fov=10/11 != 0.5).
    expect_status("K over mag/FOV-conflict", {DESIGN_MAGNIFICATION: M, DESIGN_OBJECT_FOV_SEMI: 11.0}, 10.0, "over")

    # L: object FOV without a sensor.
    expect_status("L invalid FOV-no-sensor", {DESIGN_OBJECT_FOV_SEMI: 11.0, DESIGN_OBJECT_DISTANCE: SO}, None, "invalid")

    # M-N: non-physical.
    expect_status("M invalid total<object", {DESIGN_OBJECT_DISTANCE: 200.0, DESIGN_TOTAL_TRACK: 100.0}, None, "invalid")
    expect_status("N invalid magnification<=0", {DESIGN_MAGNIFICATION: -0.5, DESIGN_OBJECT_DISTANCE: SO}, None, "invalid")

    # O: balanced solution satisfies the thin-lens forward relations (consistency).
    r = resolve_design_system({DESIGN_MAGNIFICATION: 0.5, DESIGN_OBJECT_DISTANCE: 150.0}, sensor_semi=None)
    if r.get("status") == "balanced":
        f, s_o, s_i, m = (r["focal_length"], r[DESIGN_OBJECT_DISTANCE], r[DESIGN_IMAGE_DISTANCE], r[DESIGN_MAGNIFICATION])
        if not (_approx(s_o, f * (1.0 + 1.0 / m)) and _approx(s_i, f * (1.0 + m)) and _approx(r[DESIGN_TOTAL_TRACK], s_o + s_i)):
            failures.append("O FAIL: balanced solution violates the thin-lens forward relations")
    else:
        failures.append("O FAIL: reference solve was not balanced")

    # P: service contract.
    if not hasattr(QuickEstimationService, "solve_design"):
        failures.append("P FAIL: QuickEstimationService must expose solve_design")

    # Q-T: gray-out states (design_quantity_states) -- the UI disables the
    # constraints the user can no longer change once enough are pinned.
    def state_of(states, q):
        return (states.get(q) or {}).get("state")

    # Q: a lone magnification pin locks its FOV twin, leaves the lengths available.
    sQ = design_quantity_states({DESIGN_MAGNIFICATION: 0.5}, sensor_semi=5.5)
    if state_of(sQ, DESIGN_MAGNIFICATION) != "pinned":
        failures.append(f"Q FAIL: magnification should read pinned, got {state_of(sQ, DESIGN_MAGNIFICATION)}")
    if state_of(sQ, DESIGN_OBJECT_FOV_SEMI) != "locked":
        failures.append(f"Q FAIL: object FOV should lock when magnification is pinned (same DOF), got {state_of(sQ, DESIGN_OBJECT_FOV_SEMI)}")
    if any(state_of(sQ, q) != "available" for q in (DESIGN_OBJECT_DISTANCE, DESIGN_IMAGE_DISTANCE, DESIGN_TOTAL_TRACK)):
        failures.append("Q FAIL: the three lengths should stay available with only a magnification pinned")

    # R: a balanced system locks every unpinned quantity AND carries its solved value.
    sR = design_quantity_states({DESIGN_MAGNIFICATION: 0.5, DESIGN_OBJECT_DISTANCE: 150.0}, sensor_semi=None)
    for q in (DESIGN_IMAGE_DISTANCE, DESIGN_TOTAL_TRACK, DESIGN_OBJECT_FOV_SEMI):
        if state_of(sR, q) != "locked":
            failures.append(f"R FAIL: {q} should lock once the system is balanced, got {state_of(sR, q)}")
    if not _approx((sR.get(DESIGN_IMAGE_DISTANCE) or {}).get("value"), 75.0, tol=1e-4):
        failures.append("R FAIL: a locked quantity in a balanced system must carry its solved value (image_distance=75)")

    # S: a lone length pin leaves everything else available (nothing determined yet).
    sS = design_quantity_states({DESIGN_OBJECT_DISTANCE: 150.0}, sensor_semi=5.5)
    if any(state_of(sS, q) != "available" for q in (DESIGN_MAGNIFICATION, DESIGN_IMAGE_DISTANCE, DESIGN_TOTAL_TRACK, DESIGN_OBJECT_FOV_SEMI)):
        failures.append("S FAIL: with one length pinned, every other quantity should still be available")

    # T: an object-FOV pin locks the magnification twin.
    sT = design_quantity_states({DESIGN_OBJECT_FOV_SEMI: 11.0}, sensor_semi=5.5)
    if state_of(sT, DESIGN_OBJECT_FOV_SEMI) != "pinned" or state_of(sT, DESIGN_MAGNIFICATION) != "locked":
        failures.append("T FAIL: pinning object FOV must lock magnification (same DOF)")

    # U: UI contract -- the reusable widget + the one-call service view the left panel
    # and the FOV / detector popups all bind to, plus the apply-to-layout path.
    for method in ("design_constraint_view", "apply_design"):
        if not hasattr(QuickEstimationService, method):
            failures.append(f"U FAIL: QuickEstimationService must expose {method}")
    try:
        from KrakenOS.UI.panels.design_constraint_controls import DesignConstraintControls
        for method in ("build", "recompute", "apply"):
            if not hasattr(DesignConstraintControls, method):
                failures.append(f"U FAIL: DesignConstraintControls must expose {method}")
    except Exception as exc:
        failures.append(f"U FAIL: DesignConstraintControls must import (got {exc!r})")

    # V: apply_design writes the solved conjugates into the layout rows (mutation, not
    # just text). Drives the real service against a stub editor.
    import types as _types

    rows = [_types.SimpleNamespace(thickness=10.0, diameter=11.0),
            _types.SimpleNamespace(thickness=0.0, diameter=11.0),
            _types.SimpleNamespace(thickness=10.0, diameter=11.0)]
    stub_ed = _types.SimpleNamespace(rows=rows)
    svc = QuickEstimationService(_types.SimpleNamespace(editor=stub_ed))
    ok, _msg = svc.apply_design({DESIGN_MAGNIFICATION: 0.5, DESIGN_OBJECT_DISTANCE: 150.0})
    if not ok:
        failures.append("V FAIL: apply_design should succeed on a balanced design")
    elif not (_approx(rows[0].thickness, 150.0, tol=1e-4) and _approx(rows[-2].thickness, 75.0, tol=1e-4)):
        failures.append(f"V FAIL: apply_design must write object=150 / image=75 (got {rows[0].thickness}/{rows[-2].thickness})")
    ok_bad, _ = svc.apply_design({DESIGN_MAGNIFICATION: 0.5})  # under-constrained
    if ok_bad:
        failures.append("V FAIL: apply_design must refuse an under-constrained design")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] Quick Estimation design-mode focal solve")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Quick Estimation design-mode focal solve (solve-for-EFL + DOF accountant)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
