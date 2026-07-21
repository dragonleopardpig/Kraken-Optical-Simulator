# 0383 — lens swap collapses the downstream folded arm (general)

**Flag:** `flag_20260721_122714_082` ("Multiple misplacement issue after swapped") on
`machine_vision_AZ85_RA_Mirror.py` (ELS-85, a folded RA-mirror scene). After a Swap, the whole
downstream arm — the second RA mirror, the camera, the image — jumped ~100 mm toward the lens.

## Root cause (reproduced headlessly, general)

The imaging-lens block is `Front Optical Vertex Datum … Rear Optical Vertex Datum`. The **Rear Datum's
thickness is the SCENE gap to whatever follows the lens** — a fold mirror / camera / image the user
placed — **not part of the lens**. The swap spliced in the fresh lens folder's block verbatim, whose
bare rear thickness is ~0 (a single-lens layout images almost immediately), so the downstream gap
collapsed:

| | Rear Datum thick | Mirror 2 z | Image z |
|---|---|---|---|
| before | 103.3 | 288.9 | 340.4 |
| after (naive) | 0.0 | **180.6** | **232.1** |
| after (fix) | 108.3 | **288.9** | **340.4** |

## Fix (general, not scene-specific)

When a **physical element** (not the terminal image) follows the lens, the swap now keeps the first
downstream row at its **absolute axial position** by absorbing the lens-length change into the new Rear
Datum thickness:
- `_swap_preserves_downstream(rows, rear)` — True when the row after the lens block is not the terminal
  image (a mount / mirror / camera to hold put); False for a bare lens (image right after → the image
  follows the new back focal distance, unchanged behaviour).
- `_swap_downstream_gap(rows, rear, downstream_start_z)` — the Rear Datum thickness that lands the first
  downstream row back at its pre-swap z; None if that would be negative (a longer replacement lens),
  so a bad thickness is never forced.

The anchor is captured BEFORE the splice and re-applied AFTER `_normalize_special_rows()` (which
recomputes datum thicknesses from the new lens and would otherwise re-collapse the arm). It re-finds the
rear datum via `_imaging_lens_block_indices()` so it is robust to normalisation.

## Verification

- Real AZ85 swap: Mirror 2 and Image now stay at 288.9 / 340.4 (were collapsing to 180.6 / 232.1); the
  lens block still shortens correctly (rear vertex 185.6 → 180.6).
- MV-150 swap (bare Image after the lens): the fix is a no-op — all rows + overlays preserved.
- Guard (phase 322) extended with the preserve-decision + gap math + the bare-lens no-op + a
  negative-gap guard, on synthetic rows (portable, no scene needed).

**Still under investigation:** whether the lens STEP overlay itself also needs the display-fold
re-applied after swap, or whether fixing this downstream collapse resolves the visible misplacement on
its own (the collapsed arm alone scrambled the view). Owed: an in-app eyeball / render check.

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — `_swap_preserves_downstream`,
  `_swap_downstream_gap`, and the anchor capture/restore in `swap_imaging_lens_from_folder`.
- `KrakenOS/UI/validate_open3d_lens_swap_block_safety.py` — downstream-anchor checks (phase 322).
