# 0065 — Open 3D: an off-beam promoted solid corrupts the on-axis trace

## Symptom (user's words)

From the in-app repro bundle `attachment/recorded_bug_repros/flag_20260612_073237_607`:

> randomly put beam splitter off the ray path, after Face Editor, the rays heir
> wired, some thickness measurement wrong location, the rays seems to chase the
> beam splitter, behave like sequential rather than non-sequential. Wrong from
> fundamental North Star achitecture. Image circle shown offset as well.

The user promoted a beam-splitter cube to an optical-solid row and dragged it
**clear of the beam**. The on-axis LED→lens→detector trace then went wrong:
focus landed short of the detector, the rays diverged and appeared to "chase"
the off-axis cube, a thickness dimension drew in the wrong place, and the image
circle was offset — the layout behaved sequentially even though
`resolved_trace_mode.use_nonseq` was `true`.

The recorded `scene_state` confirms it: `picked_row_index = 6`, and row 6's actor
bounds are `X[77.5, 133.1] Y[146.8, 202.3] Z[341.1, 419.7]` — a ~55 mm cube
centered ~203 mm off the `X=0, Y=0` optical axis, while rows 0–5 (the lens stack)
and row 7 (the camera) sit on-axis.

## Root cause

A promoted optical-solid row carries its lateral placement in the row's
`desp_x` / `desp_y` (the lateral drag writes there — `scene_placement_commands`).
`layout_editor._build_system_from_specs` copies those verbatim onto the built
`surface.DespX` / `surface.DespY`:

```python
surface.DespX = float(spec.get("desp_x", 0.0))
surface.DespY = float(spec.get("desp_y", 0.0))
```

In KrakenOS a surface decenter is a **propagating coordinate break**, so the
off-axis cube tilts the entire centered prescription downstream of it. Because
every paraxial / best-focus / spot-RMS / image-circle computation builds its
trial system through this one chokepoint (`paraxial_tools` and
`analysis_compute_workflow` both delegate to it; the live trace reaches it via
`_build_cached_system_from_specs`), the off-beam solid leaks into the centered
solve and shifts the conjugates — focus short of the detector, image circle
offset, rays "chasing" the displaced body. The solid is also still meshed as an
STL body in the trace, so it perturbs the non-sequential launch.

This is a North-Star violation: in true non-sequential operation a body the beam
never reaches must contribute **zero** optical effect. The earlier attempt
(`02323d2`, reverted in `01a7743`) forced the layout *sequential* for off-beam
solids — wrong: it turned the off-axis cube into a vignetting surface ("rays
stop half way"). The correct model is **display-only**: an off-beam inert solid
stays a drawn scene body but leaves the optical trace path entirely, until it is
on the beam **or carries an active coating**.

## Fix (files + lines)

`KrakenOS/UI/services/offbeam_optical_solid.py` (new, pure / display-free):
`neutralize_offbeam_inert_solids(row_specs)` returns a copy of the specs in which
each **off-beam inert promoted solid** is replaced by a flat zero-power **AIR**
surface at the on-axis station — same `thickness` / `diameter` / surface kind, so
the surface count and axial chain are preserved (no index desync, detector
station unchanged), with `desp`/`tilt` zeroed, `rc` 0, `Solid_3d_stl` → `"None"`,
and the promotion / face-role / output-port metadata dropped. Classification:

* **Promoted optical solid** — `Solid_3d_stl` present + STEP-overlay promotion
  metadata or STEP source (mirrors `_open3d_step_label_for_optical_solid_row`).
* **Inert** — no face carries an active function (`Mirror` / `TIR` /
  `Beam Splitter` / `Absorber/Mechanical`). A *coated* splitter is exempt and
  stays in the trace (North Star "on the beam **or coated**").
* **Off-beam** — the solid's nearest transverse edge clears the beam radius by
  ≥ 2× (and ≥ 1 mm): `hypot(desp_x, desp_y) − half_extent ≥ 2·beam_radius`, where
  `half_extent` comes from the `StepOverlayPromotion` world bounds (drag-invariant)
  and `beam_radius` is the largest on-beam optical semi-diameter. Deliberately
  conservative — nothing near the beam is ever neutralized.

`KrakenOS/UI/layout_editor.py` — `_build_system_from_specs` calls
`row_specs = neutralize_offbeam_inert_solids(row_specs)` at the **top**, so the
neutralized specs feed BOTH the surface-build loop and
`apply_optical_solid_output_port_system_overrides(system, row_specs)` (which
keys off `Solid_3d_stl` via `_row_has_optical_solid`, so the solid is dropped
from the output-port repositioning too). The input list is never mutated; a
layout with no off-beam solid is returned unchanged (zero overhead).

The **3-D body still draws** — the inspector renders promoted solids from the
live row overlay, not from these transient build specs (the same property that
lets bugs/0021's missing-mesh neutralization keep its placeholder body).

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_offbeam_solid_display_only.py` (display-free, 18
checks). Pure classifier (off-beam uncoated cube flagged; coated / on-axis /
beam-overlapping / non-solid-mirror all exempt; beam radius; idempotence),
neutralized-spec contents, and the real `_build_system_from_specs` prescription:

* **C2** — the off-beam built surface has `DespX == DespY == 0` (no coordinate
  break) and is a flat AIR no-op (no STL solid traced).
* **C3 (killer)** — the off-beam-cube prescription is **byte-for-byte optically
  identical to a plain air spacer** of the same thickness, i.e. zero optical
  effect: the focus is unchanged, the reported symptom is gone.
* **C4/C5/C6** — a coated splitter and an intentional decentered mirror keep
  their decenter; a solid-free layout is untouched.

Verified failing before the fix (neutralizer stubbed to identity: C2/C2b/C3
fail with `DespX=105`) and passing after.

## Integrated

Phase 66 of `validate_open3d_penta_telescope_comprehensive.py` (display-free
wrapper over the guard). Baseline `tools/penta_validator_baseline.json` updated
(`"66": "pass"`).

## Verification note

The live ray render cannot be confirmed headless — this layout class SIGSEGVs the
offscreen renderer (Xvfb llvmpipe). The fix is pinned by the display-free
prescription guard above (which proves zero optical effect at the system-build
seam); the user confirms the corrected rays in-app.
