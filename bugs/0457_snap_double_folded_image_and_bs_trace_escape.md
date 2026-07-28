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


## CORRECTION — the "stale actor" theory is REFUTED; it is a real double fold after all

`flag_20260728_092327` ("quit Kitty and restarted, direct open …") kills it. The app was
restarted at 09:21:12, after BOTH fixes landed (09:06:39 and 09:13:05), and row 8 still
drew at z = **−48.8**.

A freshly started app has **no previous scene to leave an actor behind**, and rows 1–7 all
showed the new file's positions, so the viewer had rebuilt correctly. The load hooks were
therefore redundant work, not a fix — both reverted (`git revert 38a6360d 080b70ba`).

So the LIVE build genuinely emits geometry for row 8 at −48.8, and the very first
arithmetic was right: 54.23 − 2×51.5 = −48.77, the fold displacement applied twice. I
abandoned that reading because a headless `_build_preview_system_rays_bundle` emits no
row-8 curve at all — but that is a DIFFERENT BUILD PATH, not evidence of staleness. Two
wrong turns came from trusting it.

**Why it still has no headless repro:** the editor-level bundle call and the inspector's
own `refresh_scene` are not the same build. `_open_inspector` + `capture_scene_snapshot`
reports `row_actors: 0` — that helper never populates the actor registry — so neither
route reproduces what the live viewer draws.

**The one thing to do next:** find how the live inspector actually builds its scene
(`refresh_scene` → its bundle call → `_apply_folded_display_bend` /
`_reconcile_folded_image_to_ray_convergence`) and drive THAT in a probe, checking whether
the Image lands at 2.73 or −48.77. Once it reproduces, the fix is the one named at the top
of this file: do not apply the display fold to a row whose placement is already absolute.
Do not attempt the fix before the probe reproduces — that mistake has now cost three
reverts on this bug alone.


## ROOT CAUSE FOUND — A and B are ONE bug: the TRACED image plane is off by the fold thickness

Measured on the user's saved `machine_vision_AZ85_RA_Mirror_BS.py`, one probe at a time.

**1. The beam traverses the chain correctly.** The axial ray:

    (0,0,0) -> (0,0,54.23) -> (70.46,.,54.23) -> (88.10) -> (97.96) -> (107.83)
           -> (125.46) -> (228.73,.,54.23) -> (228.73,.,-48.77)

It folds at the BS, passes every lens surface, reaches the image-side mirror -- then terminates
51.50 mm PAST the sensor. The BS fold itself is fine; the user's replacement of the RA mirror with
a BS plate works.

**2. Nothing reaches the sensor.** 0 of 837 ray paths end within 15 mm of the Image row's
prescribed position (228.73, 0, 2.73). `termination_reason` histogram:
`target_termination 145, no_next_intersection 286, missed_image 299, aperture_stop_vignette 107`.
The 145 "hit_detector" rays measured earlier hit a target at the WRONG plane, which is why that
number looked healthy.

**3. The offset is exactly the fold mirror's thickness, and it is constant.** Shifting the Image
row's `desp_z` by +51.50 (row 7's thickness) moves the termination from -48.77 to 2.73 -- i.e. onto
the sensor -- and MORE rays arrive (167 vs 145):

    | Image desp_z shift | prescription z | rays terminate at |
    |--------------------|----------------|-------------------|
    | 0                  |    2.73        |   -48.77          |
    | +51.50             |   54.23        |     2.73          |

**4. Only the image plane is affected.** Every other row traces at its prescribed position (the
lens surfaces at x = 70.46 ... 125.46 and the mirror at 228.73 all match). So this is not a
whole-chain frame error -- it is the IMAGE PLANE placement specifically.

**5. The rows are WORLD-placed and the prescription is correct.** Row 8: `desp_z = -337.67`,
`tilt_x = 180`, station 340.41, so station+desp = 2.73 exactly. `placement_space()` reports
`world` for rows 1,2,4,5,6,7,8 and `sequential` for 0 and 3. Nothing is wrong with the numbers the
user's scene stores.

**6. It is NOT the folded-sequential path.** `_folded_sequential_trace_rows(app.rows)` returns
**None** for this scene -- it traces NON-SEQUENTIALLY (the BS forces that). So the earlier Step-2
work in `_compute_folded_layout_geometry_for_rows` was aimed at a path this scene never takes,
which is why patching it was inert.

**7. It is not the phantom detectors.** Filtering `derive_branch_detectors` down to the single
`reached_image` leaf (3 -> 1) changed nothing: still 0 reaching, identical 33.0 mm closest
approach. The bugs/0448-style hard-stop theory is refuted for this scene.

### Consequence for the earlier conclusions

* "0457-A is only an invisible picking proxy" was **half right**: the -48.77 actor is indeed
  invisible, but -48.77 is ALSO where the trace terminates, so the number is real in the physics.
  The invisible disk was a symptom, not the bug.
* A and B are therefore the SAME defect, and it matches the user's report exactly: the image plane
  sits one fold-thickness away, and the rays visibly stop there.

### Where the fix goes

The image plane's placement for a chain containing a promoted-mirror fold, where the image row is
WORLD-placed. The fold mirror's thickness (51.5) is being applied to the image plane IN ADDITION to
the row's absolute placement. `must_not_display_fold()` / `placement_space()` already identify the
affected row; what remains is to find the single site that adds that thickness and gate it.

Next probe: instrument the construction of the image/detector target in the NON-SEQUENTIAL trace
path (not the folded-sequential one) and find where a term equal to the fold row's thickness enters
the image plane position.


## The mechanism, fully measured (and one inert fix attempt)

`build_system` produces, for the BS scene:

    S7 (promoted mirror solid)  Th=0.000  DespZ=-234.67  acc_before=288.90  ->  54.23  OK
    S8 (Image)                  Th=0.000  DespZ=-337.67  acc_before=288.90  -> -48.77  WRONG

while the EDITOR's stations are:

    row7  thickness=51.500  desp_z=-234.67  station=288.90  ->  54.23
    row8  thickness= 0.000  desp_z=-337.67  station=340.40  ->   2.73

So the editor's `_row_z_positions()` counts the promoted solid's 51.5 mm thickness and the SPEC
chain zeroes it (confirmed directly: `spec7 thickness=0.000` vs `row7 thickness=51.500`). A
WORLD-placed row's `desp_z` is baked against the EDITOR station, so applying it against the shorter
SPEC station lands the image plane exactly one solid-thickness short. Only rows AFTER a promoted
solid can be affected -- which is why the image alone is wrong.

**Attempt (REVERTED, inert):** re-expressed a WORLD row's `desp_z` against the spec station inside
`_serializable_specs_for_rows`. The BS scene was UNCHANGED (still -48.77); the original scene was
also unchanged (585 hit_detector, so no regression). Reverted.

Why it did nothing is the next question, and there is a concrete lead: wrapping
`_build_system_from_specs` captured SIX calls for this scene and **every one had `desp_z = 0` on
every spec** (all `apply_optical_solid_output_ports=False` reference builds) -- yet the system
`build_system()` returns has `DespZ=-337.67` on S8. So the system carrying the real desps is NOT
built through the calls that wrapper saw. Find that path first:

* is `build_system` returning a CACHED system (`_build_cached_system_from_specs`, the
  `_PARAXIAL_REF_SYSTEM_CACHE`, or the signature cache in `layout_analysis_display.build_system`)
  built at a moment the wrapper missed?
* or does another builder construct the traced system directly from rows, bypassing
  `_serializable_specs_for_rows` entirely?

Instrument the RETURNED system's identity (`id(system)`) alongside every builder call to see which
call produced the object the trace actually uses. Only then place the correction.

**Acceptance test for any fix** (cheap, ~1 min):
`desp_experiment.py 0` must report `terminated_z = 2.73` with `prescription_z = 2.73`, and
`path_diverge.py attachment/machine_vision_AZ85_RA_Mirror.py` must still report
`{'image': 585, 'stopped_at_surface_5': 144}`.


## CONFIRMED AGENT: neutralisation zeroes the fold mirror's thickness

Measured directly on the user's scene (`neutralize_check.py`):

    reached_fold_indices  = [3]        (with the experimental splitter gate; [] without)
    beam_clear_radius     = 14.5
    spec7: folds_beam=True  offbeam=True  th=51.500
    THICKNESS before -> after neutralize_offbeam_inert_solids:
        row 7 Standard   51.500 -> 0.000    <== ZEROED

So the chain is: `neutralize_offbeam_inert_solids` classifies row 7 (the image-side fold
mirror) as an off-beam parked body -- it IS far off the straight +Z axis, because it sits on the
folded arm -- and zeroes its 51.5 mm thickness. Every downstream row's station then falls short by
exactly that, and the WORLD-placed Image row's absolute `desp_z` lands it at -48.77 instead of
2.73. bugs/0243 already anticipated this and exempts folds the beam actually REACHES; the
exemption simply never fires here.

### Why the exemption misses (the one remaining gap)

`folded_beam_reached_mirror_fold_indices` walks from the origin along +Z and reflects only at a
promoted MIRROR fold. The user replaced the object-side RA mirror with a BEAM SPLITTER, and
`_is_promoted_mirror_fold` requires a *Mirror* face -- so the walk sailed straight past the BS and
never reached row 7.

**Experimental fix (REVERTED, incomplete):** accept a splitter face as a fold (a local gate, NOT by
widening `_is_promoted_mirror_fold` -- that also gates fold-to-sequential, and a splitter scene must
stay non-sequential), and walk BOTH legs at a splitter. Effect measured:

* `reached_fold_indices` went from `[]` to `[3]` -- the BS IS now seen as a fold. Real progress.
* the original AZ85 scene was unchanged (`{'image': 585, ...}`) -- no regression.
* BUT row 7 still was not reached, so the acceptance test still fails (image at -48.77).

The single remaining question: after the walk reflects off the BS, why does the resulting leg not
register a hit on row 7's mirror face at (228.73, 0, 54.23)? Candidates, in order:
1. the reflected DIRECTION is wrong (the BS face normal orientation / which face is picked -- the
   plate has two, and its diagonal coating is the folding one);
2. the hit lands outside `hit_radius` (`sqrt(area)+2mm`) for that face;
3. `promoted_mirror_world_center(specs, 7)` returns something unexpected for a world-placed row.

Instrument the walk itself -- print, per leg, the direction after each reflection and the
intersection distance/offset for row 7 -- rather than guessing between these three.

**Acceptance test unchanged:** `desp_experiment.py 0` must report `terminated_z = 2.73`, and
`path_diverge.py attachment/machine_vision_AZ85_RA_Mirror.py` must stay
`{'image': 585, 'stopped_at_surface_5': 144}`.


## THE GAP FOUND: the reached-fold walk treats LOCAL face normals as WORLD vectors

Instrumented the walk (`walk_trace.py`). Face metadata for the two solids:

    spec3 (the BS plate, world centre [0.31, 0, 55.31]):
        Beam Splitter  normal=[0, -0.707, -0.707]  centroid=[0, -0.39, -0.39]  area=8123.5
        Beam Splitter  normal=[0,  0.707,  0.707]  centroid=[0,  0.39,  0.39]  area=8123.5
        (4 Transmit/Port faces, normals +-X and +-(Y,Z))

    spec7 (the image-side fold mirror, world centre [228.73, 0, 54.23]):
        Mirror         normal=[-0.707, 0, -0.707]  centroid=[0, 0, 0]  area=883.9

Walking +Z from the origin:

    spec3 (splitter): denom=-0.7071  distance=+54.54  hit=[0,0,54.54]  offset=0.63 vs r_hit=92.13 -> HIT
                      reflected direction -> [0, -1, 0]
    spec7 (mirror):   leg_dir=[0,-1,0]  normal=[-0.707,0,-0.707]  denom=+0.0000 -> leg PARALLEL to the face: MISS

So the walk folds the beam to **-Y**, then row 7's face is exactly parallel to that leg and can never
be hit -- which is why row 7 is not exempted and its thickness is zeroed.

**But the real trace folds to +X**: the measured ray path is
(0,0,0) -> (0,0,54.23) -> (70.46,0,54.23) -> ... So the walk and the tracer disagree about which way
the beam splitter points.

**Cause: the stored face normals are in the SOLID'S LOCAL frame, and the walk consumes them as
WORLD vectors.** The BS's diagonal reads as a Y-Z tilt locally; in world (after the row's
rotation) it folds +X. Row 7's Mirror normal happens to be world-plausible ([-0.707, 0, -0.707]
folds +X -> -Z, matching the trace), which is exactly why mirror-only scenes worked and this stayed
hidden. It is the same class as bugs/0448 (drawn-vs-traced convention divergence), one layer down.

### The fix

In `folded_beam_reached_mirror_fold_indices`, transform each face's `normal` AND `centroid` by the
row's rotation before the intersection test -- `optical_solid_metadata.rotation_matrix_from_kraken_tilts`
is the existing helper (the 0448 work already uses it to convert between the mesh and trace
conventions). Then the BS reflects the leg to +X, the leg meets row 7's mirror face, row 7 joins
`reached`, its 51.5 mm thickness survives neutralisation, and the Image lands at 2.73.

Combine with the (already written, reverted) local splitter gate so the walk accepts a Beam
Splitter face as a fold at all -- that half is verified to move `reached_fold_indices` from `[]` to
`[3]` with the original scene unchanged at 585.

**Acceptance test unchanged:** `desp_experiment.py 0` -> `terminated_z = 2.73`, and the original
scene stays `{'image': 585, 'stopped_at_surface_5': 144}`.
