# 0457 — after add-BS + snap: the drawn Image is DOUBLE-FOLDED, and the trace stops half way

Recording `recording_20260728_075613.json` (3 flags) + `flag_20260728_080101_869` ("STEP hidden",
the clear view), all on build **`f1df9b58`** — i.e. WITH 0451 + 0456. Flags 1–2 are the user's
reference shots ("Original.", "1st RA mirror deleted."); flag 3 is the report:

> "After adding BS, rubberband select + snap to optical axis, sensor/image place relocate to wrong
> position, causing ray tracing stop half way. Layout save to `machine_vision_AZ85_RA_Mirror_BS.py`"

These are TWO independent defects. Neither is a 0451/0456 regression — those two fixes hold.

## Defect A — the drawn Image row is folded TWICE (the "wrong position")

The live scene and the saved prescription disagree about where the sensor is:

| | Image row (world z) | camera body (world z) |
|---|---|---|
| live app (both flags) | **−48.8** | +2.7 |
| the SAVED scene reloaded | **+2.73** | +2.73 |

Row 7 (the image-side promoted RA mirror) sits at z = 54.23 with thickness 51.5:

* correct single fold: 54.23 − 51.5 = **2.73** ← what the saved prescription and the camera say
* what the live view drew: 54.23 − 2×51.5 = **−48.77** ← the fold displacement applied a SECOND time

So the prescription is right and the DRAWING is wrong: on a frozen/snapped scene the row already
carries its absolute, already-folded world position, and the display fold then translates it by the
mirror thickness again. The camera body is drawn at the correct single-fold position, which is why
the sensor appears to "relocate" away from its camera. Same divergence FAMILY as 0456 but a
different mechanism and a different code path: 0456 was row-vs-body inside the solve; this is
prescription-vs-display inside the fold overlay. Compare 0448 (drawn-vs-traced tilt convention).

**Why the 0447/0456 probes never caught it:** they measure `station + desp` — the PRESCRIPTION. The
double fold happens in the DISPLAY layer, so a probe must assert on the DRAWN actor (what the
recorder captures in `row_actor_bounds`), not on the row arithmetic. Any guard for this must read
the drawn geometry.

## Defect B — the trace is already dead before the snap (the "stop half way")

Replaying the sequence headlessly (`/tmp/.../repro_snap.py`, ~2 min) on the pristine AZ85:

| step | ray terminal statuses | detectors |
|---|---|---|
| 1. original | **585 hit_detector** | Image at (235.9, 0, 1.5) |
| 2. 1st RA mirror deleted | **3249 stopped** (all vignetted) | + a suppressed dead-end arm (0451 working) |
| 3. BS added | **279 escaped, 0 hit** | both at the LED — (−0.12, −47.7, 38.7), (−0.12, 1.2, 88.1) |
| 4. rubber-band + snap | **279 escaped, 0 hit** | unchanged |

The beam stops imaging at **step 2** — deleting the object-side fold, long before the BS or the
snap. Nothing downstream can recover it: by step 3 every ray escapes and no detector sits at the far
end, which is exactly the flag's "ray tracing stop half way" (the STEP-hidden shot shows the bundle
dying just past the lens, with three stray "Sensor 23.0×23.0 / Image circle" labels — the three
branch arms — scattered at the BS, mid-lens and the mirror).

This is the known **non-sequential first-order seam** (`project_nonseq_first_order_seam`): the
sequential PupilCalc throws on a BS, the silent fallback aims the source down the OLD folded path,
and the launched fan misses the re-seated chain. It is now the dominant symptom, not a side effect.

**Note the asymmetry that proves it is a launch/aim problem, not a geometry problem:** loading the
user's SAVED `machine_vision_AZ85_RA_Mirror_BS.py` traces **healthy — 145 hit_detector, 7 escaped**,
with the Image at 2.73 coincident with the camera. The same geometry built INTERACTIVELY does not.
The save normalizes what the interactive path leaves inconsistent.

## What to do

Defect B is the real build — a universal first-order reference so the source aims at the actual
first surface of the actual chain (design note in `project_nonseq_first_order_seam`). It subsumes
the sparse-ray complaints from 0433/0448 as well.

Defect A is separately fixable: gate the display fold for rows whose placement is already absolute
(`stay_put_freeze` / `last_axis_to_axis_move` / snapped), the same predicate the 0447 appliers use.
Its guard MUST assert on drawn actor bounds.

## Defect A SOLVED (diagnosis) — it is a STALE ACTOR, not a double fold

`flag_20260728_084648` ("direct loaded the file.", build `070a867d`) settles it. The user loaded
`attachment/machine_vision_AZ85_RA_Mirror_BS.py` — nothing else, no freeze/BS/snap — and the live
view still drew row 8 at z = **−48.8**. Loading that same file headlessly gives:

* prescription Image row 8 = **+2.73**
* drawn `surface_curves`: rows 1,2,3,4,5,6,7,0 … and **no curve for row 8 at all**. The only
  `kind='image'` curves carry `row_index = -1` — the three branch detectors at (230.65, 2.3, 4.01),
  (74.15, 2.4, 34.26), (−2.77, 2.37, 68.39).

So the scene bundle does not draw the sequential Image at all here (branch detectors supersede it,
per the scene_builder rule), yet the LIVE viewer still has a row-8 actor — parked at the value the
PREVIOUS scene had. Nothing in the rebuild removes a row actor whose row no longer contributes a
curve, so it survives the load and floats at its old position.

That also explains the live-vs-saved asymmetry that made no sense for two rounds: the saved file was
never wrong, and the prescription was never wrong. **The arithmetic 54.23 − 2×51.5 = −48.77 was a
coincidence of the previous state, not a double fold.** Chasing that number cost attempts 1 and 2.

**Fix shape:** on scene rebuild, drop (or hide) row actors for rows the new bundle produces no
geometry for — the supersede path is exactly the case that leaves one behind. Same family as the
"2-D is stale" gate: the invariant is that no actor outlives the geometry that justified it.
Verification needs a LIVE viewer (headless never creates the actor, so a headless probe cannot see
this bug) — assert on the recorder's `row_actor_bounds` after loading a scene whose Image is
superseded, which is precisely what the flag captured.

## Attempt 1 at B — REVERTED (negative result, kept because it narrows the next attempt)

Hypothesis: in finite-conjugate mode the chief ray is by definition the ray from the object point
through the centre of the stop, so re-aiming each launch bundle at the stop's world point should
repair a folded/frozen chain and be a no-op on a healthy one. Implemented as a rigid Rodrigues
rotation of each bundle about its own launch point, applied at `_trace_preview_bundles` (the
documented choke point every sampling path funnels through), gated to Finite mode (Infinity's
bundle DIRECTION *is* the field angle — re-aiming it would silently zero the field).

It broke the healthy baseline and was reverted:

| step | before | with the re-aim |
|---|---|---|
| 1. original (healthy) | 585 hit_detector | **729 missed_detector** |
| 2. mirror deleted | 3249 stopped | 3249 missed_detector |

**Why it failed — the useful part:** `_analysis_surface_index()` → `_surface_reference_world_point()`
does NOT return the stop centre in world space. On this scene it returns the STRAIGHT-EQUIVALENT
(unfolded) Image point — visible in the replay as the Image row's prescription `[0, 0, 340.4]` while
the drawn/traced sensor is at `[235.9, 0, 1.5]`. So the fan was aimed at an unfolded phantom, which
is why even the healthy scene lost its focus. The rotation machinery itself was fine (it is exactly
the identity when the aim already matches); the REFERENCE was wrong.

**Next attempt should start from `_trace_per_branch_bundles`** (`trace_preview.py`, guarded by
"DESIGN §5b per-branch launch"). That path already exists to give a beam splitter one launch bundle
per imaging arm, "each aimed at that arm's own pupil", and its comment concedes the current
whole-layout reference "can't even build the whole-layout reference past the folded arm" — i.e. the
per-arm pupil in WORLD space is the reference this fix needs, and it is already computed there.
Reuse that, do not re-derive an aim point from the prescription.

Baseline after revert, re-measured and identical to before the attempt: 585 / 3249 / 279 / 279.

## Attempt 2 at B — also REVERTED, and it falsifies the "launch aiming" thesis

Followed the lead above. The off-axis FINITE launch in `_trace_preview_rays` does fire from
`[field_x, field_y, 0]` at a pupil disk on `z = object_distance` — both on the nominal axis — so a
launch frame was added that fires down the object -> entrance-surface direction instead, returning
`None` (arithmetic untouched) whenever the chain is still nominal.

**Result: no change at all.** 585 / 3249 / 279 / 279, identical. Reverted.

Measured why, and this is the part that matters:

* `_build_scene_source_bundles` returns **0** bundles for this scene — the LED is not driving the
  launch, so no source-aiming fix applies either.
* `off_axis = True`, `object mode = Finite` — it does reach that branch.
* But the folded path traces **straight-equivalent rows** (`_folded_sequential_trace_rows`), and on
  those rows the chain IS nominal, so the new frame correctly declined to act.

So the launch is NOT mis-aimed, and B is not a first-order/pupil seam. What actually happens: after
the freeze the chain's rows carry ABSOLUTE world placements (x ≈ 77…235 at z = 53) while the object
row sits at the origin, and those same rows are then handed to a SEQUENTIAL trace that assumes rows
are stations along one axis. The rays vignette because the traced prescription is geometrically
incoherent, not because the fan points the wrong way — the same family as bugs/0448 ("baked rows
traced BACKWARDS") and the `trace_mode_north_star` rule that a frozen/split scene must be traced
NON-SEQUENTIALLY as real world geometry.

**Corrected next step:** stop treating this as an aiming problem. The question to answer first is
whether a frozen/snapped chain should be traced non-sequentially, and if so what supplies its
per-arm stops. That is an architecture decision, not a patch, and it should be taken deliberately
rather than attempted a third time from inference.

Also note the live-vs-saved asymmetry still stands and is unexplained: the user's SAVED file traces
healthy (145 hit) while the interactive scene does not. Whatever holds that difference is live state
the save normalises — the same suspicion as defect A. A live flag taken WITHOUT closing the app is
the cheapest way to see it.


## Attempt at fixing A — REVERTED (unsafe), read this before trying again

Wiring: `load_layout_by_name` ends at `refresh_plot(...)` and never asks a live viewer to
rebuild, so the stale actor is exactly the gap. Added
`_rebuild_live_open3d_after_layout_load()` calling
`inspector.refresh_from_editor(force_retrace=True, geometry_changed=True)` after a load,
guarded by `winfo_exists()`.

**Its validator SEGFAULTED (dumped core)** driving the flag's own gesture — open the
inspector, then load the machine-vision scene again. That is the known 0294-class
use-after-free (`reference_vtk_render_backend_segfault`: "machine-vision load with live
inspector destroys the viewer; fix = keep-viewers flag around the load"), and note that
`load_layout_by_name` calls `_reset_complete_layout_runtime_state(close_viewers=True)`
BEFORE the point where the new hook fires. `winfo_exists()` is not sufficient: the Tk
widget can outlive the VTK render window.

Reverted — a fix that can segfault the app is worse than the stale actor, and a
segfaulted run also blocks the penta gate.

**Next attempt must first establish which is true:**
1. does that gesture segfault on `main` WITHOUT the hook (i.e. pre-existing, and the
   keep-viewers flag is not covering the load path here), or
2. does the hook itself resurrect a torn-down viewer?

Answer that with a bare probe (open inspector -> load -> capture snapshot, no code change)
before writing any fix. If (1), the stale actor is a symptom of the viewer teardown and the
real fix is in the keep-viewers path, NOT in a post-load refresh call.
