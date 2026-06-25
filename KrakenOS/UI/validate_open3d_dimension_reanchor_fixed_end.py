"""Display-free guard: a re-anchored dimension pins its FIXED end to the stored
``fixed_z`` instead of snapping it back to the live model surface.

bugs/0053 lets a thickness/distance dimension arrow be Ctrl-click re-anchored: the
end nearer the cursor follows the mouse to a picked surface/edge and a plain click
commits a MEASUREMENT-ONLY override (the optical model is untouched). The per-row
override is a SINGLE spec that stores only the MOVED end (``ref_z`` + which
``endpoint``) plus the other end's axial z at pick time (``fixed_z``).

bugs/0147: the drawing path ``reanchored_endpoints`` applied ``ref_z`` to the
moved end but read the FIXED end from the live model surface ``p0``/``p1``,
ignoring ``fixed_z``. For a fresh single re-anchor that coincides, so "re-anchor
the right end" looked correct. But re-anchoring the right and THEN the left
replaced the spec with ``endpoint="start"`` and redrew the right end from the live
``p1`` -- discarding where the user had just placed it ("left arrow reanchor moved
the right arrow"). The wanted position was already in ``fixed_z`` (the value-edit
path uses it); the fix makes the drawing use it too.

This guard pins the contract without any rendering:

  1. A stored ``fixed_z`` overrides a DRIFTED live fixed end for BOTH ``endpoint``
     values (the live ``p0``/``p1`` deliberately differ from ``fixed_z``).
  2. ``measured`` equals ``|ref_z - fixed_z|`` when pinned.
  3. The reported right->left SEQUENCE keeps the right end at its first re-anchor
     (the second pick's ``fixed_z`` = the first draw's right end, as the live drag
     record feeds it), not the live model surface.
  4. No ``fixed_z`` (legacy spec / LED sentinel) falls back to the live end --
     unchanged behaviour, so no regression.
  5. A non-finite / unparseable ``fixed_z`` is ignored (falls back to live).
  6. Source marker: ``reanchored_endpoints`` consults ``fixed_z`` -- so a future
     "simplification" that reverts to the live-only fixed end is caught.

Penta phase 136 (baseline -> 136).
"""

from __future__ import annotations

import inspect
import types

import numpy as np


def _service():
    from KrakenOS.UI.services.open3d_thickness_dimensions import (
        Open3DThicknessDimensionService,
    )

    return Open3DThicknessDimensionService(
        types.SimpleNamespace(editor=None), pv_module=None, billboard_text_actor_cls=None
    )


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    def record(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and bool(passed)
        status = "PASS" if passed else "FAIL"
        notes.append(f"{name} | {status}" + (f" | {detail}" if detail else ""))

    try:
        svc = _service()
    except Exception as exc:  # pragma: no cover - environment guard
        return False, [f"service unavailable: {exc!r}"]

    # Live model surfaces; fixed_z is deliberately set ELSEWHERE so a regression
    # (reading the live end) is distinguishable from honouring fixed_z.
    p0 = np.array([0.0, 0.0, 10.0])
    p1 = np.array([0.0, 0.0, 30.0])

    # --- 1) + 2) stored fixed_z overrides a drifted live fixed end -------------
    q0, q1, measured = svc.reanchored_endpoints(
        p0, p1, {"endpoint": "start", "ref_z": 5.0, "fixed_z": 99.0}
    )
    record(
        "endpoint=start pins the END to fixed_z (not live p1)",
        abs(q0[2] - 5.0) < 1e-9 and abs(q1[2] - 99.0) < 1e-9,
        f"q0z={q0[2]:.6g} q1z={q1[2]:.6g} (live p1z=30)",
    )
    record(
        "endpoint=start measured = |ref_z - fixed_z|",
        abs(measured - 94.0) < 1e-9,
        f"measured={measured:.6g} expected=94",
    )

    q0e, q1e, measured_e = svc.reanchored_endpoints(
        p0, p1, {"endpoint": "end", "ref_z": 42.0, "fixed_z": 77.0}
    )
    record(
        "endpoint=end pins the START to fixed_z (not live p0)",
        abs(q1e[2] - 42.0) < 1e-9 and abs(q0e[2] - 77.0) < 1e-9,
        f"q0z={q0e[2]:.6g} q1z={q1e[2]:.6g} (live p0z=10)",
    )
    record(
        "endpoint=end measured = |ref_z - fixed_z|",
        abs(measured_e - 35.0) < 1e-9,
        f"measured={measured_e:.6g} expected=35",
    )

    # --- 3) the reported right->left SEQUENCE keeps the right where it was put --
    # Step 1: re-anchor the RIGHT (end) to z=50. fixed_z = the live left (p0=10).
    first_q0, first_q1, _ = svc.reanchored_endpoints(
        p0, p1, {"endpoint": "end", "ref_z": 50.0, "fixed_z": float(p0[2])}
    )
    # Step 2: re-anchor the LEFT (start) to z=3. The live drag record now spans the
    # DRAWN endpoints, so the second pick's fixed end is the drawn right (first_q1).
    seq_fixed_z = float(first_q1[2])
    second_q0, second_q1, _ = svc.reanchored_endpoints(
        p0, p1, {"endpoint": "start", "ref_z": 3.0, "fixed_z": seq_fixed_z}
    )
    record(
        "right-then-left sequence keeps the right end at its first re-anchor",
        abs(first_q1[2] - 50.0) < 1e-9
        and abs(second_q1[2] - 50.0) < 1e-9
        and abs(second_q0[2] - 3.0) < 1e-9,
        f"first_rightz={first_q1[2]:.6g} second_rightz={second_q1[2]:.6g} "
        f"(live p1z=30 would be the BUG)",
    )
    record(
        "...and the right end did NOT revert to the live model surface",
        abs(second_q1[2] - float(p1[2])) > 1e-6,
        f"second_rightz={second_q1[2]:.6g} live_p1z={float(p1[2]):.6g}",
    )

    # --- 4) no fixed_z -> falls back to the live end (back-compat, no regression)
    b0, b1, bm = svc.reanchored_endpoints(p0, p1, {"endpoint": "start", "ref_z": 5.0})
    record(
        "no fixed_z, endpoint=start -> END stays at live p1",
        abs(b0[2] - 5.0) < 1e-9 and abs(b1[2] - 30.0) < 1e-9 and abs(bm - 25.0) < 1e-9,
        f"q0z={b0[2]:.6g} q1z={b1[2]:.6g} measured={bm:.6g}",
    )
    c0, c1, cm = svc.reanchored_endpoints(p0, p1, {"endpoint": "end", "ref_z": 42.0})
    record(
        "no fixed_z, endpoint=end -> START stays at live p0",
        abs(c0[2] - 10.0) < 1e-9 and abs(c1[2] - 42.0) < 1e-9 and abs(cm - 32.0) < 1e-9,
        f"q0z={c0[2]:.6g} q1z={c1[2]:.6g} measured={cm:.6g}",
    )

    # --- 5) non-finite / unparseable fixed_z is ignored (falls back to live) ----
    n0, n1, _ = svc.reanchored_endpoints(
        p0, p1, {"endpoint": "start", "ref_z": 5.0, "fixed_z": float("nan")}
    )
    s0, s1, _ = svc.reanchored_endpoints(
        p0, p1, {"endpoint": "start", "ref_z": 5.0, "fixed_z": "bad"}
    )
    record(
        "non-finite / unparseable fixed_z -> END falls back to live p1",
        abs(n1[2] - 30.0) < 1e-9 and abs(s1[2] - 30.0) < 1e-9,
        f"nan_q1z={n1[2]:.6g} str_q1z={s1[2]:.6g}",
    )

    # --- 6) source marker: fixed_z is consulted --------------------------------
    src = inspect.getsource(svc.reanchored_endpoints)
    record(
        "reanchored_endpoints consults fixed_z",
        "fixed_z" in src,
    )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(note)
    print(
        "[PASS] re-anchored dimension pins its fixed end to fixed_z"
        if ok
        else "[FAIL] re-anchored dimension fixed end regressed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
