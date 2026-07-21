# 0388 — lens swap: auto re-solve best focus, clamped to the upstream clearance

Follow-up (b) from bugs/0387's "OPEN" list. After "Swap Imaging Lens from Folder" the image
lands **defocused** on the sensor: bugs/0383 deliberately keeps the camera + downstream mounts
at their ABSOLUTE axial positions (so the fold arm doesn't collapse), but a different lens
images at a different plane. The user must then hand-solve focus every swap.

## Fix

The swap now finishes the job: after `_commit_history_capture()` it calls
`_swap_auto_refocus_to_best_focus()`.

- **Move the image, not the beam.** It reuses `snap_detector_to_image_plane()`, which moves
  ONLY the final gap (`rows[-2].thickness`, the image distance) — never the source, aperture,
  or lens geometry. So the re-solve **cannot** reproduce the escaping-ray / broken-ray
  failure mode (that is a beam-width-vs-prism-aperture issue, a separate open item); it only
  slides the sensor plane to where the new lens focuses. The underlying solve is folded-aware
  (`_real_ray_best_focus_shift_for_rows` handles the RA-mirror leg via its straight
  equivalent), so it works for the folded AZ85 scene as well as flat ones.

- **Respect the current constraints (user's requirement — "camera don't crash to the RA
  mirror").** After the solve, the image gap is CLAMPED to `_swap_refocus_min_gap()`: a
  conservative 2 mm mechanical clearance, EXCEPT when the upstream element is a thin promoted
  fold mirror whose own axial reserve is already below that — then the reserve caps the
  min-gap so the clamp never demands more room than the mirror physically occupies. If best
  focus would need the sensor closer than that, the gap is pinned at the minimum and the user
  is flagged ("focus limited by N mm clearance to the upstream element…") rather than the
  sensor being driven into the mirror. **Clamp + flag, never collide.**

- If the terminal row isn't an `Image`, or the solve can't compute (`snap` returns False —
  e.g. no computable best-focus), it is a safe **no-op**: no mutation, no flag.

## Why not auto-orient too?

Follow-up (a) (new lens comes in reversed) was investigated and **dropped for the common
case**: the user's 0703 surrogate is aperture-SYMMETRIC (front == rear clear aperture ==
13.1 mm), so no aperture/geometry heuristic can detect a reversal — an auto-flip would be a
coin-flip that could WORSEN a correctly-oriented import (the user's own concern: "what if the
import is already correct for another lens?"). The manual "Flip lens facing" toggle stays the
source of truth; a guarded auto-orient is reserved for clearly-asymmetric lenses only.

## Verification

- **Guard** `validate_open3d_lens_swap_auto_refocus` (penta phase 326), display-free with a
  stub editor: snap-can't-compute → no-op/no-flag; sub-floor solve → clamped to the floor +
  flagged; safe solve → left exactly as solved, no flag; a thin fold-mirror reserve caps the
  min-gap; an Image-less layout is refused.
- **AZ85 (folded) + MV-150 (flat) headless swaps** still complete without error with the
  refocus wired (the folded best-focus solve is a headless no-op because the folded mesh
  trace can't run offscreen — it exercises live only; the flat swap is unaffected).

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — `_swap_auto_refocus_to_best_focus`,
  `_swap_refocus_min_gap`, `_SWAP_REFOCUS_MIN_CLEARANCE_MM`; call wired into
  `swap_imaging_lens_from_folder` after the history capture.
- `KrakenOS/UI/validate_open3d_lens_swap_auto_refocus.py` — guard (phase 326).

## In-app eyeball still owed

The folded best-focus solve only runs live (needs the folded mesh trace). Confirm on a real
AZ85 swap that the sensor snaps to focus and the clearance flag fires if the new lens would
pull it into the mirror.
