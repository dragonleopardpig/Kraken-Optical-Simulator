# 0192 — BUG: the folded RA-mirror rays kink on the WRONG diagonal (a "\" in mid-air) instead of reflecting off the real drawn "/" hypotenuse — the actual "reflection wrong at hypotenuse", re-flagged AFTER 0191 went live

**Status: RESOLVED (display-side re-fold, scoped to a SINGLE promoted-mirror fold, so unfolded /
plain / penta / beam-splitter / multi-fold layouts stay byte-identical). The optical trace is
UNTOUCHED — rays still reach the sensor exactly as 0187 made them.**

Bugs 0188–0191 chased "reflection wrong at hypotenuse" through four folded-scoped *display* actors —
the unfolded detector target (0188), the reference-ray stubs + the +Z global guide (0189), the
reflected traced "Optical Axis 2" (0190), then the retroreflected marginal-ray dive (0191). The user
re-flagged the SAME visual once more — `attachment/recorded_bug_repros/flag_20260701_120015_636/`,
captured 12:00, AFTER the 0191 commit was live — with description **"reflection still wrong at
hypotenuse."** and the decisive minimal-repro clarification:

> "refer latest flag, I started with a plain Object + Image, then just add a RA mirror, promoted."

So the artifact reproduces with the MINIMAL setup — Object + Image + one promoted right-angle mirror,
a SINGLE fold — which proves it is **general to the folded machinery, not AZ85/surrogate-specific**.
Every prior bug removed a stray guide/tail; this one is the imaging cone itself reflecting on the
wrong plane.

## Root cause — a proper ROTATION where physics needs an improper REFLECTION

`bugs/0187` represents the promoted full-mirror cube as a **sequential `Mirror`** so the running
coordinate frame folds and the imaging cone reaches the sensor. KrakenOS folds that frame with
`Prerequisites3D.GeometricRotatAndTran` (`Prerequisites3D.py:109`), which applies
`rotate_x(tx)·rotate_y(ty)·rotate_z(-tz)` with `AxisMove == 2` — i.e. a **proper rotation**
(det = +1). A physical mirror is an **improper reflection** (det = −1). The two transforms:

- **agree** on the chief outgoing direction `d_out = reflect(d_in, n)` and on the sagittal axis
  `s = d_in × d_out` (a rotation about `s` by the fold angle carries `d_in → d_out`, same as the
  reflection);
- **differ** by exactly the meridional flip — a reflection across the plane the two directions span.

Result on the AZ85 fold (mirror face through world `C = (0, 0, 71.897)`, so the real drawn hypotenuse
is the plane **Z = 71.897 + X**, the "/"): every off-axis display ray kinked on the mirror image of
that plane, **Z = 71.897 − X**, the "\", which for the +X-folding scene sits **in mid-air off the
drawn cube**. Measured on the live bundle the kink vertices sat up to **12.28 mm** off the real face
— visually, the rays bend before/behind the glass instead of on its diagonal. That is the persistent
"reflection wrong at the hypotenuse".

**Why the earlier fixes could never catch it:** 0188–0191 each removed a *guide/tail* actor; none
touched where the *imaging cone* kinks. And the 0191 guard exercises the RAW non-seq trace via
`_build_scene_bundle` directly, a DIFFERENT code path from the live preview — so 0191 is a proven
**no-op on the live bundle** (its guard legitimately stays green, testing a path this bug never hit).
0191 is not reverted: it is harmless and now documented as a misdiagnosis of THIS live symptom.

## The correction (exact, display-only)

For a single mirror fold the rotation-folded downstream equals the reflection-folded downstream
**reflected across the world plane spanned by `{d_out, s}`**, whose unit normal is

```
s     = d_in × d_out            (sagittal axis, fixed by both transforms)
m_hat = normalize(d_out × s)    (flip-plane normal)
```

Re-fold each display ray (leaving the incoming leg untouched):

1. find the **mirror kink** — the vertex at the sharpest turn, `cos θ < 0.2` (a genuine ~90° fold,
   never a gentle refraction);
2. intersect the **incoming leg** with the REAL face plane `P` (through mirror centre `C`, normal =
   the mesh Mirror-face normal `n`) to get the true hypotenuse hit `K` — this re-anchors the kink
   onto the drawn "/";
3. replace every post-kink vertex `v` with `reflect(v, m_hat) + τ`, where `τ = K − reflect(kink, m_hat)`
   snaps the reflected tail back onto `K`.

This is EXACT for tilted and converging rays (the flip is a rigid reflection; `τ` is a pure
translation). It rewrites `RayPath3D.points_world` in place, so both the 3-D actors and the 2-D
projection follow. **The optical `trace_system` is never re-run** — the rays still terminate on the
sensor exactly as 0187 delivered them; only the drawn polyline geometry between the mirror and the
sensor is re-seated onto the physical reflection.

`promoted_mirror_world_center(specs, row_index)` supplies `C` = cumulative axial thickness of the
rows before the mirror + the mirror's own `desp_z`, plus its `desp_x/desp_y` decenter (AZ85 →
`(0, 0, 71.897)`). `chief_in` is captured per fold record at fold-build time
(`_chief_exit_direction` of the rows up to the mirror, fallback `+Z`).

## Fix (two source files, folded-single-fold-scoped)

`KrakenOS/UI/services/folded_sequential_fold.py` (pure, display-free):

- `_unit`, `promoted_mirror_world_center`, `mirror_reflection_flip_plane_normal(chief_in, face_normal)`
  (returns `m_hat`, or `None` when incoming ∥ outgoing = no fold), `_line_plane_intersection`, and the
  core `correct_folded_mirror_ray_points(points, fold_center, face_normal, chief_in, *, cos_fold_max=0.2)`
  implementing the three steps above (returns a new array, input shape/extra columns preserved, or
  `None` for a ray with no clear ~90° kink);
- `fold_promoted_mirror_specs_to_sequential` now records `chief_in` on each fold record.

`KrakenOS/UI/services/three_d_scene_tools.py` (wiring):

- new mixin method `_apply_folded_mirror_reflection_correction(scene_bundle)` — rebuilds the fold
  records, returns early unless **exactly one** promoted-mirror fold exists (covers the flagged scene
  AND the minimal Object+Image+RA-mirror repro; a fold *chain* keeps the current display because each
  later flip plane lives in the already folded frame — not flagged), then rewrites each ray via the
  free function and tags it `display_geometry_source = "folded_mirror_reflection_corrected"`.
- called in `_build_preview_system_rays_bundle` right after `_build_scene_bundle(system, rays, …)`,
  only in the folded branch (`folded_trace_rows is not None`).

AZ85 result: **279 folded rays with a mirror kink — max kink residual on the real "/" face
12.280 mm → 2.35e-14 mm**; all 279 tagged; incoming legs untouched. Unfolded / plain / penta /
beam-splitter scenes never enter the folded branch → byte-identical.

## Guard

`KrakenOS/UI/validate_open3d_ra_mirror_hypotenuse_reflection.py` (standalone, NOT penta) — binds the
REAL free function (unit) and the REAL wired method (to the live editor via
`_build_preview_system_rays_bundle`):

1. a synthetic rotation-folded ray re-folds onto the "/" face — kink and downstream move from
   `Z = 71.9 − X` to `Z = 71.9 + X`, incoming vertices untouched;
2. straight-forward and degenerate/short polylines are left untouched (`None`); the flip-plane
   normal is ±Z for the AZ85 geometry;
3. INTEGRATION on the real AZ85 bundle: off-axis kinks lie OFF the "/" face (max > 1 mm) BEFORE and
   ON it (< 1e-6 mm) AFTER — via BOTH the free function and the wired `_apply_…` method (the latter
   exercised by shadowing the method to a no-op for the BEFORE capture, then restoring it);
4. scope: 1 fold record for AZ85, 0 for `flat_mirror_45_deg.py` (a native sequential mirror → the
   correction is inert; unfolded scenes stay byte-identical).

Sibling AZ85 ray-display guards (0187 `folded_sequential_trace`, 0188 `detector_coverage_folds`,
0189 `faint_line_folds`, 0190 `reflected_axis_backward_extension`, 0191
`retroreflected_ray_dive`, `launch_is_cone`, `folded_mirror_projection_parity`) all stay PASS —
confirming the re-fold leaves the sensor trace and the sibling overlays byte-identical.

## In-app eyeball owed

The rays are a VTK-only 3-D overlay (headless VTK render of this scene is segfault-prone). The
geometry is proven display-free: all 279 folded rays now kink exactly on the drawn "/" hypotenuse
(residual ~1e-14 mm) and fold +X to the sensor (an X-Z snapshot confirms the kinks land on the red
"/" face, not the mid-air "\"). The user should
fully quit + relaunch, build the minimal Object + Image + promoted RA-mirror scene (and the AZ85
scene), confirm the imaging cone now reflects ON the drawn diagonal — not in mid-air behind/before
the glass — and re-flag if not. The separate "FOV ~1.19× / magnification" observation is a
different, deferred issue and is not addressed here.
