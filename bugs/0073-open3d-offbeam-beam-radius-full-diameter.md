# 0073 — Open 3D: direct-promote off-beam splitter still bends the rays (beam radius read as a full diameter)

## Symptom (user's words)

`attachment/recorded_bug_repros/flag_20260612_155154_645`:

> after direct promote the beam splitter without launching face editor.

On the real `machine_vision_120mm_65M` layout the user parked a beam-splitter
cube clear of the ray path and **direct-promoted** it to an optical-solid row
*without* opening the Face Editor. The on-axis trace then went wrong again — the
rays "chase" the off-axis cube exactly like the bugs/0065 report (focus short of
the detector, the image circle offset). This is the same corruption bugs/0065
was supposed to have killed, surfacing on the no-Face-Editor promote path.

The recorded cube (after-state row): bounds `x[-2.62, 47.86] y[50.16, 100.64]
z[217.34, 267.82]` → centre `(22.62, 75.40, 242.58)`, a 50.48 mm footprint. Its
lateral decenter is ≈ 78.7 mm and its transverse half-extent ≈ 25.24 mm, so the
nearest edge clears the optical axis by ≈ **53.5 mm** — comfortably off a lens
group whose widest clear aperture is Ø46 mm (a 23 mm beam radius).

## Root cause — a diameter-vs-radius unit bug in the off-beam classifier

bugs/0065 neutralizes an off-beam **inert** promoted solid only when its nearest
transverse edge clears the beam. `is_offbeam_inert_solid_spec` compares a
**radial** inner edge

```
inner_edge = solid_lateral_decenter(spec) - solid_transverse_half_extent(spec)
```

against a threshold built from `beam_clear_radius(row_specs)`:

```
threshold = max(beam_radius * 2.0, beam_radius + 1.0)   # 2x clearance, conservative
```

But `beam_clear_radius` returned the **largest full clear-aperture diameter**, not
a radius:

```python
radius = max(radius, _float_or_zero(spec.get("diameter", 0.0)))   # BUG: full diameter
return radius
```

The `diameter` field is a **FULL** clear-aperture diameter project-wide — KrakenOS
draws every aperture at `Diameter/2` (`Prerequisites3D.py:210/284/466`,
`Display.py:1077`, `PupilTool.py:836`), and an Image row's `diameter` is the literal
image-circle "Ø". So for this layout `beam_clear_radius` returned **46** (the Ø46
lens) where the true beam radius is **23**. The threshold became
`max(46·2, 46+1) = 92` — effectively **4× the true beam radius** — and the cube's
genuine 53.5 mm clearance was rejected (`53.5 < 92`). The cube was left in the
centered prescription, and `_build_system_from_specs` copied its `desp_x`/`desp_y`
onto `surface.DespX`/`DespY` as a propagating coordinate break (the bugs/0065
leak), so the off-axis cube dragged the centered trace off and the rays bent.

`solid_transverse_half_extent` had the same latent error in its **fallback**
branch (when a solid carries no explicit bounds): it returned the surface
`diameter` rather than half of it, mixing a full diameter into a half-extent.
Both live on the radial side of the same inequality, so they must both be
semi-diameters.

This is **not** a coating regression. `is_offbeam_inert_solid_spec` checks
`solid_has_active_coating` **first**; the recorded cube is uncoated (a
direct promote auto-assigns only a front/back `Transmit/Port` pair, no active
face), so the bugs/0066 coated-splitter exemption is reached the same way before
and after this fix. The fault is purely the inflated clearance threshold.

### Why the existing guards missed it

bugs/0065 / 0066 / 0067 are all display-free and exercise the real
`_build_system_from_specs`, but their lens fixtures put **semi-diameter** values
(e.g. `_lens(17.5, …)`) into the **full-diameter** `diameter` field. With a
"radius" of 17.5 the doubled threshold was 35 and the test cubes (decenter −55,
inner edge 42.5) still cleared it, so every fixture happened to land on the
correct side of the bug. The unit error only bites when the *real* full
diameters are wide and the cube's clearance sits between `1×` and `2×` the true
beam radius — exactly this machine-vision layout. Same fixture-gap lesson as
bugs/0066 (a bare-list coating fixture masked the dict schema).

## Fix (non-sequential — the trace is untouched)

`KrakenOS/UI/services/offbeam_optical_solid.py`:

* `beam_clear_radius` now returns the **semi-diameter** of the widest on-beam
  optical surface (`return 0.5 * max_diameter`), i.e. a true beam-envelope
  *radius* in the same units as the radial inner-edge it is compared against.
* `solid_transverse_half_extent`'s fallback now returns
  `0.5 * max(diameter, 0.0)` (half the clear diameter), matching the bounds-based
  branch above it.

Nothing else changes: the coating-first ordering, the `2×` clearance factor, the
1 mm floor, and the neutralization mechanism are all as bugs/0065 left them. With
the corrected radius the recorded cube now classifies off-beam
(`inner edge 53.5 ≥ threshold 46`) and is neutralized end-to-end (built
`DespX = DespY = 0`) — the coordinate-break leak is gone and the rays no longer
bend, while a coated splitter or an on-/near-beam solid still stays in the
non-sequential trace.

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_offbeam_solid_display_only.py` — the bugs/0065
guard's fixtures were corrected to use full diameters (`_lens(35.0, …)` → 17.5 mm
radius) and a new **Section D** pins the real layout:

* **D1** — `beam_clear_radius` of the wide machine-vision lens group is **23**
  (HALF the Ø46), not 46.
* **D2** — the recorded off-beam cube (inner edge 53.5) **is** classified
  off-beam against the corrected threshold 46 (it was rejected before the fix vs
  the inflated 92).
* **D3** — the cube is neutralized end-to-end through the real
  `_build_system_from_specs`: built `DespX = DespY = 0`, no coordinate-break
  leak.

All three fail before the fix (`beam_clear_radius` = 46, threshold 92, cube left
in the trace) and pass after. The A6 assertion was likewise re-expressed as
"beam radius = HALF the max on-beam full diameter (35 → 17.5)".

`KrakenOS/UI/validate_open3d_coated_solid_schema_exempt.py` (bugs/0066) had its
lens fixture bumped to `_lens(35.0, …)` so its `radius == 17.5` assertion and the
coated/uncoated off-beam contrast stay valid after the halving.
`validate_open3d_offbeam_body_stays_offaxis.py` (bugs/0067) uses
`beam_clear_radius` dynamically and its cube stays off-beam after the halving
(inner edge 42.5 ≥ 17.5), so it needed no change.

## Integrated

Phase 66 of `validate_open3d_penta_telescope_comprehensive.py` wraps the bugs/0065
guard's `run_checks()` and records `detail["checks"]` dynamically (now 22, +3 for
Section D), so the baseline `"66": "pass"` is unchanged. Phases 71/72 (the 0066 /
0067 guards) stay green. No baseline edit needed.

## Verification note

The live render of this machine-vision layout cannot be confirmed headless (it
SIGSEGVs the offscreen Xvfb llvmpipe renderer). The fix is pinned by the
display-free Section D above — which reproduces the real recorded cube against the
real `_build_system_from_specs` and proves the off-beam classification +
end-to-end neutralization — plus the corrected fixtures across the 0065/0066
guards; the user confirms the rays no longer chasing the off-beam cube in-app.
