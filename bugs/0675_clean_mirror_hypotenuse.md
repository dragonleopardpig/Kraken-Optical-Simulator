# 0675 — flag_20260901_080032: mirror bump leak + surrogate still bigger than the body

Two asks, both landed (scene + data; protected by the existing phase-505/506 guards):

1. **"Remove the little bump from the RA mirror — it causes ray leak; the
   hypotenuse should be a smooth mirror surface."** Confirmed and better than
   suspected: the assembly's mirror STEPs carry the mechanical engineer's
   RAY-REPRESENTATION geometry on the hypotenuse. Rays hitting those bump faces
   (default Transmit/Port) leaked THROUGH the fold -- the stray fans past mirror2
   AND the weak centre field (16/65 rays) were both the bump, not only the launch
   seam. Fix: both mirrors replaced by SYNTHESIZED clean RA prisms
   (`bugs/0675_clean_mirrors.py` -> `om05a_components/mirror{1,2}_cleanb.step`,
   OCC wedge, hypotenuse plane in the SAME local (0,1,-1) family as the
   extractions so every 0672 seating contract holds -- the first synthesis used
   the (0,1,+1) family and traced 0 rays). Result: 325/729 reach (was 281), ALL
   five cardinal+centre fields at the full 65 rays, no stray fans in the render.
2. **"Lens surrogate still bigger than the lens body":** the 48.56 discs equal the
   V38 housing's WIDEST flange (the 0668 mid-extent clamp) but stand proud of the
   typical barrel. Both om05a scenes now draw the surrogate discs at 36.0 (the
   V38's glass envelope); no ray is clipped -- bugs/0624 extends blackbox trace
   apertures beyond drawn discs.

Gotchas re-learned: the STL cache keys on FILENAME (clean prisms shipped under
NEW names); a no-op str.replace retarget silently kept the old meshes for one
build round -- verify the printed step names, not the edit.
