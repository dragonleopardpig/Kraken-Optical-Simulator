#!/usr/bin/env python3
"""Display-free guard: the single-axis CA->optical-axis snap auto-completes even when
``_optical_axis_pick_records`` is empty at snap time (bugs/0346).

User report (flag_20260717_160019_506, build-stamped 0815ab71 -- a FRESH app, so NOT
stale): "right click snap to optical axis still not working, optical axis no highlight,
click on it no snap."

Root cause
----------
  ``_optical_axis_pick_records`` is (re)populated ONLY by a scene refresh
  (open3d_scene_refresh -> ``_add_optical_axis_pick_overlays``). When the right-click
  CA snap fires before that refresh has run, the list is still empty, so
  ``_single_optical_axis_pick_info`` returned ``None`` and the snap fell through to the
  bugs/0337 two-step "click the dotted optical axis" pick -- which is exactly the
  unusable state 0337 was written to eliminate: near the opening the axis is buried
  inside the body (no hover highlight) and its only visible stubs sit in the far screen
  corners outside click tolerance. The user is stranded ("no highlight, click no snap").

  A headless probe on the user's single-axis scene (machine_vision_150mm_test) proved
  it: ``_optical_axis_pick_records`` n=0 at snap time, yet
  ``_optical_axis_records_for_3d(None)`` returns exactly one ``axis:global`` record.

Fix
---
  ``_single_optical_axis_pick_info`` falls back to ``_optical_axis_records_for_3d(None)``
  -- the SAME source ``_add_optical_axis_pick_overlays`` derives the pick records from --
  when ``_optical_axis_pick_records`` yields no usable records, so the single-axis
  auto-complete no longer depends on refresh timing. A scene with genuinely DISTINCT
  optical axes still returns ``None`` (keep the explicit disambiguating click) -- but a
  single axis a mirror merely FOLDS into ``axis:global:reflected*`` segments counts as one
  axis and auto-completes (bugs/0347). A populated pick list is used directly (no extra
  work).

What it checks
--------------
  1. Empty pick list + SINGLE-axis source -> an apply-ready payload (the fix).
  2. Empty pick list + genuinely DISTINCT axes -> None; folded segments of ONE axis
     (axis:global + axis:global:reflected*) -> payload (bugs/0347).
  3. Empty pick list + empty source -> None; a source that RAISES -> None (never leaks).
  4. A populated pick list is used directly -- the fallback source is NOT consulted.
  5. Module helper ``_usable_axis_pick_records`` filters to valid Nx3-point records.
  6. Source contract: ``_single_optical_axis_pick_info`` consults
     ``_optical_axis_records_for_3d`` as an empty-list fallback.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ca_snap_autocomplete_fallback

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types

import numpy as np


def _closest(pts, c):
    c = np.asarray(c, dtype=float).reshape(-1)[:3]
    return np.asarray([0.0, 0.0, float(c[2])]), np.asarray([0.0, 0.0, 1.0])


def _axis_record(axis_id, y=0.0):
    return {
        "axis_id": axis_id,
        "axis_label": "Optical Axis",
        "points": np.asarray([[0.0, y, -100.0], [0.0, y, 100.0]], dtype=float),
    }


def _stub(pick_records, source_records, *, source_raises=False):
    """A minimal stand-in for the FA service carrying only what the snap info touches."""
    calls = {"source": 0}

    def _source(_bundle):
        calls["source"] += 1
        if source_raises:
            raise RuntimeError("source unavailable")
        return list(source_records or [])

    svc = types.SimpleNamespace(
        _optical_axis_pick_records=list(pick_records or []),
        _optical_axis_records_for_3d=_source,
        editor=types.SimpleNamespace(_closest_polyline_point_and_direction=_closest),
    )
    return svc, calls


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services import open3d_face_assignment as fa_mod

    Svc = fa_mod.Open3DFaceAssignmentService
    info = Svc._single_optical_axis_pick_info
    failures: list[str] = []

    # 1) Empty pick list + single-axis source -> payload (the bugs/0346 fix).
    svc, calls = _stub([], [_axis_record("axis:global")])
    out = info(svc, (5.0, 1.0, 2.0))
    if not isinstance(out, dict):
        failures.append(
            "FAIL(1): empty _optical_axis_pick_records + a single-axis source must still "
            "yield a one-click payload (bugs/0346) -- got None (the pre-fix stuck-armed bug)"
        )
    else:
        if str(out.get("axis_id", "")) != "axis:global":
            failures.append(f"FAIL(1): fallback payload must carry the axis id, got {out.get('axis_id')!r}")
        pw = np.asarray(out.get("picked_world", []), dtype=float).reshape(-1)
        if pw.size < 3 or not np.allclose(pw[:3], [5.0, 1.0, 2.0]):
            failures.append("FAIL(1): picked_world must be the opening centre (perpendicular-foot target)")
    if calls["source"] < 1:
        failures.append("FAIL(1): the empty pick list must consult the _optical_axis_records_for_3d fallback")

    # 2) Empty pick list + genuinely DISTINCT axes -> None (keep the two-step pick); a
    # single axis a mirror merely FOLDS into reflected segments -> payload (bugs/0347).
    svc, _c = _stub([], [_axis_record("axis:global"), _axis_record("axis:ray:0:segment:2", y=10.0)])
    if info(svc, (0.0, 0.0, 0.0)) is not None:
        failures.append("FAIL(2): several DISTINCT optical axes in the fallback source must NOT auto-pick")
    svc, _c = _stub([], [_axis_record("axis:global"), _axis_record("axis:global:reflected", y=10.0)])
    if info(svc, (0.0, 0.0, 0.0)) is None:
        failures.append(
            "FAIL(2): a single axis FOLDED into axis:global + axis:global:reflected segments "
            "must auto-complete, not disambiguate (bugs/0347)"
        )

    # 3) Empty pick list + empty source -> None; source that raises -> None.
    svc, _c = _stub([], [])
    if info(svc, (0.0, 0.0, 0.0)) is not None:
        failures.append("FAIL(3): empty pick list + empty source must return None")
    svc, _c = _stub([], None, source_raises=True)
    if info(svc, (0.0, 0.0, 0.0)) is not None:
        failures.append("FAIL(3): a source that raises must be swallowed and yield None (never leak)")

    # 4) A populated pick list is used directly -- the fallback source is NOT consulted.
    svc, calls = _stub([_axis_record("axis:global")], [_axis_record("axis:decoy", y=99.0)])
    out = info(svc, (1.0, 2.0, 3.0))
    if not isinstance(out, dict) or str(out.get("axis_id", "")) != "axis:global":
        failures.append("FAIL(4): a populated pick list must be used directly (single axis -> payload)")
    if calls["source"] != 0:
        failures.append("FAIL(4): a populated pick list must NOT consult the fallback source")

    # 5) Module helper filters to valid Nx3-point records.
    usable = fa_mod._usable_axis_pick_records([
        _axis_record("axis:global"),
        {"axis_id": "bad:one_point", "points": np.asarray([[0.0, 0.0, 0.0]], dtype=float)},
        {"axis_id": "bad:no_points"},
        {"axis_id": "bad:2d_short", "points": np.asarray([[0.0, 0.0], [1.0, 1.0]], dtype=float)},
    ])
    ids = [str(rec.get("axis_id", "")) for rec, _pts in usable]
    if ids != ["axis:global"]:
        failures.append(f"FAIL(5): _usable_axis_pick_records must keep only valid Nx3 records, got {ids!r}")
    if fa_mod._usable_axis_pick_records(None) != []:
        failures.append("FAIL(5): _usable_axis_pick_records(None) must return []")

    # 6) Source contract: the empty-list fallback goes through _optical_axis_records_for_3d.
    src = inspect.getsource(info)
    if "_optical_axis_records_for_3d" not in src:
        failures.append(
            "FAIL(6): _single_optical_axis_pick_info must fall back to "
            "_optical_axis_records_for_3d so the single-axis snap is refresh-timing independent"
        )
    if "_usable_axis_pick_records" not in src:
        failures.append("FAIL(6): _single_optical_axis_pick_info must parse records via _usable_axis_pick_records")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] single-axis CA->optical-axis snap does not auto-complete when the "
              "pick-record list is empty at snap time")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] the single-axis CA->optical-axis snap auto-completes even when "
          "_optical_axis_pick_records is empty at snap time -- it rebuilds from "
          "_optical_axis_records_for_3d, so it no longer depends on refresh timing (bugs/0346)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
