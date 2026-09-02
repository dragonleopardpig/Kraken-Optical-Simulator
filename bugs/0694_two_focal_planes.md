# 0694 — flags 143341/144226/144429: two focal planes; the centre-prism region IS the root cause

## User (three flags, 2026-09-02 14:33-14:44)
1. "Can check whether these rays focusing on sensor correct?" (saved scene)
2. "rotated: can see 3 rays sharp focus, missing another 3 rays."
3. "Zoom in view of the prism assembly: seems all the prisms are hay wired,
   this should be the root cause!"

## Measured focus census (saved scene; bugs/0694_focus_census.py)
| arm | launch x | rays | waist y | vs plane | waist RMS | RMS @plane | lands x (die -284.2..-261.1) |
|-----|---------|------|---------|----------|-----------|------------|------------------------------|
| A | -28.3 | 201 | -9.90 | 0.00 | 1.1 um | 1.1 um | -284.1 (in) |
| A | 0     | 200 | -9.90 | 0.00 | 0.1 um | 0.1 um | -272.7 (in) |
| A | +28.3 | 120 | -28.50 | -18.6 | 5.8 um | 484 um | -258.1 (OFF-die 3.0) |
| B | -28.3 |  96 | -25.30 | -15.4 | 4.8 um | 422 um | -286.8 (OFF-die 2.6) |
| B | 0     | 160 | -24.90 | -15.0 | 1.0 um | 433 um | -272.7 (in) |
| B | +28.3 | 125 |  -8.50 | +1.4 | 1.3 um |  50 um | -261.5 (in) |

EVERY cone is razor-sharp SOMEWHERE (waists 0.1-5.8 um) — this is not smear;
it is TWO focal planes ~15-19 mm apart, three cones each, arm-ANTISYMMETRIC in
x (A bad at +x; B bad at -x and centre). Face B's device CENTRE is unusable at
the sensor (433 um on 4.5 um pixels).

## Root cause localized (bugs/0694_path_diff.py — representative polylines)
Vertex-count classes per cone: 21/21/20 (A) and 19/19/18 (B) — the bad cones
differ from their arm's good cones by +-1 crossing: DIFFERENT FACE SETS through
the centre-prism region. 15 mm focus split ~= TWO BK7 block crossings' axial
shift (2 x 21.4 mm x (1-1/1.517) = 14.6 mm ✓).
Specific geometry findings:
- mirror1's 45° face plane (y = 52.8 - x) descends INTO the centre-prism band:
  at x = +22.8 the fold happens at y 30.0, BELOW the centre prism's top face
  (y 37.19, spanning x ±37.5) — the A +x field folds while still inside the
  prism glass region (its 37.19 exit vertex is MISSING; med 20 verts).
- the B arm's centre-region traverse runs at z -35.68 where the mirror image
  of arm A's (-15.78 about the -25 split line) would be -34.22 — a 1.46 mm
  asymmetry (= the 0691 mirror2 refocus amount; suspicious, unverified), and
  B crosses ONE face on the traverse where A crosses TWO.
The user's "prisms are hay wired" instinct is CONFIRMED as the root-cause
direction: the modeled centre-region solids (extents/poses/face sets) route
different fields through different amounts of glass.

## The rotated-scene "missing 3 rays" (flag 144226) is a SEPARATE, known item
The 3 sharp cones = arm A through the 0693 carry fix (working as designed).
The 3 missing = the documented faceB mirrored-launch limitation under a
PARTIAL rotation (bugs/0693 doc): the instrument aims at the mirror image of a
stop that no longer sits in the symmetry plane. The prisms did NOT move (B-train
desp/tilt byte-identical) — correct for a partial rotation. The "haywire" look
in flag 144429 also includes two display artifacts: the two centre RA prisms
superimpose into a bowtie in the edge-on LEFT view, and the world-authored
band/strip labels linger at the old sensor position after a rotation.

## Next steps
1. Verify the REAL mirror1 width / centre-prism extents against the vendor CAD
   (attachment/Prism_Assembly) and fix the modeled solids (general fix, then
   re-census: all six cones should land on ONE plane at y -9.9).
2. Then re-derive bands/strips (the x-extreme cones landing off-die may also
   shrink the usable field) and re-pin the 0672 guard.
