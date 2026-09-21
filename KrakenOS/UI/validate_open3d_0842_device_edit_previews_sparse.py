"""bugs/0842 guard -- a device-size edit previews at a sparse fan, and the clamp does not leak.

The user: *"the ray tracing takes quite long for each opration, I have to wait and stare at the
scene for minutes each time."*  bugs/0827 clamped the SOLVE and the SWAP.  It clamped the wrong
operations first: the one the user repeats while dialling a number in is the DEVICE SIZE, and
`set_inspection_part_spec` ended in an unclamped `_refresh_open_3d_views()`.

It was the only entry in the `_current_ray_count` override chain with no clamp at all --
drag (0024), promote (0105), folded (0410) and solve/swap (0827) all have one.

Recorded cost of the full-density alternative, from `trace_cost`'s own measured header:
**28.0 s mean per trace, 43.3 s worst.**  At ray_count 31 the pupil grid is 31 x 31 = 961 rays
per bundle; the clamp makes it 9 x 9 = 81, about 12x cheaper.

CLAMPED, not deferred.  Deferring the way a load does (bugs/0646) builds bodies with NO rays,
which would blank the beam on every size change -- and resizing the part changes what is
imaged, so the rays legitimately change and the user needs to see them.

Checks:
  SOURCE  -- the edit sets the clamp, and clears it in a finally.
  CHAIN   -- _current_ray_count reads the device-edit override.
  CLAMPS  -- 31 -> 9 (961 rays -> 81), and the saving is what trace_cost predicts.
  NEVER-RAISES -- a user who chose 5 keeps 5.
  NO-LEAK -- with the override absent the full count is back; the clamp is transient.
  SAYS-SO -- the status line names both counts, so a coarser beam is not mistaken for a
             worse trace (the bugs/0828 / bugs/0834 complaint).
  NOT-DEFERRED -- the edit does not set the fast-load gate, which would remove the rays.
"""
from __future__ import annotations

import inspect as _inspect


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as _M
    from KrakenOS.UI.services import trace_preview_sampling as tps
    from KrakenOS.UI.services.trace_cost import (
        DEVICE_EDIT_PREVIEW_RAY_COUNT,
        estimate_trace_seconds,
        rays_per_bundle,
        solve_preview_ray_count,
    )

    src = _inspect.getsource(_M.set_inspection_part_spec)
    if "_device_edit_preview_ray_count_override" in src and "finally:" in src:
        notes.append("SOURCE = the edit sets the clamp and clears it in a finally")
    else:
        notes.append("SOURCE the device edit does not clamp, or does not clear in a finally")
        ok = False
    if "_preview_trace_deferred_until_requested" in src:
        notes.append("NOT-DEFERRED the edit sets the fast-load gate, which removes the rays")
        ok = False
    else:
        notes.append("NOT-DEFERRED = the edit clamps rather than blanking the beam")

    chain = _inspect.getsource(tps)
    if '"_device_edit_preview_ray_count_override"' in chain:
        notes.append("CHAIN = _current_ray_count reads the device-edit override")
    else:
        notes.append("CHAIN the override is never read, so the clamp does nothing")
        ok = False

    full, cap = 31, int(DEVICE_EDIT_PREVIEW_RAY_COUNT)
    got = solve_preview_ray_count(full, cap=cap)
    if got == cap and rays_per_bundle(got) == cap * cap:
        saved = estimate_trace_seconds(full) - estimate_trace_seconds(got)
        notes.append(
            f"CLAMPS = {full} -> {got} ({rays_per_bundle(full)} rays -> {rays_per_bundle(got)}, "
            f"{rays_per_bundle(full) / rays_per_bundle(got):.0f}x), about {saved:.0f} s saved "
            f"per edit at trace_cost's measured rate"
        )
    else:
        notes.append(f"CLAMPS {full} clamped to {got}, expected {cap}")
        ok = False

    if solve_preview_ray_count(5, cap=cap) == 5:
        notes.append("NEVER-RAISES = a user who chose 5 keeps 5")
    else:
        notes.append("NEVER-RAISES the clamp RAISED a cheaper user choice")
        ok = False

    # The property that actually matters: the clamp is transient.
    class _Stub:
        def __init__(self, n):
            self.__dict__["ray_count_var"] = type("V", (), {"get": staticmethod(lambda: n)})()
        _current_ray_count = tps.TracePreviewSamplingMixin._current_ray_count

    stub = _Stub(31)
    before = stub._current_ray_count()
    stub._device_edit_preview_ray_count_override = 9
    during = stub._current_ray_count()
    del stub._device_edit_preview_ray_count_override
    after = stub._current_ray_count()
    if (before, during, after) == (31, 9, 31):
        notes.append("NO-LEAK = 31 -> 9 while set -> 31 once cleared; the clamp is transient")
    else:
        notes.append(f"NO-LEAK the override leaks: before {before}, during {during}, after {after}")
        ok = False

    if "Trace Now for full density" in src and "instead of" in src:
        notes.append("SAYS-SO = the status line names both counts")
    else:
        notes.append("SAYS-SO the coarser preview is not explained to the user")
        ok = False

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
