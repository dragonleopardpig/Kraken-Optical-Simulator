# 0394 — swap camera-clearance: the mirror obstacle centre was STALE (root cause)

**Flag:** `flag_20260722_080341_762` — "after lens swapping, the camera still crash." Build
23a60f65 (= 0393). The 0393 instrumentation finally captured the ground truth in
`swap_clearance_diagnostics`:

```
cam_bounds:      [200.9, 270.9, -35, 35, -22.63, 51.0]     ✓ correct (live)
obstacle_bounds: [193.65, 218.65, -12.5, 12.5, 59.4, 84.4]  ✗ STALE
leg:             [0, 0, -1]                                  ✓ correct (beam folds down to the camera)
deficit:         0.0
```

## Root cause

The camera bounds and the leg were right all along. The **mirror obstacle bounds were stale**:
`_promoted_solid_world_bounds` read `row.advanced['StepOverlayPromotion'].bounds_*_world`,
which is captured at PROMOTION time and never updated when the solid is moved. The RA mirror
had been dragged since promotion:

| Row 8 mirror | X | Z |
|---|---|---|
| Stored promotion (used) | [193.7, 218.7] | [59.4, 84.4] |
| **Current actor (real)** | **[223.3, 248.6]** | **[40.4, 65.7]** |

With the stale centre the obstacle sat ~30 mm away and Z-separated from the camera, so the
clearance check found no overlap and the deficit was 0 — the camera stayed crashed.

## Fix

The promotion **extent (size)** is invariant under a move, but the **centre** is not. And a lens
swap does not move the mirror, so its live position is already in the last scene bundle. So
`_promoted_solid_world_bounds` now keeps the promotion **size** but re-reads the **centre** from
the live `optical_solid` scene-bundle placement (`_promoted_solid_current_center`, matched by
row index), falling back to the stale centre only when no live placement exists.

On the flag geometry: re-centred obstacle → x[223.5, 248.5] z[40.5, 65.5] (matches the real
actor), deficit **12.5 mm** (was 0), gap 13.48 → **25.98 mm**, camera clears the mirror along the
−Z fold leg. `obstacle_center_source` is recorded (`live_bundle` / `stale_promotion`) in the
diagnostics.

## Verification

- **Guard** `validate_open3d_lens_swap_auto_refocus` (phase 326): with STALE (Z-separated)
  bounds the deficit is 0 (reproduces the bug); with the LIVE bundle centre it is ~12.5, the
  re-centred obstacle matches the real actor bounds, and `obstacle_center_source=live_bundle`.
  All 0388–0393 cases still hold.

## The saga (why it took several passes)

0391 (datum, flange-only) → still crashed; 0392 (mesh clearance) → math right but returned 0
live; 0393 (record-path fallback + **instrumentation**) → the diagnostics named the empty/ wrong
input; 0394 → the actual root cause (stale obstacle centre). The lesson: when a headless repro is
impossible, ship the diagnostic first — the flag's `swap_clearance_diagnostics` pinned it in one
round.

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — `_promoted_solid_current_center` +
  `_promoted_solid_world_bounds` re-centres on the live placement; deficit records the source.
- `KrakenOS/UI/validate_open3d_lens_swap_auto_refocus.py` — stale-vs-live re-centring test.

## In-app eyeball still owed

Verified against the flag's real numbers; the live bundle lookup runs only in-app. Confirm on a
real AZ85 swap that the camera now pins clear of the moved mirror (`swap_clearance_diagnostics`
should read `obstacle_center_source: live_bundle`, `result: ok`, a non-zero deficit).
