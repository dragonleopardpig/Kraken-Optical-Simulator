# 0673 — flag_20260831_201424: slow trace, "where is the usual 9 point", oversized surrogate

Four asks; the first three land here, the fourth (real prism assembly + 3D cube
device) continues as 0674.

## Fixes

1. **Trace time + "illuminator look"**: the folded scene sampled a 13x13 field grid
   (169 fields x 81 pupil = 13689 paths, minutes). The scene now authors the
   USUAL 9-POINT sampling on the device faces (field 4.3 image = the face edges at
   object +-10 mm, count 3 -> 3x3): 729 paths, the full guard runs in 23 s.
2. **The authored field now survives loads** (product fix, layout_table_workbench):
   the load-time camera coverage autofill defers to a USER-AUTHORED field (0615
   doctrine) -- it re-couples only when the saved field IS the autofill's own
   value (the bugs/0312 signature), which preserves bug-0033 load/pick parity for
   every interactively coupled camera scene. The straight scene's 54x54 FOV field
   (11.52 x 13) is authored and now also survives (guard 0670 B3 re-pinned to the
   half-height).
3. **"Lens surrogate oversized"** = the dia-80 prism-plate discs. Physics wants
   them big (the launch-measure probes need WIDE first apertures: dia 46 broke the
   aim to 2% reach -- an unexplained machinery sensitivity, noted), so they stay
   dia 80 but are HIDDEN (drawing=0); the real prism assembly becomes the visible
   geometry (0674). The STRAIGHT scene keeps dia-30 drawn plates: physically
   honest clipping of beyond-face fields (its fan machinery is insensitive).

## Known frontier (pinned, not hidden)

The 3x3 grid's four cardinal fields + centre deliver (65/65/65/64/16 rays); the
DIAGONAL corners mis-aim through the two folds (3/3/0/0 rays) -- the folded launch
seam (project_nonseq_first_order_seam). Guard B1 pins >=250 rays + >=4 strong
fields and records the per-field census.
