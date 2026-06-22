#!/usr/bin/env python3
"""Display-free guard for bugs/0106: the click-on-plane FOV "Solve for Thickness"
must take effect on a beam-splitter (machine-vision) scene.

Why it exists (flag_20260622_141959_865 "After changing the FOV by clicking the
FOV plane, it does not take effect"):
  The user's scene is MV 150mm 1X with a 50mm beam-splitter cube BEFORE the single
  lens (reflect arm BARE). Double-clicking the Object plane opens the FOV box;
  "Solve for Thickness" runs a paraxial conjugate solve via
  `QuickEstimationService._paraxial_solution()`. That method called
  `editor._exact_paraxial_solution_for_rows(editor.rows)` on the RAW rows, which
  THROWS on the beam splitter (no clean sequential paraxial form) -> returns None
  -> `_conjugate_pair` None -> `fov_solve` returns (False, "no real-image
  conjugate") and the scene is left unchanged. This is a sibling of bugs/0104 (the
  object-plane magnification), in a code path 0104 did not touch.

  Fix: `_paraxial_solution` straightens to the transmissive (straight-through)
  reference whenever `_layout_needs_paraxial_reference()` is True (mirror OR beam
  splitter OR promoted mesh solid), the same reference the 0104 magnification fix
  and every other first-order consumer use. The single imaging arm's solve then
  succeeds, so the FOV thickness solve takes effect.

What it checks:
  A. On the beam-splitter scene, `_paraxial_solution()`/`focal_length()` are now a
     finite, non-zero solution (was None -- the bug) and the layout reports
     `_layout_needs_paraxial_reference()`=True.
  B. `fov_solve("object", "thickness", ...)` returns ok=True and moves the object
     thickness row (the change "takes effect").
  C. A plain refractive finite scene is unchanged (focal length finite, fov_solve
     ok), and `_paraxial_solution` is gated on `_layout_needs_paraxial_reference`
     (source check) so it cannot silently regress to raw-rows-only.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_fov_solve_after_promote

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
import types

import numpy as np

from KrakenOS.UI.validate_open3d_object_plane_after_promote import (
    _editor,
    _plain_specs,
    _splitter_specs,
)


def _qe(editor):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    # fov_solve / _paraxial_solution / focal_length only touch `self.editor`, so a
    # minimal stand-in inspector is enough to drive them display-free.
    fake_inspector = types.SimpleNamespace(editor=editor)
    return QuickEstimationService(fake_inspector)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # A) The beam-splitter scene now has a finite paraxial solution.
    bs_editor = _editor(_splitter_specs())
    bs_qe = _qe(bs_editor)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        needs_ref = bool(bs_editor._layout_needs_paraxial_reference(bs_editor.rows))
        sol = bs_qe._paraxial_solution()
        focal = bs_qe.focal_length()
    if not needs_ref:
        failures.append("FAIL: the beam-splitter scene should report _layout_needs_paraxial_reference()=True")
    if sol is None:
        failures.append("FAIL: _paraxial_solution() must straighten the splitter and return a solution (got None)")
    if focal is None or not np.isfinite(focal) or abs(focal) < 1e-9:
        failures.append(f"FAIL: focal_length() must be finite & non-zero on the splitter scene, got {focal!r}")

    # B) The FOV thickness solve takes effect (ok=True + the object gap moves).
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        obj_row = bs_qe.object_thickness_row()
        before = float(bs_editor.rows[obj_row].thickness) if obj_row is not None else None
        ok, msg = bs_qe.fov_solve("object", "thickness", 20.0, None, None)
        after = float(bs_editor.rows[obj_row].thickness) if obj_row is not None else None
    if not ok:
        failures.append(f"FAIL: FOV 'Solve for Thickness' must succeed on the splitter scene, got: {msg}")
    elif before is not None and after is not None and abs(after - before) < 1e-9:
        failures.append(
            f"FAIL: FOV thickness solve did not move the object gap (stayed {before:.6g} mm) -- no effect")

    # C) Regression: a plain refractive finite scene is unchanged + solves.
    plain_editor = _editor(_plain_specs())
    plain_qe = _qe(plain_editor)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        plain_focal = plain_qe.focal_length()
        plain_ok, plain_msg = plain_qe.fov_solve("object", "thickness", 20.0, None, None)
    if plain_focal is None or not np.isfinite(plain_focal) or abs(plain_focal) < 1e-9:
        failures.append(f"FAIL: plain MV 150 1X focal length regressed (got {plain_focal!r})")
    if not plain_ok:
        failures.append(f"FAIL: plain MV 150 1X FOV thickness solve regressed, got: {plain_msg}")

    src = inspect.getsource(type(bs_qe)._paraxial_solution)
    if "_layout_needs_paraxial_reference" not in src:
        failures.append(
            "FAIL: _paraxial_solution must straighten on _layout_needs_paraxial_reference "
            "(beam splitter / promoted solid), not solve the raw rows")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0106 FOV thickness solve must take effect on a beam-splitter scene")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] beam-splitter scene now has a paraxial solution -> FOV 'Solve for Thickness' "
          "takes effect (bugs/0106)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
