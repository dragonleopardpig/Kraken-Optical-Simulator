"""Display-free guard for bugs/0298 -- a model change made in the 3D inspector must mark the
main 2D layout stale, or "Done 2D" silently skips its re-plot.

The user clicked the right-click "Snap detector to image plane (remove defocus)", then "Done 2D",
and the 2D never refreshed. ``finish_stl_placement`` ("Done 2D") re-plots ONLY when
``_stl_placement_dirty`` is set -- and ``_snap_detector_to_image_plane`` rewrote the Image row and
retraced the 3D but never set it. An AST audit found ELEVEN inspector methods with that shape:
they force a retrace (i.e. the prescription changed) yet never mark the 2D stale. The QE solve
paths (bugs/0248) and the STEP import/delete (bugs/0296) had each been patched one at a time; this
is the same bug for the third time, so pin the INVARIANT instead of the instance.

  (A) INVARIANT: no Kraken3DInspector method calls ``refresh_from_editor(force_retrace=True)``
      without also marking the 2D stale (directly, or via ``_apply_model_change``). A twelfth
      action added without the pairing trips this.
  (B) HELPER PAIRS BOTH: ``_apply_model_change`` marks the 2D stale AND forces the retrace.
  (C) THE REPORTED ACTION: ``_snap_detector_to_image_plane`` (the "remove defocus" the user hit)
      routes through it.
  (D) DONE-2D STILL GATES ON THE FLAG: ``finish_stl_placement`` re-plots only when dirty, so the
      flag remains the single "2D is out of date" signal (bugs/0248's contract).

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_model_change_marks_2d_stale
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import ast
import inspect
import pathlib
from dataclasses import dataclass

_SOURCE = pathlib.Path(__file__).resolve().parent / "open3d_inspector.py"
_RETRACE = "refresh_from_editor(force_retrace=True)"
_MARKS = ("_mark_2d_layout_stale()", "_stl_placement_dirty = True", "_apply_model_change()")


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _unpaired_methods() -> list[str]:
    """Inspector methods that force a retrace (the model changed) but never mark the 2D stale."""
    src = _SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    cls = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Kraken3DInspector"
    )
    offenders: list[str] = []
    for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef)]:
        body = ast.get_source_segment(src, fn) or ""
        if _RETRACE not in body:
            continue
        if fn.name == "_apply_model_change":
            continue  # the helper itself -- it IS the pairing (checked separately)
        if not any(mark in body for mark in _MARKS):
            offenders.append(f"{fn.name}:{fn.lineno}")
    return offenders


def validate() -> list[Check]:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    checks: list[Check] = []

    offenders = _unpaired_methods()
    checks.append(Check(
        "INVARIANT: no inspector method forces a retrace without marking the 2D stale",
        not offenders,
        "all model-changing methods pair the retrace with the 2D mark"
        if not offenders
        else f"{len(offenders)} unpaired: {', '.join(offenders)}",
    ))

    helper = inspect.getsource(Kraken3DInspector._apply_model_change)
    retraces = "refresh_from_editor(" in helper and "force_retrace=True" in helper
    paired = "_mark_2d_layout_stale()" in helper and retraces
    checks.append(Check(
        "HELPER PAIRS BOTH: _apply_model_change marks the 2D stale AND forces the retrace",
        paired,
        f"marks={'_mark_2d_layout_stale()' in helper} retraces={retraces}",
    ))

    snap = inspect.getsource(Kraken3DInspector._snap_detector_to_image_plane)
    routed = "_apply_model_change()" in snap
    checks.append(Check(
        "THE REPORTED ACTION: the best-focus snap ('remove defocus') routes through the helper",
        routed,
        f"_snap_detector_to_image_plane uses _apply_model_change: {routed}",
    ))

    done = inspect.getsource(Kraken3DInspector.finish_stl_placement)
    gated = "_stl_placement_dirty" in done and "refresh_plot" in done
    checks.append(Check(
        "DONE-2D STILL GATES ON THE FLAG: finish_stl_placement re-plots only when dirty",
        gated,
        f"gate={'_stl_placement_dirty' in done} replot={'refresh_plot' in done}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate()
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if any(not c.ok for c in checks):
        raise SystemExit(1)
    print("Model-change / 2D-stale pairing validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
