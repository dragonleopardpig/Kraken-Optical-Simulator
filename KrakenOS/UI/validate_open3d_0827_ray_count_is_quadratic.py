"""Guard for bugs/0827 -- the preview ray count costs N SQUARED, and now says so.

Measured on a real 25.7-minute om05a session (5848 timing events): 16 traces cost 448 s,
one lens swap cost 150 s, and 91% of all bundle time was 78 bundles x 361 rays. All nine
scene refreshes together cost 31 s, so RENDERING was never the problem -- ray volume was.
NsTraceLoop already runs at 9.9 ms/ray against the 80 ms/ray of the bugs/0166 era, so the
earlier cell-normal cache and decimated proxy are working; what remained was the dial.

``_full_pupil_grid_xy`` builds an N x N grid from ``ray_count``, and the combo offers
5..41 -- 25 to 1681 rays per bundle, a 67x range behind one number that looks linear.

Two fixes, both guarded here:
  * the Ray count LABEL states rays/bundle and an estimated trace time, before it is paid;
  * a SOLVE or SWAP iterates at a sparse fan, the same transient-clamp shape the drag
    (0024), promote (0105) and folded (0410) overrides already use.

Checks (display-free, pure arithmetic + source structure):
  A  the cost is quadratic, and the combo's own range spans 25..1681;
  B  the estimate scales with N squared, and 31 -> 9 is the ~12x it measured;
  C  the hint names rays AND time, and escalates to minutes where minutes are real;
  D  the clamp NEVER raises a user's choice -- someone who picked 5 keeps 5;
  E  the clamp is wired into _current_ray_count's override chain;
  F  the solve and the swap both SET and CLEAR it -- a leaked clamp would silently
     degrade every later trace, which is worse than the slowness it fixes;
  G  malformed input degrades instead of raising.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0827_ray_count_is_quadratic
"""

from __future__ import annotations

import inspect as _inspect
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.trace_cost import (
        NS_MS_PER_RAY,
        SEQ_MS_PER_RAY,
        SOLVE_PREVIEW_RAY_COUNT,
        compare_ray_counts,
        estimate_trace_seconds,
        format_ray_count_hint,
        rays_per_bundle,
        solve_preview_ray_count,
    )
    from KrakenOS.UI.source_trace_helpers import RAY_FAN_COUNT_VALUES

    # ---- A: quadratic, over the range the UI actually offers ------------------------------------
    ok(rays_per_bundle(9) == 81 and rays_per_bundle(31) == 961,
       "A1: rays per bundle is N squared, not N")
    lo, hi = rays_per_bundle(min(int(v) for v in RAY_FAN_COUNT_VALUES)), \
             rays_per_bundle(max(int(v) for v in RAY_FAN_COUNT_VALUES))
    ok((lo, hi) == (25, 1681),
       f"A2: the combo's own 5..41 spans 25..1681 rays/bundle (got {lo}..{hi})")
    ok(hi // lo == 67,
       f"A3: that is a 67x range behind one number (got {hi // lo}x)")

    # ---- B: the estimate ------------------------------------------------------------------------
    ok(abs(estimate_trace_seconds(18) / estimate_trace_seconds(9) - 4.0) < 1e-6,
       "B1: doubling the ray count quadruples the estimate")
    ok(NS_MS_PER_RAY > SEQ_MS_PER_RAY * 10,
       f"B2: the mesh backend is an order slower than sequential "
       f"({NS_MS_PER_RAY} vs {SEQ_MS_PER_RAY} ms/ray)")
    ok(estimate_trace_seconds(9, nonsequential=False) < estimate_trace_seconds(9),
       "B3: a sequential scene is estimated cheaper than a mesh-trace one")
    faster = compare_ray_counts(31, 9)
    ok("11.9x faster" in faster,
       f"B4: 31 -> 9 is the ~12x the session measured (got {faster!r})")

    # ---- C: the hint -----------------------------------------------------------------------------
    h9, h31, h41 = (format_ray_count_hint(n) for n in (9, 31, 41))
    ok("81 rays/bundle" in h9 and "9x9" in h9,
       f"C1: the hint states the grid AND the ray count (got {h9!r})")
    ok("s/trace" in h9 and "s/trace" in h31,
       "C2: and an estimated time, which is the part the number hides")
    ok("min/trace" in h41,
       f"C3: it escalates to minutes where minutes are real (got {h41!r})")
    ok("mesh trace" in h9 and "sequential" in format_ray_count_hint(9, nonsequential=False),
       "C4: and names which backend the estimate assumes")
    # Two DIFFERENT degradations, and the distinction is deliberate: a non-numeric value
    # cannot be answered at all, while 0 is answered the way production answers it --
    # _full_pupil_grid_xy does n = max(1, ray_count), so a 0 really does build a 1-ray grid.
    # Modelling that as "no answer" would make the estimate disagree with the code it models.
    ok(format_ray_count_hint("nonsense") == "",
       "C5: a non-numeric ray count produces no hint rather than a bogus one")
    ok("1 rays/bundle" in format_ray_count_hint(0),
       f"C6: but 0 reports the 1-ray grid production would build, not an error "
       f"(got {format_ray_count_hint(0)!r})")

    # ---- D: the clamp never raises a user's choice ------------------------------------------------
    ok(solve_preview_ray_count(31) == SOLVE_PREVIEW_RAY_COUNT,
       "D1: an expensive choice is clamped for the intermediate traces")
    ok(solve_preview_ray_count(5) == 5,
       "D2: a user who already chose 5 keeps 5 -- the clamp only ever LOWERS")
    ok(solve_preview_ray_count(SOLVE_PREVIEW_RAY_COUNT) == SOLVE_PREVIEW_RAY_COUNT,
       "D3: a choice exactly at the cap is unchanged")
    ok(0 < SOLVE_PREVIEW_RAY_COUNT < 31,
       f"D4: the cap is a real reduction (got {SOLVE_PREVIEW_RAY_COUNT})")

    # ---- E: wired into the resolver ---------------------------------------------------------------
    from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin

    src = _inspect.getsource(TracePreviewSamplingMixin._current_ray_count)
    ok("_solve_preview_ray_count_override" in src,
       "E1: _current_ray_count honours the solve/swap clamp")
    for name in ("_drag_preview_ray_count_override", "_promote_preview_ray_count_override",
                 "_folded_preview_ray_count_override"):
        ok(name in src, f"E1: and still honours the pre-existing {name}")
    ok("__dict__.get" in src,
       "E2: it reads __dict__, not getattr -- the editor is a tk.Tk subclass whose "
       "__getattr__ recurses on a missing name")

    # ---- F: set AND cleared, at both sites ---------------------------------------------------------
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    for meth, label in ((LayoutTableWorkbenchMixin.solve_fov_to_inspection_face, "the FOV solve"),
                        (LayoutTableWorkbenchMixin.swap_imaging_lens_from_folder, "the lens swap")):
        body = _inspect.getsource(meth)
        ok("_solve_preview_ray_count_override" in body,
           f"F: {label} sets the clamp")
        ok("finally:" in body and "pop(\"_solve_preview_ray_count_override\"" in body,
           f"F: {label} clears it in a finally -- a LEAKED clamp would silently degrade "
           f"every later trace, which is worse than the slowness it fixes")

    # ---- G: degradation ----------------------------------------------------------------------------
    ok(rays_per_bundle("nonsense") == 0 and rays_per_bundle(None) == 0,
       "G1: a malformed ray count yields 0 rather than raising")
    ok(solve_preview_ray_count("nonsense") == SOLVE_PREVIEW_RAY_COUNT,
       "G2: and the clamp falls back to the cap rather than to the user's bad value")
    ok(compare_ray_counts("nonsense", 9) == "",
       "G3: an uncomparable pair returns nothing rather than a divide-by-zero")
    ok("faster" in compare_ray_counts(31, 9) and "slower" in compare_ray_counts(9, 31),
       "G4: the comparison names the direction, both ways round")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0827 ray-count-is-quadratic validation PASSED")
        return 0
    print("0827 ray-count-is-quadratic validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
