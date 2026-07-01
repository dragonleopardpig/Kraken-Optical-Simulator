# 0191 — BUG: after 0190 the folded RA-mirror scene STILL shows a "wrong reflection at the hypotenuse" — ~21% of the MARGINAL rays retroreflect at the first ideal Thin Lens, double-pass back, and dive out the 45° hypotenuse as a downward ray fan

**Status: RESOLVED (one source-level fix, scoped to promoted-mirror FOLDED scenes only via the
same fold-override gate 0188/0189 use, so unfolded / plain / penta / beam-splitter layouts stay
byte-identical).**

Bugs 0188–0190 chased the faint "line at the hypotenuse" through THREE display actors — the
unfolded detector target (0188), the blocked reference-ray stubs + the over-extended +Z global
guide (0189), and the reflected traced optical-axis guide "Optical Axis 2" (0190). Each was a
guide/overlay actor. The user re-flagged the SAME visual once more —
`attachment/recorded_bug_repros/flag_20260701_102844_382/`, captured 10:28, AFTER the 0190 commit
(`31cdd467`) was live — with description **"reflection still wrong at hypotenuse."** This time the
residual is NOT a guide overlay: it is the **traced imaging rays themselves**.

## Root cause — measured headlessly on the live AZ85 bundle

Enumerating the DRAWN 3-D ray records (`editor._iter_3d_scene_ray_records`) on the real AZ85 bundle:
**53 of 250 rays (21%) never reach the camera.** They reflect off the mirror to +X, propagate to
the FIRST ideal Thin Lens (row 4, "Blackbox Group 1", world X≈100), then **REVERSE** — the tracer's
own surface events record the propagation flipping ~180° — double-pass back through the lens and the
mirror, and terminate DOWN at Z≈−50, i.e. straight out the back of the 45° hypotenuse. That downward
fan of rays crossing the mirror body is the persistent "reflection wrong at the hypotenuse". The
same lens traced UNFOLDED (`machine_vision_85mm_azure_datasheet_05x_20x.py`) reverses **0** rays —
so this is entirely fold-induced.

**Why (the deeper tracer cause, same family as 0187):** `bugs/0187` already documents that a
mesh-mirror reflection flips the propagation sign and the AZ85 surrogate's IDEAL Thin Lenses (no
real glass — KrakenOS fakes the deflection in `InterNormalCalc` as `P_x2=(L/N)·f`, `P_y2=(M/N)·f`)
then **retroreflect** after that flip. 0187's fix — represent the promoted full-mirror cube as a
sequential `Mirror` so the running frame folds — made the imaging cone (197/250 rays) behave. But
`(L/N)·f` still back-bends a folded OFF-AXIS ray whose local axial cosine `N` has been driven small
by the fold, so the residual 21% MARGINAL rays keep retroreflecting. A full tracer fix (the
"tracer-SIGN across fold, next-level" note) is out of scope for the display branch; this bug removes
the non-physical *display* tail, consistent with how 0189 removed the stranded stub rays.

Measured per-vertex turn cos(θ) across the 250 rays is cleanly **bimodal**: the 53 retroreflections
all fall in `[-1.0, -0.9]`, then a HARD empty gap `[-0.9, -0.6]`, then every legitimate fold /
refraction turn (steepest is the ~90–120° mirror fold for a marginal FIELD ray) at cos ≥ −0.6. So a
single mid-gap threshold isolates the artifact with ~0.15 margin either way.

## Fix (one source-level change, folded-scene-scoped)

`KrakenOS/UI/services/layout_scene_bundle_display.py`:

- new module free function `_folded_retroreflected_tail_points(points, cos_max=-0.75)` — walks a
  display polyline and, at the first vertex whose incoming-vs-outgoing unit-direction dot is below
  `_FOLDED_RETROREFLECTED_TAIL_COS_MAX = -0.75` (a ~180° retroreflection, never a fold/refraction),
  keeps every point up to and INCLUDING that vertex (the ray stops at the lens where it turned
  around) and drops the non-physical tail. Returns `None` (leave untouched) for a forward-only ray
  or a polyline too short / degenerate to judge.
- new mixin method `LayoutSceneBundleDisplayMixin._truncate_folded_retroreflected_ray_tails(bundle)`
  — gated on `scene_is_folded` (the `_optical_axis_fold_world_transform_for_row` override, the exact
  gate 0188's detector fold + 0189's stub drop use), rewrites each `path.points_world` in place with
  the truncated array (the SAME display-time `points_world` mutation `two_arm_display_fold` already
  performs, so both the 2-D projection and the 3-D actors follow). Called in the folded branch of
  the scene-bundle finalizer, right after `_suppress_blocked_reference_ray_stubs(bundle)`.

AZ85 result: dive-through-hypotenuse rays **43 → 0**; 53 rays truncated, 197 forward rays untouched.
Ray 124 (the chief/axis ray, itself a retroreflector) is truncated at the Thin Lens (ends X≈100,
Z=71.9 on the folded axis) — its segment 2→3 (X 40→82.45) is BEFORE the reversal, so 0190's derived
"Optical Axis 2" is unaffected (and the phantom return-leg axis segments 0190 had to clamp are gone).
Unfolded azure-85: 0 truncated, byte-identical.

## Guard

`KrakenOS/UI/validate_open3d_ra_mirror_retroreflected_ray_dive.py` (standalone, NOT penta) — binds
the REAL free function (unit) and the REAL folded gate (to the live editor):

1. a synthetic forward→lens→reversed→dive polyline truncates at the reversal vertex (tail dropped,
   forward prefix + the reversal vertex preserved);
2. a monotonic-forward polyline and a degenerate/short polyline are left untouched (`None`);
3. INTEGRATION: on the real traced AZ85 bundle 43 drawn rays dive through the hypotenuse
   (Z<40 at |X|<20,|Y|<20) BEFORE and **0** AFTER; exactly 53 rays truncate, 197 stay; ray 124 keeps
   its segment 2→3 so Optical Axis 2 survives;
4. the folded gate is not None for AZ85 (truncation runs) and None for `flat_mirror_45_deg.py`
   (gated OFF → unfolded scenes byte-identical).

Sibling AZ85 guards (0185–0190) + `validate_open3d_optical_axis_guides` /
`validate_open3d_beam_splitter_transmit_and_second_axis` (the non-folded scenes most sensitive to
the bundle finalizer) must stay PASS — confirming the folded gate leaves them byte-identical.

## In-app eyeball owed

The rays are a VTK-only 3-D overlay (headless VTK render of this scene is segfault-prone). The
geometry is proven display-free: 0 of 250 drawn rays now cross below the mirror at the axis; the 53
marginal rays stop at the first lens group instead of doubling back through the fold. The user should
fully quit + relaunch, confirm the downward fan crossing the 45° hypotenuse is gone (only the folded
+X imaging cone reaching the sensor + the incoming +Z beam-to-the-mirror remain), and re-flag if not.
The separate "FOV 19.3, not 1×" magnification observation (the marginal rays that DO reach X≈288 but
land at Z≈−29, below the sensor) is a different, deferred issue and is not addressed here.
