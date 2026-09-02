# 0695 — vendor-true prism rebuild (WIP: commit-and-continue on M90aPro)

## User architecture (flag series 2026-09-02 + clarification)
Per side, from the Object Plane: (1) FIRST RA MIRROR only (the extra right-angle
block was spurious); (2) CUBE BEAM SPLITTER (two RA glass halves; LED lies FLAT
under it shining up: LED -> BS transmit -> RA mirror -> object; return -> RA
mirror -> BS bends 90° toward the centre); (3) CENTRE RA MIRROR (was distorted).
The 0684 model had (1) and (2) SWAPPED (BS at the window) and the centre prism
~2x too tall — the 0694 two-focal-plane root cause.

## Vendor truth (OPT-ILS8275-X STEP z=0 section; bugs/0695_vendor_section.png)
- first RA mirror: thin FIRST-SURFACE plate on the 45° plane (modeled as a
  9.8 x 9.9 x 60 prism, glass BEHIND the plane so no glass in either leg)
- cube BS near half: 13.5-leg triangle bar, coated hyp (25.5,7.0)-(39.0,20.5);
  far half synthesized with a 0.1 mm cement gap (EXACTLY coplanar meshes
  coin-flip ray interactions -> mixed path classes, 0.8-1.3 mm waists)
- centre prism: apex-down V, corners (±11.892, 18.192), apex (0, 6.30); two
  back-to-back halves with a 0.1 mm slot at the split line
- LED panels: 18.1 x 1.6 x 75 flat under each tower (user zoom flag 151208)
- device beam height y_d = 26.02 (calibrated to the proven face-A fold 8.78)
Scene map (side A): scene_z = vendor_x - 25; scene_y = 0.25 + (26.02 - vendor_y);
side B mirrors across z = -25. Builder: bugs/0695_build_vendor_prisms.py
(meshes MUST be local-centred about bbox; absolute-world meshes displace all
faces: 0/3249 with the 0684 'wrong fold face = Fresnel splitter' signature).

## Pipeline order (each geometry change invalidates the next stage)
geometry (apply/remesh) -> SEAT (bugs/0689, KRAKEN_0690_AIM_Y=0.0) ->
REFOCUS (bugs/0695_refocus.py) -> census (bugs/0694_focus_census.py).
- The seat desp goes stale on ANY front-end change (walk frame moves).
- LANDMINE FOUND: changing mirror2 row THICKNESS shifts every later row's
  station and silently DRAGS all after-mirror2 free-placed solids off their
  world poses (this is exactly how the 0691 refocus created the 1.46 mm B-arm
  asymmetry 0694 measured). 0695_refocus now re-bakes every
  StepOverlayPromotion.center_world row after any thickness change.
- The refocus MEASURES the light (x < -250 final-leg filter, wide scan); its
  first version anchored on the sensor row and chased strays.

## Measured state at this commit (scene = bugs/om05a_folded_0695_wip.py)
- Arm A: PERFECT. 3/3 cones waist 1.4-1.9 um EXACTLY on the plane (sensor y
  -1.205), landings on-die x -284.2..-261.1, strip z -28.9, ~795 reach.
- Arm B: present + sharp per cone (2.2-6.6 um) but ALL cones 19.2 mm behind
  the plane. Geometric paths measured EQUAL to 4 um (301.15 both arms) — the
  defect is the LAUNCH: the mirrored faceB instrument reflects
  `_last_imaging_launch_bundles`, which across sync/async/headless topologies
  holds a NON-final launch (measured: B cone 1.155° unaimed vs A 2.902° with
  the -y aim tilt; the stash held a 3249-ray merged aggregate post-build).
  stash_launch gating added (isolated-illumination + analysis probes no longer
  clobber; the 0319 mixin wrapper threading done) but insufficient. An explicit
  same-build rebuild was tried and REVERTED (grid builder = unaimed 31-ray
  disk; world-mode builders outside the sampler context killed the B arm).
  => bugs/0696: give faceB a FIRST-CLASS launcher aimed through the B train.

## Remaining (continue on M90aPro)
1. Strips restamp: bugs/0692_sensor_reach_sweep.py (patched for the live
   sensor plane) -> stamp via bugs/0692_stamp_strips.py with NEW numbers ->
   re-pin guard A8b (still pins the old strips).
2. Guard: A1/A3/B1/B2/B5 re-pinned this commit (12 solids, new B_TRAIN names,
   live sensor_y) — RUN IT; A8b will fail until step 1.
3. Render with the user's layout (bugs/0692_snap_verify.py pattern) + eyeball.
4. Doc finalization + penta phases 505/508/509 smoke + full re-cut later.
5. bugs/0696 faceB launcher rework (the 19.2 mm B focus).
6. Backlog: whole-station rotate verb; env-gated KRAKEN_0695_STASH_DEBUG prints
   remain in trace_preview.py (harmless, useful for 0696).
