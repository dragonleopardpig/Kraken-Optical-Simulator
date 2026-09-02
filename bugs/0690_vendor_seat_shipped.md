# 0690 — flag_20260902_074210 ("same as previous flag"): the vendor lens seat SHIPPED

## Result (the arc's goal, blocked since the 0680 arm-B work)
Both arms now reach the sensor at NEAR-PARITY:
- arm A (chain): 3249 launched / **1800 on-strip** at sensor z ~ -28.8, central
  waist 13.1 um;
- arm B (face B): 3249 launched / **1980 on-strip** at z ~ -20.7 (was 20!).
The strips sit ~+-4 mm about the z=-25 lens axis -- exactly the vendor split-field
prediction (+-9.4 mm arm field offset x m 0.42).

## What actually made it work (three pieces)
1. **The 0689 v2 frame-desp seat was RIGHT but over-applied**: the fold walk's
   carried frame ADVANCES FROM EACH POSED ROW'S CENTRE (nonseq_output_ports ~2321),
   so a desp on every row of the block COMPOUNDED (-9.46 x 7 ~ -66 mm -- everything
   died). ONE desp on the FIRST row of the contiguous follower block ("Front
   Optical Vertex Datum") shifts the whole downstream train -- lens, stop, filter,
   the mirror-2 fold, and the Image -- onto the vendor axis.
2. **No pupil-aim offset was needed after all**: the 0625 launch-measure
   re-measures on load and the -9.46 shift sits within its correction trust
   region, so the launcher self-steered. (The 0689 all-rows failure was beyond
   the trust region -- hence "0 reach" there, which had suggested a launcher
   feature.) The authored `launch_pupil_aim_offset` knob was still added to the
   world-bundle builder + layout settings (default absent = today's behavior) --
   harmless, and the honest escape hatch for scenes whose offset exceeds the
   measure's reach. The om05a scene carries [0, 0].
3. The mirrored face-B launch inherits the seat symmetrically through the
   `mirror_launch_plane_z=-25` reflection -- no separate arm-B work.

## Also
- faceB spec role briefly flipped to 'imaging' chasing per-field colours --
  REVERTED (degraded the readouts); arm B keeps its single identity colour for
  now (per-field colours for additive sources remain a cosmetic follow-up).
- The delivered-magnification HUD readout (Resolution/Magnification lines) is
  absent on the seated scene -- the measure's readout path needs a look
  (follow-up); the trace itself is healthy.
- /tmp scratchpad rolled back AGAIN overnight (old scripts resurfaced) -- the
  0689 scene backup only survived because it was ALSO copied into bugs/
  (om05a_folded_pre0690_backup.py). Builders/backups in bugs/ remains the rule.

## Guard
0672 scene guard re-pinned end-to-end for the seat (B1 arm-A strip z -30.4..-27.4
>=1600; B5 arm-B strip z -22.5..-19.0 >=1500 -- near-parity is now PINNED):
15/15 PASS.
