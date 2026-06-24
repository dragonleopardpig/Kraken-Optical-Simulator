# 0131 — "live gap disappears once the placed LED becomes a camera"

## Symptom

`flag_20260624_083154_091`:

> "dragging the LED passed the lens, and the live gap shows up. Placing it and the
> LED now becomes Camera, sensor and image plane attached to it. Drag again no
> longer show live gap."

While the bare LED STEP is carry-dragged the green live edge-gap dimension tracks
the cursor. The moment the LED is placed and promoted into a **camera** (sensor +
image plane glued to it), a second drag shows no live gap at all.

## Root cause

`Kraken3DInspector._step_overlay_axial_gap` picks the "previous" component — the
one whose far edge the gap is measured to — by axial **center**: among components
whose `proj_center` sits before the dragged body's center it took the one with the
largest `proj_max`.

A camera carries a glued detector / image plane that sits **inside** the camera
body. In the flag geometry:

- camera STEP body: `z[159.24, 235.64]` (center 197.44, near edge 159.24)
- glued image plane: `z = 170.72` (row 6) — **11.5 mm inside the body**
- object plane: `z = 0`; lens STEP: `z[275, 331]`

The buried plane's center (170.72) is before the camera center (197.44) and its
`proj_max` (170.72) is the largest among the candidates before the center, so it
**won** the search. The gap then came out as `near − far = 159.24 − 170.72 =
−11.5 mm` — a backward arrow buried inside the camera body, i.e. effectively no
visible dimension. The bare LED had no glued companion, so the search found the
genuine previous and the live gap showed; gaining the companion silently broke it.

## Fix

**Choose the previous component by far edge, not center: a genuine previous must
end at or behind the dragged body's near edge.**

1. New pure static helper
   `Kraken3DInspector._previous_axial_component(me_near, extents, overlap_eps=1e-6)`
   returns the nearest candidate whose `proj_max ≤ me_near` (the dragged body's
   near edge), rejecting any component that far-overlaps the body. A glued
   companion buried inside the body is dropped, so it can no longer masquerade as
   the preceding optic. A small `overlap_eps` admits a *touching* previous
   (gap 0) against float noise.
2. `_step_overlay_axial_gap` reads the near edge (`me_near = proj_min`) and
   delegates the selection to the helper. With the camera dragged, the buried
   image plane is skipped and the gap measures to the genuine preceding element
   (here the object plane at `z = 0` → a clean `+159.24 mm`), so the live gap
   reappears.

The working in-flight LED drag is unchanged (it has no buried companion; the
genuine previous already ends before the LED, so the far-edge rule keeps it). The
fix is scoped to the STEP-overlay drag gap; the promoted-row gap paths
(`_row_slide_axial_gap`, `_row_overlay_axial_gap`) are untouched.

## Test

`KrakenOS/UI/validate_open3d_camera_live_gap.py::run_checks` — display-free; calls
the real `Kraken3DInspector._previous_axial_component`:

- **A** empty / `None` candidates yield no previous;
- **B** the flag geometry — a glued companion buried in the body is rejected and
  the object plane is chosen, giving a **positive** gap, not the bogus negative;
- **C** among several cleanly-preceding candidates the nearest (largest
  `proj_max`) wins;
- **D** edge semantics — a previous touching the near edge (gap 0) is admitted, a
  hair past it is rejected;
- **E** malformed / non-finite extents are skipped, not fatal;
- **source contract** — the overlay delegates to `_previous_axial_component`,
  selects by the near edge (`proj_min` / `me_near`), no longer gates on
  `proj_center`, and the helper rejects far-overlap via `overlap_eps`.

Penta **phase 121** runs this guard. Mutation-tested: disabling the far-overlap
rejection (`if False`) flips B (the lens/buried companion wins) and D (a component
past the near edge is wrongly admitted).

## Note — in-app eyeball owed

Headless llvmpipe can't drive the embedded-VTK carry-drag, so the actual
drag-the-camera → green-live-gap-reappears gesture is verified in-app. The guard
pins the previous-component selection math (the overlap rejection) that the
overlay depends on.
