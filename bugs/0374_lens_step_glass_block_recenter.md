# 0374 — Lens STEP overlay jumps ~3 mm off the surrogate when flipped

**Source:** user follow-up to 0373 — "make sure the lens surrogate Front and Rear lens are positioned
at the Lens STEP front and rear lens. Are they matched?" and (after the 0373 flip) the barrel visibly
sits a few mm off its surrogate depending on orientation. **Fix must be general** (any future lens
import), **display-only**. **Status:** SHIPPED 2026-07-20 (guard
`validate_open3d_lens_step_glass_recenter`, penta phase 315).

## Why it happens

A mechanical lens STEP is not centred on its glass: the barrel has different mechanical overhang at
the object vs image end. The overlay alignment pins the **mechanical body front face** at the Front
Optical Vertex Datum (`_cad_mesh_aligned_to_optical_axis`, `target_front_z = front_datum_z`). Because
the glass block sits off-centre in the body by δ, the glass lands `δ` from where the surrogate expects
it — and δ **swaps sign** when the barrel is flipped (`front_face` max↔min, bugs/0373), so the glass
overlay jumps `2·δ` between orientations:

| lens (STEP)                     | on-axis optical spheres | glass span | body span | flip swing 2·δ |
|---------------------------------|:-----------------------:|:----------:|:---------:|:--------------:|
| PYRITE 4.5/85 (1072517)         | 2                       | 39.52 mm   | 47.86 mm  | 1.80 mm        |
| PYRITE (1097303)                | 2                       | 35.58 mm   | 40.08 mm  | 3.56 mm        |
| PYRITE 5.6/80 (1097785)         | 2                       | 43.19 mm   | 47.03 mm  | 1.95 mm        |
| ELS-85 (AZ85)                   | 4                       | 55.00 mm   | 59.19 mm  | 3.51 mm        |

The physics/surrogate is **already correct**: the datasheet Σd (physical vertex span) for PYRITE 85 is
**39.52 mm**, the surrogate's Front→Rear Optical Vertex Datum span is **39.5230 mm**, and this bug's
independent STEP glass detector reads **39.519 mm** — all three agree to 0.004 mm. The mismatch was
*only* in the display overlay's axial anchor (body face, not glass), not in the trace.

## The fix — pin the glass-block CENTRE on the datum-span centre (display-only)

`_lens_step_display_front_z(front_face)` replaces `front_datum_z` as the overlay's `target_front_z`.
It locates the optical **glass block** and re-anchors so the glass centre lands on the surrogate's
datum-span centre (midpoint of Front and Rear Optical Vertex Datum). Because the surrogate datum span
equals the glass span, this puts the glass **front vertex on the front datum and rear vertex on the
rear datum to ~0.002 mm**, and — crucially — makes the overlay **flip-invariant** (both `front_face`
values land the glass centre at the identical world z; measured swing 1.8 mm → 0.000 mm).

### How the glass block is found (general, keyed only on geometry)

`_step_optical_glass_axial_metrics(step_path)`:

- An **optical surface** is a spherical FACE whose curvature centre lies ON the barrel axis (a mount
  fillet's sphere centre is off-axis by ~the body radius, so `perp ≤ max(2, 0.05·body_diag)` cleanly
  rejects non-optical spheres).
- Its **surface vertex (pole)** is the axis crossing `centre ± radius` that lies within **that cap's
  own face bounding box** — the antipode is on the far side of the centre, outside the face. Using the
  face bbox (not the body bbox) is essential: when `2·radius ≈ body length`, *both* poles fall inside
  the body and the body test drops a real optical surface (hit on 1097303 — it went from “None” to a
  correct 2-surface detection once switched to the per-cap face bbox).
- **Use the vertex, never the curvature centre.** (The classic error — see
  `reference_machine_vision_surrogate_recipe`. An earlier pass mis-read this lens's span as 47 mm by
  using centres/antipodes; the datasheet Σd = 39.52 mm is the ground truth the vertex method matches.)
- Requires ≥2 on-axis spheres and a plausible block extent (0.2–1.2× body); otherwise returns `None`
  and the overlay falls back to the old body-face pin (no regression for lenses whose STEP has no
  detectable glass, e.g. aspheric-only or envelope-only CAD).

Cached to `*.glass.v2.json` beside the mesh cache and in `_external_cad_mesh_cache` (negative results
memoised for the session). The overlay's cache signature gains the rear datum z.

### Generalization note (for future lens imports)

The datum-span centre is the right anchor **because the importer sets the datum span to the STEP glass
vertex span** (`STEP_GLASS_VERTEX_SPAN_MM = front_glass_vertex_z − rear_glass_vertex_z`), which equals
the datasheet Σd. So any future lens whose STEP has ≥2 on-axis spherical optical surfaces registers
front-vertex→front-datum and rear-vertex→rear-datum automatically. If a future STEP has near-flat or
aspheric outer surfaces (skipped by the sphere test), the detector may under-span or return `None`; it
degrades to the body-face pin rather than mis-centring. **Gated to untilted overlays** (|rot_x|,|rot_y|
≤ 0.5°): a tilt rotates z out of the barrel axis and breaks the axial-delta relation, so tilted
overlays keep the plain datum pin.

## Files

- `KrakenOS/UI/services/layout_polyline_display.py` — `_step_optical_glass_axial_metrics`,
  `_lens_step_display_front_z`, `_lens_rear_datum_z`, `_cached_step_glass_path`; builder now passes
  `target_front_z=_lens_step_display_front_z(front_face)` and adds the rear datum to the signature.
- `KrakenOS/UI/validate_open3d_lens_step_glass_recenter.py` — display-free guard (penta phase 315).
