# 0827 -- the preview ray count costs N squared, and nothing said so

User: *"the ray tracing takes quite long for each opration, I have to wait and stare at
the scene for minutes each time."*

## Measured, from the user's own session

`~/.cache/krakenos/logs/open3d_timing_latest.jsonl`, 5848 events over 25.7 minutes on
`om05a_folded.py`:

    preview_system_rays_bundle    16 traces   448 s   mean 28.0 s   max 43.3 s
    swap_imaging_lens_from_folder  1 call     150 s
    trace_preview_bundle         194 bundles  305 s
       78 bundles x 361 rays = 28158 rays  ->  279 s   (91% of all bundle time)
       12 x 62 rays, 104 x 5 rays          ->  the rest, negligible
    all 9 refresh_scene together            31 s      <- RENDERING IS NOT THE COST
    render_done                  2075 draws  mean 20.6 ms

**The earlier fixes are working.** `NsTraceLoop` now runs at **9.9 ms/ray** against the
80 ms/ray of the bugs/0166 era -- the cell-normal cache (`f77a0aa`) and the lossless
decimated trace proxy (`9dc6a2e`) are earning their ~9x. This is not a regression. What
remained was volume.

## The dial is quadratic and the UI never said so

`_full_pupil_grid_xy` builds an **N x N** grid where N is the user's `ray_count`, once per
branch bundle. `RAY_FAN_COUNT_VALUES` offers `5..41`:

    ray_count  5 ->   25 rays/bundle    ~1 s/trace
    ray_count  9 ->   81               ~4 s
    ray_count 21 ->  441              ~21 s
    ray_count 31 ->  961              ~47 s     <- both the user's scenes carry 31
    ray_count 41 -> 1681             ~1.4 min

A **67x range** behind one number that reads as if it were linear. Both
`om05a_folded.py` and `machine_vision_ELS85.py` carry `ray_count: 31`.

## Two fixes

**1. The cost is stated before it is paid.** The Ray count LABEL is now live and reads
e.g. `Ray count -- 31x31 = 961 rays/bundle, ~47 s/trace (mesh trace)`.
`services/trace_cost.py` is the pure arithmetic, with the measured constants
(9.9 ms/ray mesh, 0.55 sequential, 4.9 bundles/trace) named and sourced. The estimate is
worded as an estimate: it exists to make 6 s vs 80 s visible, not to predict a scene.

**2. A solve or swap iterates at a sparse fan.** New
`_solve_preview_ray_count_override`, the same transient-clamp shape as the drag (0024),
promote (0105) and folded (0410) overrides that already existed -- none of which covered
the solve or the swap, which is exactly where the 28 s and the 150 s went. Set around
`qe.fov_solve` and around `_swap_auto_refocus_to_best_focus`, cleared in a `finally`.

`solve_preview_ray_count` **never raises** a user's choice: someone who picked 5 keeps 5.
It only lowers an expensive one for the intermediate traces nobody looks at.

The `finally` matters more than the clamp: a LEAKED clamp would silently degrade every
later trace, which is a worse defect than the slowness it fixes. The guard asserts both
sites clear it.

## Not done

The bin rule for `ray_count` is unchanged and no default was lowered -- the user's setting
is theirs. The 361-vs-961 gap (the session traced 361 while the scenes declare 31 -> 961)
means something already caps it on this path; that cap is not characterised here.

Also seen and left: two full traces 0 s apart at t=77 s in the same session, the
bugs/0166/0700 double-trace class. Real but small beside the above.

## Guard

`KrakenOS/UI/validate_open3d_0827_ray_count_is_quadratic.py`, penta phase 606. Pure:
the quadratic over the combo's own range, the estimate's scaling, the hint's content and
its escalation to minutes, the clamp never raising a choice, the override chain including
the three pre-existing clamps, both sites setting AND clearing, and degradation -- where a
non-numeric value yields no answer while 0 reports the 1-ray grid production really builds
(`max(1, n)`), because a model that disagreed with the code it models is worse than none.
