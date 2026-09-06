# 0719 — the lens move is a THICKNESS PAIR: physical-room gate, no Filter drum, focus residual

Flag `attachment/recorded_bug_repros/flag_20260905_194708_067` on
`attachment/om05a_folded_80mm.py`: a 20 mm device -> the NORMAL FOV solve was **refused**
("the object or image leg would go negative -- slide the fold mirrors first") although the
lens had ~180 mm of leg in front of it, and **Force FOV** then drew a ~150 mm (user) /
171.5 mm (re-run) translucent **tube** under the Filter row.

Follows 0717 (refusal banner + force) and 0718 (force freeze). Standing directives that
shaped the fix: [[feedback_vendor_hardware_immutable]] (only the lens moves; focus
consequences are the user's next step), [[feedback_no_silent_solve_failure]],
[[feedback_display_follows_physics]], [[feedback_general_not_special_case]].

## Root cause 1 -- the tube is the FILTER's core side body, not the barrel

The 0717 force was a desp two-write: `rows[8].desp_z += A` (front datum carries the block
and the tail) and `rows[13].desp_z -= A` (a "cancel" on the row after the rear datum). On
om05a row 13 is the **Filter 48-926 (N-BK7, 1 mm, dia 50.8)** -- a GLASS row.
`Prerequisites3D.py` builds `Side3D(13, 14)` for every glass row without an STL, and the
core applies a surface's OWN decentre only (`PA=1` for its own row, `PA=AxisMove=0` for the
next), so surface 13 was baked at station+|A| while surface 14 stayed put: a raw drum
|A|-1 mm long. The UI then re-posed EEE[13] + the BBB body with ONE rigid delta, landing
ring 13 back on the fixed Filter disc and ring 14 |A| toward the moved lens.

Measured (force, 20 x 1 face, A = -171.966): row-13 actors went 6 -> 8; the new body spans
x 78.654..250.127 (171.47 x 50.8 x 52.5 mm, rings of the Filter's diameter 50.8, not the
lens 23.8); ring 13 fixed at x 249.611..250.127, ring 14 moved 250.611 -> 78.654. The lens
STEP overlay itself moved rigidly (x 185.66..233.01 -> 13.70..61.05, offset (0,0,0)) --
it was never the tube. **Any desp cancel on a glass row elongates that row's drum.**

## Root cause 2 -- the normal solve never read the lens leg's room

`_apply_conjugate_pair` called `slide_lens_block_along_its_leg(object_delta)`, which
returns **None silently** when `_lens_leg_slide_plan()` reports `folded=False`: the axis
tree snaps rows by their RAW prescription pose, so rows 8-12 (stations 275-319, desp ~0)
land on `axis:root` although the follower walk physically places them on RA mirror 1's
+X leg (measured plan `([8..12], (0,0,1), False)`). With the refusal channel EMPTY, the
0573 recruitment and the honest-refusal return were both skipped and the object delta
fell to `_distribute_folded_gap_delta(rows, 0, -171.966, spill=1)`: the Object row
(5.35 mm) and its spill row 1 ('First RA mirror A', a VENDOR solid) cannot absorb it ->
None -> the ":1668" refusal. Row 7's 180.47 mm leg was never consulted.

A second, measured correction: the STATION room (180.47 mm) **overstates** the physical
room. After the 172 mm force the lens body (x 13.70..61.05) overlapped RA mirror 1's actor
(x -25.16..25.0) by 11.3 mm while the banner said "8.504 mm clearance" -- the station gap
ignores the mirror body's half-extent (~25 mm) and the barrel's overhang past its datum
(~3 mm).

## The fix -- ONE primitive `translate_lens_block_along_leg(d, *, force=False)`

`ScenePlacementMixin.translate_lens_block_along_leg` (scene_placement_commands.py), `d` =
the folded conjugate's `object_delta` (NEGATIVE = toward the object / shorter WD).

* **Dispatch.** `_lens_leg_slide_plan()[2] is True` (a 0433-frozen desp-leg scene: AZ85 /
  PYRITE) -> the existing tested `slide_lens_block_along_its_leg` unchanged (force
  bypasses only its room refusal). Otherwise (om05a-class live follower walk, root-axis
  block) -> the **thickness pair** on the gaps bracketing `_imaging_lens_block_indices()`:

      rows[front-1].thickness += d     # row 7 'RA mirror 1' LEG gap: 180.47 -> 180.47 + d
      rows[rear].thickness    -= d     # row 12 rear datum gap:      17.93 -> 17.93 - d

  The fold source frame advances by `thickness`, each follower by its own, so rows
  front..rear translate rigidly by d along the leg; every station >= rear+1 (Filter, RA
  mirror 2, camera, every free-placed vendor row pinned at station+desp) is byte-identical;
  the core leaves Side3D(13,14) at 1 mm; the lens STEP body follows through its datum pin +
  fold anchor. **No decentre write on any row, no cancel row, no placement-offset write.**
  Writing row 7's thickness is the LEG, not the mirror: its pose (station + own desp/tilt)
  is invariant (asserted by the smoke test: row 7 desp/tilt and actor bounds identical).

* **Room (the gate)** `_lens_block_physical_room_mm(front, rear, sign, *, leg_unit=None)`:
  along-leg separation of the lens STEP AABB (memoised
  `_transformed_imported_step_mesh_for_label('lens')`) and the obstacle's world AABB
  (`_solid_row_world_aabb`: the cached STL's corners posed like the follower walk pins a
  free-placed solid; promotion-metadata bounds only when the STL cannot be read), projected
  on the leg unit via `_aabb_corner_projection_range`, minus `_SWAP_REFOCUS_MIN_CLEARANCE_MM`
  (2.0). The leg unit is the caller's (the frozen slide plan's direction) when supplied, else
  `R[:,2]` of `_optical_axis_fold_world_transform_for_row(front)`, else +Z. The obstacle is
  chosen by GEOMETRY: among the solids in the travel direction whose AABB overlaps the lens
  body in both transverse directions and is not already beyond it, the smallest along-leg
  separation wins (the coaxial bars project closer than RA mirror 1 on om05a but never
  overlap the barrel transversely). Fallback without a lens mesh: the row-order nearest
  solid, station gap - 0.5*diameter - 2.0. The station gap is the HARD CAP. No system
  rebuild (the 0717 `_surface_origin_for_rows` loop was ~50 s a call).
  om05a measured: leg unit (0.9999, 0, -0.0102); lens span 185.668..233.526; RA mirror 1
  span -24.999..25.506 -> **room_phys 158.16 mm** (station 180.47).

* **Normal** (`force=False`): `|d| <= room_phys` -> apply, return
  `{mode:'thickness_pair', distance, room_mm, clearance_mm, obstacle, rows:[front-1, rear],
  capped:False}`; else NOTHING written, `_lens_move_refusal` (names the obstacle, both rooms,
  the shortfall) + `_lens_move_room_mm` (physical) -> the caller banners it.
  For `d > 0` the downstream solid (row 15) is measured the same way and `rows[rear]` caps.

* **Force** (`force=True`): the same pair regardless of the physical room, `|d|` capped at
  `rows[gap].thickness - 1e-3` so no gap ever goes negative (bugs/0564
  `_normalize_special_rows` would zero it and RAID the vendor prism gaps upstream);
  `penetration_mm = room_phys - |moved|` (negative = the barrel is inside the mirror body),
  `capped` + `capped_mm` when clipped. `force_translate_lens_toward_object` is kept as a thin
  wrapper (`return self.translate_lens_block_along_leg(amount, force=True)`).

* **Solve wiring** (`quick_estimation._apply_conjugate_pair`): the object side goes through
  the primitive (first try and the post-0573-recruitment retry); the refusal stash reads
  `_lens_move_refusal` / `_lens_move_room_mm` -> `{lens_move_needed_mm, leg_room_mm, reason}`;
  with a lens block present the object delta is NEVER booked into the object gap.
  The force short-circuit reads the PHYSICAL `penetration_mm`, `capped` ->
  `forced_penetration_mm / forced_room_mm / forced_capped_mm / forced_drawn_mm`; the 0718
  deferred-trace lines stay.

* **Image side after a pair move** -- never move vendor hardware. After the re-measure
  (`image_delta_new = image_delta_old + d`), `_image_write_locked_by_vendor_hardware(rows,
  img_row)` returns why the write may not be booked: a glued camera STEP (the sensor carries
  the vendor body) or a `Solid_3d_stl` row downstream of the gap row (pinned at
  station+desp). Locked, or the distributor returns None -> NO ":1668" refusal after the
  lens moved: the residual track mismatch is stashed in the NEW non-banner field
  `_fov_solve_focus_residual_info` `{image_delta_mm, image_gap_row, lens_move_mm, reason}`,
  reported in the status text ("focus residual: the exact conjugate needs the object/sensor
  track shortened/lengthened by X mm -- device stage / camera focus is your call") and in
  the system HUD (`format_focus_residual_lines`), the traced-focus finisher is skipped (it
  would move the vendor-glued sensor), `ok=True`. `fov_solve` clears the stash at entry and
  gates the real-ray field-fill refinement on it (a defocused sensor plane is not a ruler
  for the WD -- the secant would walk the lens off the requested WD). When the write IS free
  (no camera STEP, no vendor row past the gap) it is applied as before.

* **Banner** (`format_solve_refusal_lines`): "clearance to <obstacle> body"; a
  "FORCED: move capped at the fold mirror station (requested X mm, drawn Y mm)" line.

## Measured (smoke_0719.py, headless xvfb, om05a_folded_80mm)

Before (both cases): lens block 8..12; RA mirror 1 row 7 t=180.47 desp (0, 52.8, -119.93)
tilt (0, 90, 0) station 94.93; row 12 t=17.93; Filter row 13 t=1.0 station 336.52; lens STEP
x 185.656..233.008 (47.35 x 46.04 x 50.04); merged actor x: r7 -25.164..25.0, r8 188.63,
r12 231.82..232.06, r13 249.611..251.126 (max X extent 1.516), r15 252.117..293.085.

**Case A -- the user's device, 20 x 20 x 20 (front face 20 x 20 -> FOV 21 x 21, |m| 1.097).**
Normal solve: **ok=True, `_fov_solve_refusal_info` None** (no banner), 72 s with the 3D view
open (incl. the traced refresh). d = **-150.0349 mm**; rows changed [7, 12] only: row 7
180.47 -> 30.4351, row 12 17.93 -> 167.9649, gap7+gap12 = 198.4 invariant; desp/tilt changed
on NO row; stations 8-12 shift -150.0349, stations 7 and 13+ 0.0. Actors: rows 8-12 x-shift
-150.0272 each (spread 0.0000, dz +1.5232 = the leg's -0.0102 tilt); rows 13-23 deltas all
0.0; all 12 vendor rows' desp/tilt identical and actor bounds identical (row 7's thickness
is the only vendor-row field that changed -- by design). Row 13: 6 actors, max X extent
1.516 mm (**no tube**). Lens STEP x 35.629..82.981, delta (-150.027, 0, +1.524), extent
47.352 x 46.04 x 50.04 unchanged, placement offset (0,0,0). Focus residual stash:
image_delta **+36.10 mm** (the exact conjugate needs the track lengthened by 36.1 mm),
reason "the sensor carries the vendor camera body (glued camera STEP)"; HUD shows the two
residual lines; status: "lens at WD -- moved -150 mm ... focus residual ... Trace Now shows
the true focus. Field verification by real rays deferred". Snapshot smoke_0719_caseA.png:
the four lens discs sit ~8 mm in front of RA mirror 1's prism, the Filter disc unmoved at
RA mirror 2, no drum.

**Case B -- 20 x 20 x 1 (front face 20 x 1 -> FOV 21 x 1.05, |m| 1.5495, d = -171.966).**
Normal solve: **ok=False**, stash `{lens_move_needed_mm: -171.966, leg_room_mm: 158.16
(physical), reason: "... only 158.2 mm of physical room is left before its body reaches RA
mirror 1 (50 mm) (station gap 180.5 mm; short by 13.8 mm) ..."}`; rows changed [] ; every
actor delta 0.0 (nothing moved). Force: ok=True in 9.0 s; rows changed [7, 12]: row 7
180.47 -> **8.5042 (>= 0, not capped: |d| < 180.469)**, row 12 17.93 -> 189.896; stations
8-12 -171.9658, 13+ 0.0; actors rows 8-12 -171.9569 (spread 1e-4), rows 13-23 0.0, vendor
rows 0.0; row 13 max X extent **1.516 (no tube)**; lens STEP x 13.699..61.051 (same extent),
overlapping the mirror actor (x <= 25.0) by 11.3 mm; banner "FORCED: lens PENETRATES RA
mirror 1 (50 mm) by 13.8 mm" (= 158.16 physical room - 171.97, i.e. the 11.3 mm body overlap
+ the 2 mm clearance + ~0.5 mm AABB over-estimate of the 45-degree prism). The 0564
normaliser (`_normalize_special_rows` on a deep copy) does NO thickness work afterwards:
its only diff is `(row 0, desp_z, -15.0 -> 0.0)`, the Object template clearing the
device's axis offset, identical to the as-loaded baseline. Snapshot
smoke_0719_caseB_force.png: the first lens disc sits inside the prism, banner painted.

## Not done here (follow-ups)

* Item [7] of the brief: `translate_step_overlay`'s root-axis redirect (:6233 single gap
  write) still cascades stations >= 13 on a lens DRAG; route it through the primitive so
  "drag = solve" holds on om05a too. Separate commit.
* `_promoted_solid_current_center(7)` returns (-119.93, 105.6, -25.0) on om05a -- the fold
  transform applied to a free-placed pinned solid's desp (true centre (0, 52.8, -25)). The
  new `_solid_row_world_aabb` avoids it; the camera anti-crash consumers of
  `_promoted_solid_world_bounds` inherit the bug on such scenes.
* `solve_fov_to_inspection_face` sets the status text and then `refresh_plot` overwrites it
  with "Plot refreshed | ..." (pre-existing); the returned message and the HUD carry the
  residual.

## Guard

`validate_open3d_0719_lens_move_thickness_pair` = penta phase 518 (display-free; the real
primitive on a stub editor built from the mixins): A the pair (only rows 7/12, stations 8-12
shift, no desp, vendor poses identical), B the physical-room gate (refuse with the numbers,
nothing written), C force (penetration, cap at the leg gap, every gap >= 0), D the frozen
dispatch, E source pins (mover delegates, no desp writes, residual before the ":1668"
refusal, fov_solve gates), F the vendor lock, G the formatters, H the Phase-2 adversarial
judge's must-fixes (the banner shortfall is |need| − room, not the signed need; a refused
FORCE carries the primitive's reason + physical room instead of a fixed text; the frozen-leg
slide branch reports room/obstacle for BOTH move directions; the obstacle AABB poses the STL
corners first and uses promotion metadata only as fallback; a CAD solid parked inside the
lens block refuses the pair rather than being carried, force included; a +X frozen-leg case
proves the room is measured along the PLAN direction, not a +Z fallback; the slide branch
measures BEFORE the composite moves the rows; a forced move that finds no obstacle body still
reads FORCED, never the Force hint). 0717's B3/B4a pins were
rewritten to the new contract (no dead desp code kept green).

## Re-verification round (adversarial judge, must-fixes)

The Phase-2 judge verified the physics but refused to ship until five banner / room defects
were fixed; an independent re-verification then caught a sixth inside must-fix 3. All are in:

1. **Banner shortfall** = |need| − room. The signed form printed "short by −333.5" on the
   om05a refusal while the status text said 13.8 mm.
2. **A refused FORCE carries the primitive's reason + physical room** (a CAD solid parked
   inside the block, an exhausted leg gap, the frozen slide's contiguity/gap refusals). It
   used to return a fixed "no imaging-lens block to drive" with no numbers.
3. **Frozen-leg (slide) branch room** — three defects, all measured on
   `attachment/machine_vision_Pyrite85.py`:
   - *wrong axis*: the helper's leg unit came from the front datum's fold frame, which is
     None on every 0433-frozen / BS-leg scene, so it fell back to +Z while the slide runs
     along +X — a fabricated −41.8 mm room ("PENETRATES by 46.8") where the 0572 leg-room and
     an along-leg AABB projection both give +44.84. Fix: the slide branch passes the plan
     direction as `leg_unit`.
   - *measured after the move*: the room was taken after `slide_lens_block_along_its_leg`
     had shortened the gap, then |move| was subtracted again. Fix: measure first.
   - *obstacle by row order*: a station-neutral BS plate physically UPSTREAM of the lens was
     picked as the "downstream" obstacle. Fix: choose by geometry — transverse overlap in
     both perpendicular directions AND not already beyond the lens, nearest along-leg
     separation wins. (A bare along-leg projection is not enough either: on om05a the
     coaxial bars project closer than RA mirror 1 but sit at y 0–30 under a lens spanning
     y 30–76 — the barrel never touches them.)
4. **Obstacle AABB**: pose the cached STL corners first (matches the RA-mirror-1 actor to
   0.16 mm); promotion-metadata bounds only when the STL cannot be read (their live centre
   was (−119.93, 105.6, −25) against the true (0, 52.8, −25)).
5. **A CAD solid parked inside the lens block refuses the pair**, force included — the pair
   would shift its station (pose = station + desp) = move hardware.
6. **FORCED banner keyed on the move having been applied**, not on a penetration number
   existing: a forced move that finds no obstacle body now prints the move + leg gap instead
   of falling through to the "right-click → Force FOV" hint. The stashed physical room is
   rendered next to the penetration.

Validator section H (H1–H9) pins each of these display-free, including a +X frozen-leg stub
whose room would come out −27 on the +Z fallback and 158.656 along the plan direction.

## Follow-ups recorded by the final adversarial review (not exercised by the om05a / Pyrite85 cases)

- **Candidate enumeration is row-half partitioned** (`rows 0..front-1` toward / `rear+1..end`
  away): a solid physically in the travel direction but in the OTHER row half (a
  station-neutral promoted body appended after the lens block yet parked upstream) is never
  evaluated. Geometry-only enumeration over ALL solid rows is the general fix.
- **`_lens_leg_slide_plan()` is None → the thickness-pair branch** with no proof the block is
  on the root axis (axis-tree exception, datums on different segments — the 0581/0582 shape).
  Should refuse with a reason rather than write a straight-frame pair on a frozen scene.
- **A body straddling the lens's near face** gets a negative separation in both directions
  and wins the min, so the away move that would relieve an existing overlap is refused (Force
  still applies it).
- **Forced-success status text is sign-blind** ("drove the lens X mm toward the object (WD
  shortened)") although the primitive is signed; a forced away-from-object move reads wrong.
- **Lens DRAG** (`translate_step_overlay` root-axis redirect, single gap write) still cascades
  downstream stations; route it through `translate_lens_block_along_leg` ("drag = solve").
- FORCED banner heading still reads "SOLVE REFUSED — the drawn scene does NOT deliver this
  request" on a successful forced solve (0717 wording).
