# 0824 -- which rays get drawn depends on the ray, not on its position

Not a flag. optiland's NSQ path recorder ships a `record_paths` contract that selects
its subset by a PCG32 hash of `ray_id`, explicitly so membership is *"independent of
batch_size ... and stable for a given seed regardless of how many rays end up
actually being born"*. Reading that surfaced the same defect here.

## The bug

`source_illumination_rays_overlay._subsample` capped the drawn rays with:

    idx = rng.choice(len(polylines), int(cap), replace=False)

The module comment says *"Subsampling is deterministic (seeded)"*. For one fixed list
that is true. Across runs it is false, because the draw is over **list positions**.
Anything that changes the list re-rolls every ray on screen:

* a different ray budget;
* a role tag that now matches, or stops matching (the fallback at
  flags 20260708_1516..1519 switches the whole input list);
* one more ray clipping short, moving every later ray's index;
* any upstream code consuming random numbers before the overlay runs.

This is the one path a user reaches for when they need to know where stray light came
from, and two runs of it could not be compared ray-for-ray.

## Fix

`KrakenOS/UI/services/stable_ray_subset.py`. Selection is a pure function of
(ray identity, seed) via a splitmix64 finalizer -- no RNG, no position. Two policies,
because they trade different things:

* `select_smallest_k` -- exactly `cap` items, the lowest hashes. What the overlay uses.
* `select_by_probability` -- a fixed threshold, so membership is **fully
  population-independent**: a ray is in or out no matter what else was traced.

`ray_identity` prefers the engine's `source_ray_index`, falls back to `ray_index`,
then to the launch point. It never falls back to list position -- that is the bug.

## What this buys, precisely

Worth stating exactly, because overclaiming here would be its own defect:

* **order-independent** -- shuffle the input, get the same set. This is the real fix.
* **free of upstream RNG coupling** -- nothing that draws random numbers first can
  shift the overlay.
* **reproducible at a fixed population.**
* **NOT population-independent** under `select_smallest_k`: growing the population
  tightens which hashes win. For comparing two runs at different ray budgets,
  `select_by_probability` is the policy, and it is population-independent in both
  directions.

The first draft of the code comment claimed raising the ray budget would not reshuffle
the overlay. That is not true of smallest-k and was corrected before landing.

## Collateral found while wiring it

`_split` discarded the record and returned bare polylines, so identity could not reach
the cap. It now returns `(record, polyline)` pairs. The aperture statistics further
down (`_terminals`, `_plane_crossings`) must keep reading the **full** populations,
not the drawn sample -- the clear aperture is a property of every ray that passed, not
of the 240 on screen. Both dead `np.random.default_rng` calls are gone: leaving a live
RNG there would invite a future caller to draw from it and silently reintroduce the
coupling.

## Guard

`KrakenOS/UI/validate_open3d_0824_stable_ray_subset.py`, penta phase 603. Display-free:
hash avalanche and uniformity, reproducibility, order-independence **with the positional
draw's contrasting behaviour asserted** so the motivation cannot rot, RNG decoupling,
population-independence of the probability policy in both directions, identity
precedence, the overlay's wiring and its RNG-free source, and degradation.

Regression: `validate_open3d_source_illumination_rays`,
`validate_open3d_illumination_marker_emission`,
`validate_open3d_0542_illumination_rays_master_toggle` all pass.
