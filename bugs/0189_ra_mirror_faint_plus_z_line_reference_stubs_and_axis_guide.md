# 0189 — BUG: after 0188 the folded RA-mirror scene STILL shows a faint +Z line — two display actors that don't fold (blocked pupil reference-ray stubs + the over-extended global optical-axis guide)

**Status: RESOLVED (two source-level fixes, both scoped to promoted-mirror FOLDED scenes only,
so unfolded / plain / sequential-mirror layouts stay byte-identical). Bug 0188 (commit `6ab17579`)
correctly folded the detector TARGET + all three of its consumers onto +X; these are the TWO
REMAINING contributors to the "faint line" the user kept re-flagging, neither of which is a
detector/overlay:**

1. **29 blocked pupil/field REFERENCE-ray stubs** stranded on the unfolded +Z axis. They never
   reach the mirror (`termination_reason='stopped_at_surface_0'`, `branch_power=0`,
   `reaches_image=False`, `source_role='pupil_field_reference'`), so the display fold never carries
   them — they draw as a faint +Z line from the object up to Z≈120.
2. **The global optical-axis guide (`axis:global`, `dotted_global_guide`)** over-extended up +Z to
   Z≈386 (≈300 mm PAST the mirror), reaching toward the folded detector. `_optical_axis_z_span`
   pads the guide by `0.65 × _bounds_span`, and `_bounds_span` = max(X,Y,Z extent). In the folded
   scene the +X branch makes **X** the largest extent (369 mm), so the +Z guide inflates far past
   the fold point.

## Flags — the same "faint line" re-flagged three more times (all POST-date the 0188 fix)

The 0188 fix is commit `6ab17579` (2026-07-01). All three flags below post-date it and were logged
on the folded AZURE ELS-85 layout (`KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`):

- `attachment/recorded_bug_repros/flag_20260701_081756_830/` — *"reflection rays still follow the
  fainted line perpendicular to the hypotenuse mirror surface."*
- `attachment/recorded_bug_repros/flag_20260701_084145_529/` — *"still the same, reflected from a
  faint line."*
- `attachment/recorded_bug_repros/flag_20260701_084745_972/` — *"Unpromote and promote again, still
  the same. Also notice the FOV is 19.3, not 1X."* (the FOV note is a separate magnification
  observation, tracked apart — the RA-mirror surrogate images at ≈1.19×, not the 1× the user
  expects; not part of this faint-line fix.)

The 0188 detector fold is genuinely in place (headless: row-8 detector target folds to
X≈287.82, Z≈71.9, normal +X). The residual "faint line" is NOT the detector — it is these two +Z
display actors that 0188 never touched.

## Root cause — measured headlessly on the live AZ85 bundle, not eyeballed

Building the real bundle (`editor._build_scene_bundle`) and inspecting `bundle.ray_paths`:

```
total ray_paths           = 279
  missed_image            = 250   (real launched rays — 197 fold to +X, 0 travel up +Z)
  stopped_at_surface_0    =  29   (blocked pupil_field_reference stubs, all on the +Z axis)
blocked-stub Z-max        = 120.065   (a faint +Z line from the object up to Z≈120)
```

All 279 paths carry `source_role='pupil_field_reference'` (this preview builds the display set from
the reference bundle), so the discriminator for a STUB is the strict AND: `pupil_field_reference` +
`stopped_at_surface_0` + `branch_power≈0` + `not reaches_image`. Classifying the 250 real rays by
endpoint proves **197 fold to +X and ZERO travel up +Z past the mirror** — the global max-Z point
(Z=145.54) sits at **X=287.82** (on the folded +X cone at the detector), not on the +Z axis. So
once the 29 stubs are gone, no RAY draws a +Z line.

The remaining +Z line is the axis guide. All seven folded rows (2–8) fold to a constant world
**Z=71.897** on the +X branch (the fold plane / mirror vertex). Yet:

```
_bounds_span            = 369.29   (X-ext=369.3 dominates; Z-ext=207.2)
global guide z-span      = -301.73 .. 385.58   (+Z end is ~314 mm PAST the mirror at Z=71.9)
```

The guide is drawn straight up the +Z axis (x=y=0) from −301.73 to **+385.58**, a faint dotted line
reaching from behind the object all the way past the mirror toward the folded detector. That is the
"faint line perpendicular to the hypotenuse" — a +Z line crossing the 45° mirror.

## Fix (two source-level changes, both folded-scene-scoped)

### Fix A — suppress the blocked reference-ray stubs at the bundle source

`KrakenOS/UI/services/layout_scene_bundle_display.py`:

- new module predicate `_is_blocked_reference_ray_stub(path)` — true only for a
  `pupil_field_reference` path that stopped at surface 0 with no branch power and no image reach
  (pure sampling scaffolding that never propagated; a real `missed_image` / detector-reaching ray
  is never a match);
- new `LayoutSceneBundleDisplayMixin._suppress_blocked_reference_ray_stubs(bundle)` — filters
  `bundle.ray_paths`, but ONLY when the scene is folded (`any` row carries an
  `_optical_axis_fold_world_transform_for_row` override — the same gate the 0188 detector fold
  uses). Unfolded scenes early-return 0 → every ray byte-identical.
- called from `_build_scene_bundle` in the single-axis `else` branch, right after
  `_fold_promoted_mirror_table_row_targets(bundle)` (the two-arm splitter path replaces
  `ray_paths` with its own per-arm folded paths and is left untouched).

Reassigning `bundle.ray_paths` propagates to every downstream consumer — the 3-D actors, the 2-D
projection, and the bounds augmentation — so the stubs vanish from all views at once. AZ85:
279 → 250 paths, 29 → 0 blocked stubs.

### Fix B — clamp the global +Z optical-axis guide to the fold point

`KrakenOS/UI/open3d_inspector.py`:

- new `Kraken3DInspector._folded_axis_incoming_fold_point_z()` — applies each folded row's rigid
  fold transform to its straight +Z anchor and returns the nearest resulting world Z (the fold
  plane / mirror vertex); `None` for an unfolded scene (no row folds) → the guide is left
  byte-identical;
- in `_optical_axis_records_for_3d`, right after `z0, z1 = _optical_axis_z_span(bounds)`:

  ```python
  fold_point_z = self._folded_axis_incoming_fold_point_z()
  if fold_point_z is not None and np.isfinite(fold_point_z):
      z1 = min(z1, float(fold_point_z) + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM)  # 5.0 mm
  ```

The +Z global guide is only the INCOMING optical axis (object → mirror); past the mirror the axis
bends onto +X, which the traced-segment records already draw (when Show Rays is on). Clamping the
far end to the fold point + 5 mm stops the guide at the mirror instead of letting the folded +X
width inflate it. AZ85: z1 385.58 → 76.9 (a 97% reduction; the stray reach is gone). The object-side
z0 (−301.73, a −Z tail trailing behind the object, away from the folded image) is deliberately left
unchanged — it is not the flagged symptom and clamping it would widen the blast radius.

## Guard

`KrakenOS/UI/validate_open3d_ra_mirror_faint_line_folds.py` (standalone, NOT penta) — binds the
REAL helpers (`_is_blocked_reference_ray_stub`, `_suppress_blocked_reference_ray_stubs` bound to the
live editor, and `Kraken3DInspector._folded_axis_incoming_fold_point_z` bound to a stub carrying the
editor):

1. AZ85 emits 29 blocked `pupil_field_reference` stubs, and the built bundle has 0 left (Fix A ran);
2. no real ray in the built bundle travels up +Z past the mirror (endpoint classification: the only
   high-Z points sit on the folded +X branch);
3. the REAL fold-point helper returns Z≈71.9 for AZ85, and the +Z guide clamps from ≈386 to ≈77
   (past-mirror reach eliminated);
4. a non-folded layout (`flat_mirror_45_deg.py`) reports fold-point `None`, and
   `_suppress_blocked_reference_ray_stubs` on a synthetic stub-bearing bundle returns 0 dropped —
   the folded-scene gate keeps unfolded scenes byte-identical even when such stubs exist.

Sibling AZ85 guards (0185 fold-follows-reflection, 0186 launch-is-cone, 0187 folded-sequential
trace, 0188 detector-coverage folds) + `validate_machine_vision_azure_85_ra_mirror` still PASS.

## In-app eyeball owed

The ray stubs + optical-axis guide are VTK-only 3-D overlays (headless VTK render of this scene is
segfault-prone). The geometry is proven display-free: the built bundle has 0 blocked stubs, no real
ray runs up +Z, and the guide clamps to the mirror at Z≈77 instead of Z≈386. The user should fully
quit + relaunch, confirm the faint +Z line is gone (only the folded +X optics + the incoming +Z
axis-to-the-mirror remain), and re-flag if not. The separate "FOV 19.3, not 1×" magnification
observation is not addressed here.
