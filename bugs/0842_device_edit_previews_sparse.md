# 0842 -- a device-size edit previews at a sparse fan

> *"the ray tracing takes quite long for each opration, I have to wait and stare at the scene
> for minutes each time."*

bugs/0827 clamped the SOLVE and the SWAP. **It clamped the wrong operations first.** The one
the user repeats while dialling a number in is the DEVICE SIZE, and `set_inspection_part_spec`
ended in an unclamped `_refresh_open_3d_views()`.

It was the only entry in the `_current_ray_count` override chain with no clamp at all:

    _drag_preview_ray_count_override       bugs/0024
    _promote_preview_ray_count_override    bugs/0105
    _folded_preview_ray_count_override     bugs/0410
    _solve_preview_ray_count_override      bugs/0827   (solve + swap)
    <device edit>                          nothing

Recorded cost of the full-density alternative, from `trace_cost`'s own measured header:
**28.0 s mean per trace, 43.3 s worst.** At ray_count 31 the pupil grid is 31 x 31 = 961 rays
per bundle; clamped it is 9 x 9 = 81, about **12x cheaper**.

## Clamped, not deferred

Deferring the way a load does (bugs/0646) builds the bodies with **no rays** and waits for
Trace Now. That is right for a load, where the geometry may be crashed and the trace can wedge.
It is wrong here: resizing the part changes what is imaged, so the rays legitimately change and
the user needs to SEE them -- this user has filed repeatedly about seeing the true light
(bugs/0379, the detector-miss work, the stray-light census). Blanking the beam on every size
change would trade one annoyance for a worse one.

The clamp keeps the beam drawn and costs a twelfth.

## It says so

    Device resized -- ... Preview traced at 9x9 rays instead of 31x31 -- Trace Now for full density.

A quietly coarser beam looks like a worse trace rather than a faster preview. That is the
bugs/0828 / bugs/0834 complaint in picture form: an output without its parent.

## An honest note on the measurement

I could not re-measure this live. Three headless probes returned **0.00 s and no ray-count
reads**, because `_refresh_open_3d_views` begins `if self._three_d_inspector is not None:` and
a headless editor has no inspector -- an empty measurement, which I briefly mistook for a
finding about the deferred-trace state before checking. The timing log on disk was then
contaminated by those same probes (404 system rebuilds, 290 s, of which 363 and 286 s were
mine).

So this rests on what IS verifiable: the code path has no clamp, which is read directly, and
the 28.0 s / 43.3 s per-trace figures recorded in `trace_cost` from a real 25.7-minute session.
No new measurement is claimed.

## Guard

`KrakenOS/UI/validate_open3d_0842_device_edit_previews_sparse.py`, penta phase 621. The check
that matters is NO-LEAK: 31 -> 9 while the override is set -> 31 once cleared. A clamp that
leaked would silently halve the density of every later trace, which is a far worse bug than the
one being fixed. It also pins that the edit does NOT set the fast-load gate, so a later
"simplification" to deferral cannot remove the rays without failing.
