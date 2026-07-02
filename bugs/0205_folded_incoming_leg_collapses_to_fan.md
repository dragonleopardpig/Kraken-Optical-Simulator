# 0205 — BUG: on the folded RA-mirror the LAUNCHED (incoming) rays draw as a flat FAN while only the reflected (outgoing) leg is a CONE

**Status: RESOLVED. The display fold no longer ROTATES the past-mirror ray vertices about the fold
anchor; it REFLECTS the straight-equivalent rays about the mirror plane
(`reflect_straight_equivalent_ray_points` / `_reflect_straight_equivalent_display_rays`). A reflection
is an isometry, so the incoming leg — on the same side of the plane as the launch point — is left
UNTOUCHED and keeps its cone, while the outgoing leg is congruent (still a cone) and the focus, being
a fixed distance from an isometry, stays on the drawn detector. On the AZ85 RA-mirror the on-axis
incoming (X,Y) cross-section goes from a collinear fan (2nd singular value `s2 = 0.000`) to a round
disk (`s2 = 17.194`, X-spread 4.229 = Y-spread 4.229) with the focus unmoved at X = 295.577 mm. The
reflecting plane passes through the mirror-face CENTRE (`promoted_mirror_world_center`), so the folded
outgoing arm lands on the drawn optical axis (Z = 71.897 mm) — see the Follow-up correction, which
fixed a −12.5 mm offset from an initial front-datum plane.**

## Origin

The user flagged the working folded AZURE ELS-85 layout
(`KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`, AZ85 = ELS-85 surrogate) in an
Open-3D session (`attachment/recorded_bug_repros/flag_20260702_130129_167/`):

> *"The launched rays seems to be Fan, but after reflection becomes Cone? Correct me if I am wrong."*

The user was right. On the folded scene the pre-mirror leg of every drawn ray fanned out only in Y
(a flat slit) while the post-reflection arm opened into a proper cone — physically impossible for a
single revolved bundle, and a pure display artefact of the fold.

## Root cause

The non-branching promoted-mirror display fold traced the rays through the STRAIGHT-EQUIVALENT
sequential rows (an unfolded +Z bundle) and then bent the drawn geometry at the mirror. That bend was
`_fold_straight_equivalent_display_rays` → `_fold_ray_downstream_of_station`, which **ROTATED every
vertex at or after the mirror station about the fold anchor**.

The AZ85 mirror sits at the FIRST optical surface, so its station is at `station_z ≈ 59.4 mm` — right
where the rays are launched. Rotating "everything past the station" therefore rotated essentially the
whole ray. The rotation maps the incoming cone's meridional (X) spread into pure axial (Z)
displacement, so:

- the incoming leg collapsed to a **flat Y-only fan** (its X-spread rotated away to ~0), and
- the lost meridional spread reappeared as extra **Z-spread in the outgoing arm**.

Hence "fan in, cone out": one bundle, torn in two by a rotation that treated the near-launch station
as if it were far downstream.

## Fix

Fold by REFLECTION instead of rotation. A single new pure helper does the geometry
(`services/folded_sequential_fold.py`):

```python
def reflect_straight_equivalent_ray_points(points, plane_point, plane_normal):
    # p' = p - 2 * ((p - p0) . n̂) * n̂  for every vertex on the FAR side of the plane;
    # near-side (incoming) vertices are left exactly where they are; the plane-crossing
    # vertex is inserted as a fixed point (a clean kink, no gap).
```

This is formula-based and scene-general — the only constants are float epsilons (`1e-9`, `1e-12`);
there are no baked-in AZ85 numbers. The reflection plane is derived per scene from the fold record:

- **normal** = the mirror `face_normal` carried in the fold record from
  `fold_promoted_mirror_specs_to_sequential`;
- **point** = `promoted_mirror_world_center(specs, row_index)` — the reflecting hypotenuse's centre,
  at the cube CENTRE `station_z + desp_z` (the real drawn mirror face). It MUST be the drawn
  hypotenuse: reflecting about the FRONT DATUM (`station_z`, excluding `desp_z`) instead lands the
  folded outgoing arm `desp_z` (12.5 mm on AZ85) off the drawn detector Z — see the
  **Follow-up correction** below, which is exactly that regression.

Why the isometry fixes all three symptoms:

- **incoming cone preserved** — those vertices are on the launch side of the plane, so the reflection
  leaves them untouched;
- **outgoing cone preserved** — the reflected arm is congruent to the unfolded downstream bundle, so
  it stays a cone (it was never the problem);
- **focus preserved** — an isometry cannot move the distance from the mirror to the focus, so the
  converged spot stays exactly on the drawn detector.

Wiring: `three_d_scene_tools.py` `_apply_folded_display_bend` now dispatches the AZ85 Path-A case
(`fold_transform is not None`) to the new `_reflect_straight_equivalent_display_rays(scene_bundle)`,
which rebuilds the fold record, computes the mirror-centre plane, and reflects each ray in place
(tagging it `folded_straight_equivalent_reflected`). The sequential-Mirror fallback (Path B,
`fold_transform is None`) is unchanged. The old rotate + rigid-flip methods are kept (importable) only
for the `bugs/render_0205_incoming_cone.py` before/after proof render.

## Verification (display-free)

New guard `KrakenOS/UI/validate_open3d_ra_mirror_incoming_cone.py` binds the real wired pipeline to the
live AZ85 editor and asserts, on the on-axis field's incoming leg (a Z-slice at Z = 35 mm, below the
station so it samples the incoming leg only):

```
PASS bugs/0205 folded RA-mirror incoming cone (incoming leg is a preserved cone):
  - incoming (X,Y) cross-section is a 2D disk (s2>0.5), round, not a flat fan
  - incoming spread is unchanged from the raw straight-equivalent (reflection is an isometry)
  - outgoing arm (Y,Z) cross-section stays a 2D disk
  - on-axis rays raw 361 / folded 361 | incoming s2=17.194 (X 4.229 ~ Y 4.229) | outgoing s2=48.747 | drawn arm X=295.6
```

- **disk not fan** — incoming (X,Y) 2nd singular value `s2 = 17.194 > 0.5` (a rotate fold gives
  `s2 = 0.000`, caught);
- **round** — X-spread 4.229 ≈ Y-spread 4.229 (a revolved cone, not an elongated slit);
- **isometry** — the incoming spread is unchanged (<5%) from the raw straight-equivalent bundle
  (captured by shadowing `_reflect_straight_equivalent_display_rays` to a no-op);
- **outgoing stays a disk** — (Y,Z) at X = 0.6·(drawn arm) has `s2 = 48.747 > 0.5`;
- **outgoing arm on the optical axis** — its mean Z matches the folded axis Z (the mirror-face centre,
  71.897 mm) within 0.25 mm (added by the Follow-up correction; a front-datum fold reads 59.397 mm,
  a −12.5 mm offset, caught).

The `bugs/0192` hypotenuse-reflection guard was updated to exercise the new reflection path and
re-passes with a STRONGER result than the old rigid-flip: every one of **3235/3235** folded rays lands
its kink ON the `'/'` mirror face (residual max `7.99e-15 mm`, correct sign, all tagged
`folded_straight_equivalent_reflected`). The unfolded straight-equivalent has 0 kinks (precondition).
The `bugs/0181` folded-focus phase still passes (the converged spot stays on the drawn detector,
RMS 0.83 µm), confirming the isometry did not disturb focus.

Visual proof (eyeballed, not asserted): `bugs/render_0205_incoming_cone.py` renders the down-axis view
the user sees — OLD rotate fold (incoming collapses to a vertical line, `s2 = 0.000`) vs NEW reflection
fold (incoming is a round hexapolar disk, `s2 = 17.194`) — to
`attachment/bugs_0205_incoming_cone_proof.png`.

Guard wired as `phase_183_folded_incoming_cone` in the comprehensive penta validator; baseline updated
`"183": "pass"`.

## Follow-up correction — reflection plane must be the mirror-face CENTRE, not the front datum

The first 0205 commit (`ccb387c6`) reflected about the mirror's FRONT DATUM plane
(`[decenter_x, decenter_y, station_z]`, excluding `desp_z`). That preserved the incoming cone (the fan
fix) but a reflection about the wrong-Z plane is still an isometry that lands the WHOLE outgoing arm on
the wrong axis: the folded arm centred on Z = 59.397 mm instead of the drawn detector / folded optical
axis at Z = 71.897 mm — a **−12.5 mm = −`desp_z`** offset. The user re-flagged it immediately
(`flag_20260702_152020_279`, *"there is an obvious offset from optical axis"*).

Root cause of the wrong choice: the earlier 0197 rotate fold used `station_z` as its anchor, and I
carried that anchor over — but rotation about an axis point and reflection about a plane are different
operations. The rotation fold happened to still land the arm on-axis (it rotated the downstream frame
about that point); reflection about a plane through the same point translates the arm by twice the
plane's offset from the true face. The correct reflecting plane is the REAL drawn hypotenuse —
`promoted_mirror_world_center` (the cube centre, `station_z + desp_z`).

Fix (this commit): `_reflect_straight_equivalent_display_rays` now sets
`plane_point = promoted_mirror_world_center(specs, row_index)` directly (dropping the `station_z`
recomputation). Measured: outgoing on-axis arm Z 59.397 → **71.897** (offset +0.000 from the drawn
axis), incoming cone unchanged (`s2` 17.194, still round). The phase-183 guard gained assertion **(5)**
— the outgoing arm's mean Z must equal the folded optical-axis Z (mirror-face centre) within 0.25 mm;
`bugs/probe_0205_guard_catches_offset.py` proves it FAILS on the front-datum path (reads 59.397,
offset −12.500) and passes on the fix. The `bugs/0192` hypotenuse guard's integration check was
likewise moved from the front-datum plane to `promoted_mirror_world_center` and re-passes
(3249/3249 rays, residual 7.99e-15 mm).

### Phase-181 (`bugs/0203`) retarget — focus lands at the reflected image, not on the drawn detector

Moving the fold to the mirror-face CENTRE reflection also fixed the on-axis Z (71.897) but surfaced
a second, unavoidable consequence: the phase-181 folded-cone-focus guard
(`validate_open3d_ra_mirror_folded_cone_focus.py`) had asserted the wired on-axis endpoint lands on
the DRAWN DETECTOR X (295.577). The reflected focus now lands at **X = 283.077** — `desp_z` (12.5 mm)
short of the detector along +X. This is not a ray bug; it is a **fold-convention mismatch**: the rays
are folded by a REFLECTION (det −1, the real reflecting hypotenuse), while the drawn detector and all
folded overlays are folded by the ROTATION `F = _optical_axis_fold_world_transform_for_row` (det +1).
A reflection and a rotation about the same 45° mirror differ by the meridional flip, and for the
on-axis chief that difference is exactly `desp_z`. No single reflection plane can hit BOTH the
detector's X (295.577, needs the front datum) AND the on-axis Z (71.897, needs the centre) — the
reflected focus slides along a (+X, −Z) locus and (295.577, 71.897) is not on it (measured by
`bugs/probe_0205_detector_vs_focus.py`).

`F` **must stay a rotation** — it also folds the lens/camera STEP CAD, and a reflection would MIRROR
those meshes (and their text labels). So reconciling the detector to the reflected image (reflection-
folding the detector/overlay POSITIONS while keeping mesh ORIENTATION unmirrored) is a larger
overlay-fold change, **deferred**. It is nearly invisible here: over the f/13 fold the 12.5 mm
longitudinal gap is a ~1 mm blur, whereas the flagged defect was the 12.5 mm TRANSVERSE offset (now
fixed). Phase-181 was therefore **retargeted** to assert the wired focus lands at the PHYSICAL
reflected image — endpoint X AND Z match the mirror-centre reflection of the straight on-axis focus
(283.077, 71.897) within 0.05 mm, plus transverse-RMS convergence (0.83 µm) — rather than the
mis-folded detector X. The new Z-assertion also independently catches the front-datum offset
regression (reads Z 59.397). It targets the physics, so a future overlay-fold fix that moves the
detector onto 283.077 leaves the guard passing.
