# 0595 — the sensor square's edge renders in two colours (coincident actors) (FIXED)

Flag `flag_20260809_100904_100`: *"I turn on Illumination overlays as well as other analysis, none
of them works. **Also note the sensor square edge is now split to 2 colors.**"*

The first half is **bugs/0593** (the field-aberration scan cannot run on a folded scene) — same
scene `machine_vision_Apo75.py`, same three overlays. This bug is the second half.

## Established from the recordings

Two actor groups draw the *same* detector square. From `row_actor_bounds` in both recent
recordings:

| recording | actor key | bounds (x, y, z) |
|---|---|---|
| `flag_20260809_100904_100` | row `8` | 233.279 … 265.862, ±16.292, **−5.058 … −5.041** |
| | row `100000` | 233.279 … 265.862, ±16.292, **−5.049 … −5.049** |
| `flag_20260809_102408_191` | row `8` | 285.795 … 318.378, ±16.292, **49.699 … 49.723** |
| | row `100000` | 285.795 … 318.378, ±16.292, **49.711 … 49.711** |

x and y are **identical to the micron** (32.583 mm — the detector row diameter), and the `100000`
plane sits exactly at the MIDPOINT of row 8's z span. Two nearly-coplanar surfaces ~0.02 mm apart
is textbook **z-fighting**: along the rim, whichever is nearer alternates, so the edge renders in
two interleaved colours. Present on both scenes, so it is not scene-specific.

Note `row_actor_bounds[k]` is the **merged union** of every actor filed under key `k`
(`open3d_event_recorder.py:427`), so row 8's 0.017–0.024 mm z span may be two flat actors rather
than one tilted one. Both readings are still open.

## What the scene bundle rules OUT

Measured on the flagged Apo75 scene (`_build_scene_bundle`, 259 targets):

```
row=0       is_detector=False draw_suppressed=False center=[0. 0. 0.]
row=3       is_detector=False draw_suppressed=False center=[107.041 -0. 54.283]
row=8       is_detector=True  draw_suppressed=False center=[179.788 -0. -3.349]   <- the ONLY drawn detector
row=100000  is_detector=True  draw_suppressed=True  center=[-104.798 11.18 35.652]
  ... 100001 .. 100255, ALL draw_suppressed=True, ALL at that same phantom point
```

So this is **not** the "2 square detectors per arm" redundancy class that
`drop_superseded_image_display` (`scene_builder.py:860-882`) exists to fix. That mechanism is
correctly dormant here: `has_drawn_branch_detector` is False because every branch detector is
suppressed, which is exactly bugs/0291's rule (an illumination flood parks suppressed branch
detectors as ray hard-stops, and the sequential Image is the one real detector — dropping it left
the scene with no visible detector at all).

**Therefore the actor filed under key `100000` at the sensor footprint is not the branch-detector
target's own geometry** — that target is suppressed and parked 350 mm away. Something else is
filing an actor under the synthetic key.

## Two concrete suspects

1. **A default row key of `100000`.** `open3d_thickness_dimensions.py:432` and `:483` both do
   `int(getattr(target, "row_index", 100000) or 100000)` — any target without a row index lands on
   key 100000, and the `or` also maps a legitimate row **0** there.
2. **Draw-suppressed branch detectors still get overlays.** That same
   `add_branch_exit_to_detector_dimensions` filters on
   `metadata["target_source"] == "branch_detector"` and on `_thickness_dimension_is_hidden`, but
   **never checks `draw_suppressed`** — so all 256 phantom detectors are still eligible for an
   exit→detector dimension. Whether their geometry can reach the sensor footprint is unverified.

## Done here

1. **The recorder now captures per-actor detail.** `row_actor_detail[row]` carries each actor's
   key, bounds, visibility and colour, with `row_actor_counts[row]` giving the untruncated total
   (capped at 12 per row, because this scene carries 256 branch detectors). The merged
   `row_actor_bounds` is unchanged, so `analyze_open3d_recording.py` and the existing guards keep
   working and old recordings still parse. **The next recording of this flag will say outright
   whether row 8 is one tilted actor or two flat ones, and which code filed the `100000` actor.**
2. **Fixed the synthetic-key default** (suspect 1): `int(getattr(target, "row_index", 100000) or
   100000)` mapped a legitimate row **0** onto the branch-detector key as well as a missing index,
   so row 0's hide-state and recorded actors were filed under 100000. Now an explicit `is not None`
   test. On the flagged scene this is latent rather than the cause -- branch detectors never carry
   row 0 -- so it is a correctness fix, **not** a claim to have fixed the two-tone edge.

Suspect 2 (overlays drawn for `draw_suppressed` branch detectors) is deliberately **not** changed:
it is a behaviour change that would remove overlays, and without a repro it cannot be validated.

## FIXED — Quick Estimation's image-plane duplicates (phase 454)

The per-actor recorder detail (shipped for this bug) settled it, by ruling things OUT: the
recorded row-8 "duplicate" has **opacity 0.0** — it is the bugs/0033 *suppressed* Image disk,
invisible and innocent — and the 100000-blue actor is the coverage overlay's 8% pick quad. None
of the recorded row-keyed actors was the second tone. The visible culprit only appeared on an
actual LOOK at the flag screenshot: the square's top/right edges are **orange** and bottom/left
are **YELLOW**.

Two identical-size squares draw at the sensor footprint when Quick Estimation and the detector
coverage overlay are both on:

| element | colour | source |
|---|---|---|
| vendor sensor square | orange (0.98, 0.45, 0.05) | `_scene_detector_overlay_specs` |
| QE recommended-sensor rect | yellow (1.0, 0.9, 0.2) | `quick_estimation_overlay.py` |

Coplanar and congruent → z-fighting → the rim alternates colours. (QE's image circle likewise
coincides with the coverage image circle — same hue, so it never showed as two-tone, but it was
double-drawn too.)

**Fix** — the bugs/0033 masquerade rule, applied to QE: the scene refresh threads
`suppress_image_plane_duplicates=detector_coverage_active` through the inspector wrapper (the
bugs/0319 kwarg-threading trap) into `QuickEstimationOverlayService.add_overlays`, which then
skips its image-plane circle + rect. QE keeps its object-plane FOV circle, ghosts and pick
disks; with the coverage overlay off, QE draws everything exactly as before.

**Verified by rendered snapshots in the Normal-to-Sensor view** (the user's own view): with
Det + QE on, the square's edge is a single uniform orange on all four sides; with Det off,
QE's yellow rect returns alone. Actor-level: Det+QE on → 0 visible yellow rects, 3 coverage
square actors; Det off → 1 yellow rect.

Guard: phase 454 (`validate_open3d_0595_sensor_square_single_edge`) — verified failing on all
four checks pre-fix, including the real render (1 yellow rect drawn).

## Superseded diagnosis notes (kept for the record)

Dump `inspector._row_actor_map[100000]` and each actor's individual bounds/colour in the **live**
app. The headless route stalls short of this: `refresh_from_editor` returns early on the async
trace kick, and `_paint_bodies_while_async_trace_runs` draws rows 1–7 only — the detector and
branch actors never appear, so row keys stop at 7.

Worth fixing regardless: the recorder captures only MERGED bounds per row, which is why this flag
cannot be settled from the recording. Capturing per-actor keys under each row would make this
whole bug class diagnosable without a live repro.

## Do not fix by nudging

Per `feedback_display_follows_physics`: if row 8's z span turns out to be a genuine ~0.04° tilt,
the fix is in the placement and suppressing the z-fight would hide a real defect. If instead it is
a redundant overlay, the fix is to stop drawing it — not to offset it.

## Guard

An image-snapshot test (`feedback_image_snapshot_tests`) is the right guard — the defect is
visible and a property assertion on either actor alone would pass. Assert that the detector rim
renders a single colour, and separately that no two scene actors share x/y bounds to within a
micron while sitting within ~0.05 mm in z.
