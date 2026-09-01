# 0687 — flag_20260901_201645: six-part correction on the remodelled scene

## User report -> root causes -> fixes

1. "The ray is not launching from the object plane."
   The world was still anchored on the OLD conjugate (launch z=0 at the BS face)
   while the centred part's faces sat at -3.9/-53.9. FIX: re-anchored the world on
   the PART -- every free-placed solid shifted +3.9 in z, so face A IS the object
   plane z=0, face B = -50, symmetry plane -25. Part axis_offset back to 0. The
   chunk DECORATION (absolutely placed) shifted with it (placement_offset_z
   -106.79 -> -102.89).

2. "The second mirror seems to reflect from second surface."
   CONFIRMED by the chief polyline: at the outer mirror the beam refracted through
   the front 45-degree plane (y+z=15.41), crossed the 3 mm slab, TIR'd at the BACK
   plane (19.65) and exited displaced -- the slab's front Mirror face never armed.
   FIX: all four fold mirrors rebuilt as clean extruded-triangle RA prisms (the
   proven 0675 recipe -- RA mirrors 1/2 in this scene arm first-surface) with the
   hypotenuse ON the CAD coated plane. Chief now folds in a single clean event;
   chain reach 924 -> 959/1083; the down-leg returns to the CAD axis.

3. "The red ray defocus at the sensor."
   Was dominated by the second-surface lateral displacement. Post-fix the +26.8
   field measures 533 um vs ~77 um for the others -- REAL edge vignetting at the
   40 mm mirror 2 (285 vs 337 rays reach): the field lands 14.7 mm off the mirror
   centre, its cone clips the +x edge. Physical; the vendor-true lens seat arc owns
   any residual.

4. "The other half of prism only launching one point of ray missing the other two."
   TWO stacked bugs: (a) the mirrored-launch bound reused radius_x=25, and the
   edge-field bundles' PUPIL SPREAD around x=+-26.8 exceeded it -- whole bundles
   dropped, leaving one launch point; (b) widening radius to 1000 as a workaround
   drew a 1000 mm SOURCE GLYPH (the giant yellow tube). FIX: dedicated
   `mirror_bound_x/y` spec keys filter mirrored launch points (absent = unbounded);
   radius_x/y stay glyph-sized (27.5 x 5). `mirror_bound_y: 8` keeps the y=0 field
   row (3 launch points, symmetric with arm A) and drops the unphysical +-26.8-row
   mirrored bundles. faceB: 1083 rays from 3 points, 20 reach (was 361/4).

5+6. "Green translucent object plane ... calculate the FOV for one side ...
   another symmetrical plane on the other side ... full FOV on the sensor."
   The calculated one-side FOV: width = sensor 23.04 / m = 55.0 mm; height = the
   geometric acceptance = outer-window (+-5.25 about the face) INTERSECT the
   centre-flank window (fold parity maps its column span one-sided, (-8.9, +3.1))
   = y -5.25..+3.1 = 8.35 mm -- and the MEASURED band (-4..+3 at >=90% reach)
   agrees. Both PART faces (z=0 and z=-50) now carry this band. On the sensor:
   each face images a 23.04 x 3.50 mm strip (8.35 x m); the two half-FOVs combine
   to ~23.04 x 7.0 mm of active image, strips side by side. (A dedicated split-FOV
   HUD readout remains a follow-up.)

## Guard
0672 validator fully re-pinned (part-anchored poses, clean-prism centres, bands,
full-grid mirrored launch, strip windows A z -17.5..-13.5 / B z -9.4..-5.4):
15/15 PASS. Scene: load 17 s, trace ~38 s, chain 1083/959.
