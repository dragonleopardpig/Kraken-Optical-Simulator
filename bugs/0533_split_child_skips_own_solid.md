# 0533 — the split's reflected child never exited its own solid (two legs)

## Evidence

The plate-BS ghost (`S3/transmit -> S3/reflect`) reflected at the FAR face — verified
geometrically correct against the shared 45° normal — then terminated
`no_next_intersection` 1.2 mm INSIDE the glass, flying off 15–17° high with its IN-GLASS
direction (flag_20260804_082939; zoom 084655 shows rays crossing the drawn plate outline
with no kink). A real plane-parallel-plate second-surface fold exits through the entry
face and emerges PARALLEL to the front-surface fold.

## Leg 1 — the row-level skip killed the re-crossing

`__NsTraceSplitChildSkipSurface` exempted only ENTRY-face splits (0445: the transmit
child must exit through the far face). The EXIT-face split is the mirror case: the
REFLECT child goes back INTO the glass and must re-interact with its own row. Fix: the
`"exit"` transition returns None too; the leaving child is protected by the origin nudge.

## Leg 2 — the reflect child's media state crossed the boundary

`refl_sign = +1.0`, so `__NsRayMediaEvent` treated the reflect child as a TRANSMISSION
and ran the face's exit transition: volume popped, medium = ambient at the glass index.
The later real exit then computed N == Np — a kink point with NO refraction (the
15–17° emergence). Fix: the spawn passes a reflection sign (−1) to the MEDIA event only —
a reflection never crosses the boundary — while the trace SIGN keeps `child_sign`.

## Verified

Second-surface-coating configuration (splitter on the far plate face — the legitimate
0444/0445 model): all 279 reflect children exit the plate through a real `refraction`
event and the emergent fold is parallel to the front-surface fold to **median 0.00°**
(279/279 within 1.5°); the fold now IMAGES (222 rays reach the target). Violated
principles restored: rays must not vanish; overlay-ON must show true light.

## Guard

`validate_open3d_0533_split_child_exits_solid.py` (penta phase 428): source exemption +
the far-face-coated real-scene drive (exit events + frame-free parallelism check via the
internal-reflection-derived plate normal).
