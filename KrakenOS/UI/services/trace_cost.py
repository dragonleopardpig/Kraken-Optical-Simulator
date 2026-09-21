"""bugs/0827: a preview ray count costs N SQUARED, and nothing said so.

Measured on a real 25.7-minute om05a session (``open3d_timing_latest.jsonl``, 5848 events):

    preview_system_rays_bundle   16 traces   448 s total   mean 28.0 s   max 43.3 s
    swap_imaging_lens_from_folder 1 call     150 s
    trace_preview_bundle         194 bundles 305 s
      of which  78 bundles x 361 rays = 28158 rays  ->  279 s  (91% of all bundle time)
                12 bundles x  62 rays,  104 bundles x 5 rays -> the rest, negligible
    all 9 refresh_scene together  31 s        <- rendering is NOT the cost
    NsTraceLoop median            9.9 ms/ray  <- already 8x better than the 80 ms/ray
                                                 bugs/0166-era figure; the cell-normal
                                                 cache and decimated proxy are working

So the remaining cost is ray VOLUME, and the dial is quadratic:
``_full_pupil_grid_xy`` builds an N x N grid where N is the user's ``ray_count``.
``RAY_FAN_COUNT_VALUES`` offers 5..41, i.e. **25 to 1681 rays per bundle** -- a 67x range
behind a single innocuous-looking number.

This module is the pure arithmetic, so the number can be shown BEFORE it is paid for.
"""

from __future__ import annotations

#: Median ms/ray measured for ``NsTraceLoop`` on the om05a session above. The
#: non-sequential mesh backend, which any scene with a promoted STL optical solid plus
#: off-axis geometry falls into.
NS_MS_PER_RAY: float = 9.9

#: Sequential ``Scalar TraceLoop`` cost, ~18x cheaper (bugs/0166 profiling).
SEQ_MS_PER_RAY: float = 0.55

#: Bundles per trace on the measured session: 78 full-density bundles over 16 traces.
#: The per-branch unfold emits one bundle per branch, so a folded two-arm scene pays
#: this multiplier on top of N squared.
TYPICAL_BUNDLES_PER_TRACE: float = 4.9

#: Clamp applied while a SOLVE or SWAP iterates. 9 x 9 = 81 rays is 4.5x cheaper than
#: the 361 the session actually ran, and those operations trace repeatedly before the
#: user sees anything -- the sparse fan is for getting there, not for the final look.
#: Consistent with the three clamps that already exist for drag (0024), promote (0105)
#: and folded scenes (0410).
SOLVE_PREVIEW_RAY_COUNT: int = 9


def rays_per_bundle(ray_count) -> int:
    """``N x N``. The whole point of this module: it is not linear."""
    try:
        n = max(1, int(ray_count))
    except (TypeError, ValueError):
        return 0
    return n * n


def estimate_trace_seconds(ray_count, *, nonsequential: bool = True,
                           bundles: float = TYPICAL_BUNDLES_PER_TRACE) -> float:
    """Rough seconds for ONE trace at this ray count. Rough on purpose.

    The figure exists to make an order of magnitude visible before it is spent -- 6 s
    against 80 s -- not to predict a specific scene. A caller must not present it as a
    measurement; :func:`format_ray_count_hint` words it as an estimate.
    """
    per_ray = NS_MS_PER_RAY if nonsequential else SEQ_MS_PER_RAY
    return rays_per_bundle(ray_count) * max(float(bundles), 0.0) * per_ray / 1000.0


def format_ray_count_hint(ray_count, *, nonsequential: bool = True,
                          bundles: float = TYPICAL_BUNDLES_PER_TRACE) -> str:
    """One line for the Ray count control: what this choice actually costs."""
    rays = rays_per_bundle(ray_count)
    if rays <= 0:
        return ""
    seconds = estimate_trace_seconds(ray_count, nonsequential=nonsequential, bundles=bundles)
    if seconds >= 60.0:
        cost = f"~{seconds / 60.0:.1f} min/trace"
    elif seconds >= 1.0:
        cost = f"~{seconds:.0f} s/trace"
    else:
        cost = "<1 s/trace"
    backend = "mesh trace" if nonsequential else "sequential"
    return f"{int(ray_count)}x{int(ray_count)} = {rays} rays/bundle, {cost} ({backend})"


def compare_ray_counts(current, candidate, *, nonsequential: bool = True,
                       bundles: float = TYPICAL_BUNDLES_PER_TRACE) -> str:
    """How much a different ray count would cost, relative to the current one."""
    now = estimate_trace_seconds(current, nonsequential=nonsequential, bundles=bundles)
    then = estimate_trace_seconds(candidate, nonsequential=nonsequential, bundles=bundles)
    if now <= 0.0 or then <= 0.0:
        return ""
    if then < now:
        return f"{int(candidate)} would be {now / then:.1f}x faster ({then:.0f} s vs {now:.0f} s)"
    if then > now:
        return f"{int(candidate)} would be {then / now:.1f}x slower ({then:.0f} s vs {now:.0f} s)"
    return f"{int(candidate)} costs the same"


#: bugs/0842: the clamp a DEVICE-SIZE edit previews at. Resizing the inspected part changes
#: what is imaged, so the rays legitimately change and must stay VISIBLE -- deferring them the
#: way a load does would blank the beam on every size change, and this user has filed repeatedly
#: about seeing the true light. 9 x 9 = 81 rays against 961 at their ray_count of 31 is ~12x
#: cheaper with the beam still drawn. The recorded cost of the full-density alternative, from
#: the session in this module's own header: 28.0 s mean per trace, 43.3 s worst.
DEVICE_EDIT_PREVIEW_RAY_COUNT: int = SOLVE_PREVIEW_RAY_COUNT


def solve_preview_ray_count(user_ray_count, *, cap: int = SOLVE_PREVIEW_RAY_COUNT) -> int:
    """The ray count a SOLVE or SWAP should iterate at.

    Never RAISES the user's choice -- a user who picked 5 keeps 5. It only lowers an
    expensive one for the intermediate traces nobody looks at, exactly as the drag and
    promote clamps already do.
    """
    try:
        n = max(1, int(user_ray_count))
    except (TypeError, ValueError):
        return max(1, int(cap))
    return min(n, max(1, int(cap)))
