# 0684 — remodel the prism stations per their REAL components (user, 2026-09-01)

## User
"1) Outer Prism is Right Angle Mirror. I see there is another Right Angle glass
below it, which is wrong. 2) Lower Prism is a Cube Beam Splitter. I see there is a
gap in the two pieces of Right Angle Glass, which is wrong, they should be attached
to form a Cube Beam Splitter. 3) Center Prism is a Right Angle Mirror. I see there
is another Right Angle glass below it, which is wrong."
Plus: "You may get the original vendor supplier STEP at attachment/Prism_Assembly"
(OPT-ILS8275: the module is a coaxial LINE ILLUMINATOR -- the two barrels are LED
injection arms, hence the BS at device level).

## CAD truth (om05a_26_1_r03_2s_lr_asm.stp, armA map scene = Rz180 + T)
- Device-level station ("Lower") = the 75x10.5x10.5 CUBE-BS bar per side; the CAD
  carries the far-of-cement half as one solid (10/11) WITH its 45-degree cement
  face; the imaging fold is TIR at that plane.
- y 11.65 station ("Outer") = a first-surface RA MIRROR (solid 7/8; the 45-degree
  coated plane + a back plane 0.2-0.3 mm behind -- it is a thin PLATE, not glass
  the beam traverses).
- Centre = ONE V-block (solid 9) carrying BOTH sides' 45-degree mirror flanks
  (the GP-600 drawing's 23x12 45-deg part); split at z=-28.9 into the A/B halves.
The "extra RA glasses" the user saw were my synthesized through-glass wedges drawn
beside the chunk's real bodies; the "gap" was my wedge half vs the CAD half.

## New model per side (bugs/0684_extract_real_optics.py + 0684_rebuild_scene.py)
- "BS cube A/B": the NEAR half (synthesized from the cube bbox, cut 0.02 mm shy of
  the CAD cement plane; watertight 8-tri wedge) -- glass BK7, the cement plane
  flagged Mirror/Interaction (TIR fold). Plus "BS cube X (far half)": the CAD far
  half as plain glass so the cube reads ATTACHED -- marked
  `StepOverlayPromotion.beam_splitter` (0397/0398) so the frame walk skips it.
- "Outer RA mirror A/B": a clean 3 mm slab whose front face IS the CAD coated
  plane (the CAD body meshes NON-watertight -> traced inert; 0675 clean-mirror
  pattern).
- "Centre RA mirror A/B": the CAD V-block halves (watertight), coated flank
  flagged Mirror/Interaction. First-surface: no glass traversal at either mirror.

## Debugging landmines (each cost a cycle)
1. OCC SetMirror-composed transforms invert solid orientation -> the mesh traces
   INSIDE-OUT (no entry refraction, Mirror pass-through). diag(-1,-1,1) IS a proper
   rotation: build it as SetRotation(Z, pi).
2. A row swap must carry `advanced["Solid_3d_stl"]` (+SourcePath/Format) -- copying
   only OpticalSolidFaces leaves the row tracing as a PLAIN SURFACE (station-plane
   crossings, no glass).
3. The mirror plate carries TWO nearly-equal-area 45-degree faces 0.2 mm apart --
   an area-based hyp pick is a coin flip onto the BACK face (through-glass Fresnel
   splitter, 3249 paths). Pick the 45-degree face whose PLANE passes closest to the
   station's beam fold point.
4. The CAD mirror bodies mesh non-watertight -> the glass-volume logic fails and
   the solid is INERT (rays cross every face event-recorded, zero physics).
5. An un-marked far half's biggest face is the 45-degree cement plane -> the walk
   picks it as an INFERRED output, reads it as a FOLDING exit, and drags the Image
   onto the cube (chain 0 reach). The beam_splitter mark (2080 skip) is the
   designed escape.

## Result (attachment/om05a_folded.py)
- Chain: 1083 paths / 924 reach (85%) -- vs 68/243 with the through-glass wedges.
  Strip z -19.3..-17.3 on y=-11.
- faceB: 361 paths / 4 reach (the lens-seat asymmetry still limits arm B).
- Delivered field band re-measured: y -4..+3 at ~90% reach (was -5..+1 at ~55%);
  authored `object_fov_bands` + guard A8 updated. A secondary +5..+9 window is a
  direct-to-outer-mirror bypass that the (untraced) mount hardware shadows in the
  real machine -- excluded from the authored band, noted for future mount solids.
- Removing the two spurious glass traversals also moves the conjugates toward the
  50 mm part spacing (the 57.8-vs-50 discrepancy) -- final WD/part-face refit rides
  with the vendor-true lens seat follow-up.

## Guards
0672 validator re-pinned: A1 ten solids, A3 the renamed B stations, A3b the
beam_splitter marks, A8 the new band, B-checks re-measured (phase 505).
