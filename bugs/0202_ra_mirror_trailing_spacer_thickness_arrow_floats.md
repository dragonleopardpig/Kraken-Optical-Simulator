# 0202 — BUG: a promoted solid's trailing-spacer thickness arrow floats past the exit face

**Status: RESOLVED. The trailing AIR spacer inserted after a promoted optical solid now
anchors its NEAR thickness arrow to the solid's rendered EXIT face and labels the REAL air
gap (solid exit → next surface), instead of floating its near endpoint at the reserve
origin ~27.5 mm downstream. The edit dialog + `apply_dimension_value` round-trip the
reserve dead-space (`_trailing_spacer_gap_offset`) so the drawn gap stays WYSIWYG. Guard
`validate_open3d_trailing_spacer_exit_gap.py`.**

## Flag

Reported in the 2026-07-01 review pass of the folded AZ85 RA-mirror scene
(flag_20260701_201444):

> "S2 thickness overlay: one side arrow still point to wrong location"

## Root cause — the near endpoint took the reserve origin, not the solid exit

On the folded AZ85 RA-mirror scene the mirror cube (row 1) is promoted with a **40 mm axial
reserve**, but the physical cube exit face sits only **12.5 mm** past the fold vertex. The
in-path promote (bugs/0079) inserts an AIR "trailing spacer" row (row 2,
`InPathTrailingSpacer=True`) that carries the downstream gap while keeping the solid's large
diameter so the trace never clips.

The thickness overlay for that spacer took its NEAR endpoint (`p0`) from the row
**reference** — the reserve origin at X=40, ~27.5 mm downstream of the cube exit at X=12.5.
So the near arrow + leader floated in mid-air on the beam instead of landing on the mirror's
exit face, leaving an unlabeled ~27.5 mm dead-space. This is the exit-side twin of the
already-handled "gap to solid" ENTRY case (where the NEXT row is a promoted solid and `p1`
is snapped to the solid's entry face).

## Fix — anchor the near endpoint to the solid EXIT face and label the real gap

New helper `_solid_exit_gap_for_trailing_spacer(rows, row_index, p0, p1)` in
`services/open3d_thickness_dimensions.py`, the mirror of the entry-side "gap to solid"
handling:

- fires only when `row_index` IS an `InPathTrailingSpacer` (via
  `scene_builder._is_inpath_trailing_spacer_row`) AND the PREVIOUS row is a promoted
  optical solid (`_row_optical_solid_stl`);
- projects the solid's rendered faces onto the arrow direction
  (`_optical_solid_span_points`) and takes the downstream-most (max-projection) face as the
  EXIT point;
- re-anchors `p0` to that exit face and labels the REAL air gap `gap from <solid> = G mm`
  (mirror exit → front datum ≈ **69.95 mm** on AZ85);
- returns `(None, None, None)` headless / when the row is not a trailing spacer / when the
  body has no rendered actors, so non-spacer rows never get a false anchor.

`add_overlays` calls it right after the entry-side block, sets `p0 = exit_point`, and
records the **reserve dead-space** `_trailing_spacer_gap_offset[row_index] = gap - thickness`
(≈ 27.5 mm), rebuilt each redraw from live geometry.

### Keeping the edit round-trip WYSIWYG

The displayed gap (69.95) differs from the stored row thickness (42.45) by the reserve
dead-space (27.5). The entry-side "gap to solid" case needs no offset because the cube entry
face coincides with the row origin; the exit case does, because the exit face is 27.5 mm
short of the next origin. So:

- `edit_dimension` prefills `current + gap_offset` — the dialog edits the DRAWN gap;
- `apply_dimension_value` converts the typed gap back with `next_value - gap_offset` — the
  stored thickness lands so the front datum sits exactly the typed gap past the mirror exit.

Both reads are defensive (`(getattr(self, "_trailing_spacer_gap_offset", None) or {}).get(...)`)
so services that bind these methods onto light fakes without the dict still work.

## Verification (done)

`KrakenOS/UI/validate_open3d_trailing_spacer_exit_gap.py` (standalone, display-free; the
cube exit face is synthesised from world bounds so it runs headless without a renderer):

1. the helper anchors the NEAR endpoint to the cube exit (X=12.5), not the reserve origin
   (X=40) — the ~27.5 mm float is gone;
2. the drawn gap is the true mirror-exit → front-datum distance (69.9529 mm) and the offset
   = gap − stored thickness = 27.5 mm; the label reads `gap from solid = 69.95 mm`;
3. NON-spacer rows + the solid row itself return None (no false anchor);
4. editing the drawn gap round-trips: apply(row, 80.0) stores thickness 52.5, so a redraw
   reads 80.0 back — WYSIWYG; a row with no recorded offset edits its raw thickness;
5. source contract: `add_overlays` records the offset + uses `solid_exit_gap_label`; the
   edit dialog + apply consult `_trailing_spacer_gap_offset`.

All 9 pre-existing thickness/gap guards stay green after the change.

STANDALONE (NOT a penta phase) — like the rest of the folded RA-mirror suite (bugs
0185-0201), the overlay geometry is driven directly by the display-free guard. In-app
eyeball still owed (headless cannot render the arrow + leader on the drawn cube).
