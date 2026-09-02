# 0695 — vendor-true prism rebuild (COMPLETE; 0696 faceB launcher owed)

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

## Completion (M90aPro, 2026-09-02 evening)
Sweep on the vendor-true scene (sensor centre (-272.65, -1.2, -26.4)):
- arm A: band y -4..+3 at a uniform 266/361 (74%), ZERO per-field landing
  spread, strip z -30.14..-27.27. The 0694 x-asymmetry is GONE: object
  x = -27.5 AND +27.5 both land razor-sharp just inside the die
  (-283.91 / -261.39 vs die -284.17..-261.13).
- arm B: 269-302/361 (~80%), strip z -23.69..-18.36 (~1.6 mm blur pending
  0696).
Strips restamped + guard A8b re-pinned; FULL GUARD 16/16 PASS (A1 twelve
solids incl. LED panels, new B_TRAIN, live sensor plane, B1 794/794 on-strip,
B2 waist 0.4 um at -1.15, B5 faceB 633).

## Owed
- bugs/0696: first-class faceB launcher (B arm's absolute focus 19.2 mm late;
  the mirrored-launch stash reflects a non-final launch). All measurements in
  this doc's Measured state section.
- Whole-station rotate verb (production Top/Bottom station).
- Penta full baseline re-cut for phases 500-509.
- env-gated KRAKEN_0695_STASH_DEBUG prints remain in trace_preview.py
  (harmless; useful for 0696).
