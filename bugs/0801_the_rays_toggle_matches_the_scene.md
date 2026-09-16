# 0801 -- the Show Rays toggle states what is on screen, and ticking it traces

The user, after `bugs/0800`:

> *"if ray is not on, why not just untick the rays on? Main thing here is matching UI toggle
> with actual scene. If user toggle rays on or off, it should immediately show the ray, right
> now on fresh load, without clicking Trace Now, the rays on/off toggle is not functioning."*

Right on both counts, and a better framing than the one 0800 shipped. 0800 made the view SAY
that rays were pending, which is an explanation for a control that still did nothing. A toggle
that does not toggle is broken, not merely quiet.

## Measured, before

| | fresh load | tick Show Rays ON |
|---|---|---|
| `_preview_trace_deferred_until_requested` | True | True |
| `show_rays_var` | **True** | True |
| ray paths on screen | **0** | **0** |

`_on_show_rays_changed` ends in `refresh_from_editor()`, and every refresh entry honours the
fast-load gate (bugs/0646, made authoritative by bugs/0718), so ticking the box rebuilt the
scene bodies-only and drew nothing.

## Fix

**Ticking the box IS the deliberate trace request.** bugs/0646 asks that "every REAL trace entry
clears the gate first" and bugs/0718 keeps the gate authoritative because the non-sequential
trace runs in-process and can wedge the UI on crashed geometry -- but a user ticking *Show Rays*
is asking for rays in so many words, exactly as Trace Now does. An INCIDENTAL refresh still
cannot clear it, which is all 0718 ever required.

So `_on_show_rays_changed` clears the gate when the box is turned ON (never when turned off) and
before refreshing, and `_pending_rays_note` now **unticks** the box on a deferred open instead of
leaving it lying:

    Show Rays is off because the fast load deferred the trace: tick it (or press Trace Now)
    to trace. The STEP/DXF export follows the view.

## Verified

| | fresh load | tick ON | tick OFF |
|---|---|---|---|
| `show_rays_var` | **False** | True | False |
| ray paths on screen | **0** | **3249** | hidden |
| gate | True | cleared | stays cleared |

The box matches the scene at every point, and rays appear on the tick with no Trace Now.

## What is deliberately preserved

bugs/0718's protection is the reason this was not fixed by tracing on open. The guard pins that
neither `open_3d_view` nor the refresh service clears the gate -- only the two deliberate user
requests do -- so a future "just trace it on open" cannot quietly reintroduce the hang.

## Guard

`python -m KrakenOS.UI.validate_open3d_0801_the_rays_toggle_matches_the_scene` -- display-free,
source contracts plus a stub toggle. It pins that ticking clears the gate and only when turned
ON and before the refresh; that the refresh service and `open_3d_view` still never clear it;
that a deferred open unticks the box and explains how to get rays; that a traced scene leaves
the user's toggle exactly as it was; and that the export still follows the view. Penta phase 584.
