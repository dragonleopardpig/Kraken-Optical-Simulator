# 0644 — a STEP-overlay COMMIT must re-derive the optical axes (user report)

flag_20260824_164800 ("original") + flag_20260824_164820: *"the 2nd optical axis stays after
the BS+LED+illuminator shifted. The optical axis should be generated from the BS. Seems the
algorithm separate BS with optical axis generation."* Build 60e50580.

## Evidence (straight from the two flag state files)

|                          | original            | after the shift        |
|--------------------------|---------------------|------------------------|
| BS row actor bounds (z)  | 146.7 .. 202.6      | **247.7 .. 303.6** (+101 mm) |
| LED STEP body bounds (z) | 131.9 .. 208.3      | **232.9 .. 309.3** (+101 mm) |
| optical_axis_records     | 2 records           | **byte-identical**     |

So the MODEL moved (+101 mm ALONG the imaging axis -- the on-beam case that bugs/0643 verified
does follow) and the drawn axes were simply never regenerated. The user's read was exactly
right: the BS moved, axis generation didn't run.

## Root cause

`translate_step_overlay` ended with `if refresh: self._refresh_open_3d_views(step_label=label)`.
But `refresh` is the caller's RETRACE appetite: the gizmo release
(`open3d_inspector._finish_step_translate_drag`) passes `refresh=physics_requested`, which is
**False** whenever Live Mode / physics is off. The optical axes are DISPLAY geometry derived
from the model, so with the rebuild skipped they kept their pre-drag pose while
`_translate_step_overlay_actors` had already carried the bodies live (which is why the CAD
visibly moved). Every earlier headless test missed it because those probes always called
`refresh_from_editor(...)` explicitly afterwards -- the live physics-off path never does.

## Fix

`if refresh or record_history:` -- a COMMIT (`record_history=True`) always re-derives the
display; the per-frame drag calls (`record_history=False`) still skip it, so dragging stays
smooth. The rebuild forces no retrace of its own (`_refresh_open_3d_views` passes
`force_retrace=False`), so a physics-off drag pays only for the actor/axis rebuild it needed.

## Verified (headless, one app per process, NO manual refresh after the move)

| experiment | BS row desp z | axis:global:split anchor |
|---|---|---|
| EXP-A post-fix commit (`record_history=True`) | -27.5 -> 73.5 (+101) | **173.346 -> 274.346 (+101)** |
| EXP-B per-frame path (`record_history=False`) | -27.5 -> 73.5 (+101) | unchanged (smooth drag preserved) |
| EXP-B2 pre-fix guard simulated on the SAME call | -27.5 -> 73.5 (+101) | stale -- reproduces the flag |

EXP-B2 (the commit call with `_refresh_open_3d_views` no-op'ed) proves the new branch is the
sole cause of the fix. `axis:global` correctly stays put in all three -- illuminator-only
semantics (bugs/0642) keep the Object row, and hence the root axis, anchored.

Guard: phase 482 (`validate_open3d_0644_commit_rebuilds_axes`) -- the commit gate includes
`record_history`; the 3 per-frame drag sites still pass `record_history=False`; the
gizmo-release commit passes `record_history=True`.
