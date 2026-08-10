# 0601 — stray tails drawn as sensor arrivals (the hard-stop board) (FIXED)

Flag `flag_20260810_145934`: *"changed to 55x55 FOV, why there are some pencils of rays
reaching the detector? Those not located at the 9 focused points."*

## Measured mechanism

After the 55×55 solve on the frozen Apo75, the termination census is stark: **all 573 rays
end `no_next_intersection`** — the engine never books a sensor hit on this scene family
(the world-placed Image row is never a sequential surface hit), so EVERY drawn sensor
arrival is manufactured by the display's detector hard-stop
(`_clip_polyline_at_detector_planes`). Its radial limit was, by its own docstring, "a
generous radial board, NOT a tight active-area rect" — so any stray envelope tail crossing
the board was truncated AT the plane, drawn as an arrival for light that physically passes
BESIDE the sensor. The 9 focused pencils are honest (their crossings are genuine
convergences inside the sensor); the extra pencils were the board's fakes.

(Getting this census took three probe pipelines: the raw records and the plain
`_build_scene_bundle` never see the termination rewrite; the canonical entry is
`_build_preview_system_rays_bundle` — the 0530 guard's own harness.)

## Fix

`detector_planes_for_hard_stop` now registers TWO limits per plane: the ACTIVE-sensor
half-diagonal ×1.15 (falling back to the board when no active dims exist) and the old
generous board. Ordinary rays clip at the ACTIVE limit — a crossing inside the sensor is
real (ghost) light and keeps its arrival look; outside it the ray flies on, visibly missing
the glass. DRAW-SUPPRESSED branches and DIFFUSE double-pass scenes keep the board: their
planes exist precisely to bound the scatter starburst (bugs/0182/0184/0506 — phases 178/180
measured the regression when the rect let scatter fly past, and pass again with the
scene_has_diffuse_scatter gate).

Verified: 0530 (its own "non-target tails must not END near the sensor" check),
0531, 0457, 0555 standalones and marathon phases 178/180 all pass.

## Deeper issue, recorded

That NOTHING is ever `target_termination` on a frozen folded scene means the ray
status/colour machinery reads every ray as non-reaching — the census cannot distinguish a
converging beam from a stray at the bookkeeping level; only the display geometry does. The
detector-surface-hit bookkeeping for world-placed Image rows is a standing debt (the same
family as the 0593 instrument's motivation).

## Addendum (bugs/0605)

The 1.15x half-DIAGONAL disc was still too generous: on the live Apo75 bundle the 9
missed_image rays (one per field) cross the plane outside the 23x23 glass rectangle
but inside the disc, and were drawn as fake arrivals — the user's second flag on these
pencils (flag_20260810_164247). The active stop is now the true RECTANGLE
(tangent/bitangent + half extents on the plane tuples); the disc remains only as the
no-dims fallback, and the radial board still governs draw-suppressed branches. See
bugs/0605.
