#!/usr/bin/env python3
"""Display-free guard for bugs/0131: the live edge-gap overlay must keep showing
after a dragged LED is placed and becomes a camera (sensor + image plane glued).

Why it exists (user flagged it, flag_20260624_083154_091):
  "dragging the LED passed the lens, and the live gap shows up. Placing it and the
   LED now becomes Camera, sensor and image plane attached to it. Drag again no
   longer show live gap."

Root cause: ``_step_overlay_axial_gap`` chose the "previous" component by axial
*center* (largest ``proj_max`` among components whose center sits before the
dragged body's center). Once the LED becomes a camera it gains a glued detector /
image plane that sits INSIDE the camera body (flag geometry: camera STEP
z[159.24, 235.64], glued plane at z=170.72). That buried companion's center is
before the camera center, so it WON the search and produced a bogus negative gap
(159.24 - 170.72 = -11.5 mm) -- an invisible backward arrow inside the body, so
the live spacing read silently vanished.

The fix chooses the previous component by FAR EDGE: a genuine previous must end at
or behind the dragged body's near edge. The glued companion far-overlaps the body
and is rejected, so the gap measures to the real preceding element (here the
object plane at z=0 -> a clean +159.24 mm).

What it checks (against the REAL ``Kraken3DInspector._previous_axial_component``):
  A. No / empty candidates -> None.
  B. The flag geometry: a glued companion buried inside the body is rejected and
     the object plane is chosen -> a POSITIVE gap, not the bogus negative one.
  C. Among several cleanly-preceding candidates the nearest (largest proj_max)
     wins.
  D. Edge semantics: a touching previous (far == near) is admitted; one a hair
     past the near edge is rejected.
  E. Malformed / non-finite extents are skipped, not crashed on.
  F. Source contract -- the overlay delegates to ``_previous_axial_component``,
     reads the near edge (``proj_min`` / ``me_near``), and the helper rejects
     far-overlap via ``overlap_eps``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_camera_live_gap

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector

_previous = Kraken3DInspector._previous_axial_component


def _label(extent):
    return None if extent is None else extent.get("label")


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # --- A: nothing to measure to -> None -----------------------------------
    if _previous(159.24, []) is not None:
        failures.append("A FAIL: empty candidate list should yield no previous")
    if _previous(159.24, None) is not None:
        failures.append("A FAIL: None candidates should yield no previous")

    # --- B: the flag geometry (camera with a glued detector inside it) -------
    # camera STEP near edge = 159.24; the glued image plane sits at 170.72,
    # 11.5 mm INSIDE the body; the real preceding element is the object at 0.
    me_near = 159.24
    flag_extents = [
        {"label": "object", "proj_max": 0.0, "proj_center": 0.0},
        {"label": "detector", "proj_max": 170.72, "proj_center": 170.72},  # buried companion
        {"label": "lens", "proj_max": 331.31, "proj_center": 303.16},
    ]
    prev = _previous(me_near, flag_extents)
    if _label(prev) != "object":
        failures.append(
            f"B FAIL: a glued companion buried in the body must be rejected; "
            f"expected the object plane, got {_label(prev)}"
        )
    elif (me_near - float(prev["proj_max"])) <= 0.0:
        failures.append("B FAIL: the live gap must be POSITIVE (it vanished as a negative gap)")
    if _label(prev) == "detector":
        failures.append("B FAIL: the buried detector won the search (bugs/0131 regression)")

    # --- C: nearest cleanly-preceding candidate wins -------------------------
    multi = [
        {"label": "far", "proj_max": 10.0},
        {"label": "near", "proj_max": 100.0},   # closest below 159.24
        {"label": "mid", "proj_max": 55.0},
    ]
    if _label(_previous(159.24, multi)) != "near":
        failures.append("C FAIL: the nearest preceding component (largest proj_max) should win")

    # --- D: edge semantics ---------------------------------------------------
    touching = [{"label": "touch", "proj_max": 159.24}]
    if _label(_previous(159.24, touching)) != "touch":
        failures.append("D FAIL: a previous touching the near edge (gap 0) must be admitted")
    just_inside = [{"label": "inside", "proj_max": 159.25}]  # a hair past the near edge
    if _previous(159.24, just_inside) is not None:
        failures.append("D FAIL: a component past the near edge must be rejected as overlapping")

    # --- E: malformed / non-finite extents are skipped, not fatal ------------
    messy = [
        {"label": "nofield"},                       # no proj_max
        {"label": "nan", "proj_max": float("nan")},
        {"label": "ok", "proj_max": 42.0},
    ]
    try:
        if _label(_previous(159.24, messy)) != "ok":
            failures.append("E FAIL: malformed extents should be skipped, leaving the valid one")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"E FAIL: malformed extents crashed the helper: {exc!r}")

    # --- F: source contracts -------------------------------------------------
    gap_src = inspect.getsource(Kraken3DInspector._step_overlay_axial_gap)
    if "_previous_axial_component" not in gap_src:
        failures.append("F FAIL: the overlay must delegate to _previous_axial_component")
    if "me_near" not in gap_src or "proj_min" not in gap_src:
        failures.append("F FAIL: the overlay must select by the near edge (proj_min / me_near)")
    if "proj_center" in gap_src:
        failures.append("F FAIL: the overlay must no longer gate the previous on proj_center")
    helper_src = inspect.getsource(Kraken3DInspector._previous_axial_component)
    if "overlap_eps" not in helper_src or "proj_max" not in helper_src:
        failures.append("F FAIL: the helper must reject far-overlap via overlap_eps on proj_max")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0131 camera live edge-gap must survive the LED->camera placement")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] camera live edge-gap measures past the glued detector to the real previous (bugs/0131)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
