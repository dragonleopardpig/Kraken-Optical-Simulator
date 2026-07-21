# 0385 — swap corrupts the lens block's datum surfaces → overlay renders unfolded

**Flags:** `flag_20260721_134702` / `_135006` ("before/after lens swap" on the AZ85 RA-mirror scene,
build 713acba0 — the user's live re-test). The scene stayed intact (0381/0383 worked: mirror 2, camera,
image all held their absolute positions), but the **lens mechanical barrel rendered UNFOLDED** — vertical
at the bottom of the housing instead of folded onto the RA-mirror leg.

## Root cause (general, reproduced headlessly)

Traced the fold override live: before swap the lens rows `[2,3,4,5,6,7,8,9]` all fold; after swap **row 3
(the lens Front Optical Vertex Datum) drops out** → `[2,4,5,6,7,8,9]`. The lens overlay anchors to row 3
(`_lens_front_datum_row_index`), which no longer has a fold override → `fold_transform = None` → the
overlay stays at the raw unfolded datum z.

Why row 3 dropped: the fold-override follower walk (`nonseq_output_ports.py:1421`) SKIPS any row whose
surface is `"Object"`. After swap, row 3's surface was `"Object"` (before: `"Standard"`). The corruption
is in `_normalized_rows_copy` — the swap wraps the new lens block in it, and it treats ANY row list as a
**standalone layout**, forcing its first row → `"Object"` and last → `"Image"`:

```
raw block   : ['Standard', 'Thin Lens', 'Aperture', 'Thin Lens', 'Standard']
_normalized : ['Object',   'Thin Lens', 'Aperture', 'Thin Lens', 'Image']   <- ends corrupted
```

Spliced into the MIDDLE of the scene, that `Object` front datum + `Image` rear datum are not the scene's
real Object/Image (which `_normalize_special_rows` fixes at rows[0]/[-1]), so the corruption persists in
the middle and breaks the fold.

## Fix (general)

The lens block is a mid-scene segment bracketed by Front/Rear Vertex DATUMS — its ends must keep their
real `"Standard"` surface. After `_normalized_rows_copy`, restore the datum ends from the raw slice:

```python
raw_block = new_rows[new_front:new_rear + 1]
new_block = self._normalized_rows_copy(raw_block)
if new_block and raw_block:
    new_block[0].surface = raw_block[0].surface   # front datum stays 'Standard', not 'Object'
    new_block[-1].surface = raw_block[-1].surface  # rear datum stays 'Standard', not 'Image'
```

## Verification

- AZ85 swap: row 3 stays `Standard`; the lens overlay folds again (`rows_with_fold` = `[2,3,4,5,6,7,8,9]`,
  `lens_fold = SET`), matching the before-swap state.
- MV-150 swap: unchanged — all rows + overlays preserved.
- Guard (phase 322) extended: documents that `_normalized_rows_copy` corrupts the ends and that the
  restore yields `Standard` front + rear (flags a premise change if the copy ever stops forcing
  Object/Image).

**Still open:** the swap SLOWNESS / freeze (the folded multi-STEP scene's display rebuild) — separate.

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — datum-end surface restore in
  `swap_imaging_lens_from_folder`.
- `KrakenOS/UI/validate_open3d_lens_swap_block_safety.py` — surface-preserve check (phase 322).
