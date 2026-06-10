# 0046 — Cemented doublet duplicates itself in 3D (the microns-thick bond drawn as a slab)

**Status:** Fixed (2026-06-10).
**Component:** 3D side-body rendering. `_iter_3d_side_body_meshes` in
`KrakenOS/UI/services/three_d_scene_tools.py`.

## Symptom

User flag (`attachment/recorded_bug_repros/flag_20260610_085002_114/`):
*"3D lens element not matching 2D."* — *"Seems like the 3D lens element is
duplicating itself."* The loaded prescription was the Zemax short-course
`Advanced Optical System Design Using OpticStudio/Doublet_4_surf_no_TDE.zmx`
("A SIMPLE DOUBLET USING A CROWN AND A FLINT"). The 2D layout pane showed one
cemented doublet; the 3D view showed what read as an extra, duplicated element.

The user then asked the sharp question: *is this a North-Star violation?* It is
**not**. North-Star invariant #2 forbids the 2D pane being a *separate
simulation* from the 3D scene. Here both panes render the SAME traced scene
data — three real glass volumes. The mismatch is a 3D *legibility* artifact, not
a divergence of the underlying model.

## Root cause

The prescription models the crown/flint bond as a **real, third glass**: a
`___BLANK 1 3 1.5597575 42.3262` model cement (nd ≈ 1.560, vd ≈ 42.3) just
**0.0075 mm (7.5 µm)** thick, between the 8 mm BK7 crown and the 5 mm F2 flint —
surfaces at z = 102 / 110 / 110.0075 / 115.0075.

`Prerequisites3D` builds one `BBB` solid per glass-bearing surface (one body for
each surface whose following medium is not NULL/AIR/MIRROR). So the 7.5 µm cement
gets its own full-aperture `Side3D` body, drawn semi-transparent like any
element. Edge-on at 0.18 opacity it stacks against the crown and flint and reads
as a duplicated element. The 2D meridional (X = 0) slice draws lens bodies from
the optical-surface *profiles*, so the same 7.5 µm collapses to a sub-pixel
hairline — invisible. Hence "3D not matching 2D".

Headless confirmation (`_iter_3d_side_body_meshes` on the rebuilt system):
three bodies at `side_number = [2, 3, 4]`; body 1 (front surface 3, the cement)
has an axial thickness of 0.0075 mm — the spurious slab.

This is **different glasses** (BK7 / cement / F2), so a "merge same-material
bodies" rule would not apply and would be wrong; the distinguishing signal is the
microns-scale **thickness** of a bond layer.

## Fix

`_iter_3d_side_body_meshes` already draws some bodies at opacity 0 to keep their
actor (so `_row_actor_map` centroid queries resolve) while hiding them (the
analytic-STEP body case). Extend that: a glass layer thinner than
`_CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM` (0.05 mm) is a cement / optical-contact
bond, never a free-standing mechanical element, so its body is drawn invisibly.

```python
layer_thickness_mm = abs(float(getattr(row, "thickness", 0.0) or 0.0))
if layer_thickness_mm < _CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM:
    body_opacity = 0.0
```

Real elements — even thin field flatteners — have centre thickness far above
0.05 mm; cement bonds sit at 5–25 µm, so 50 µm cleanly separates the two. The
cement **optical surface stays in `AAA`**, so ray tracing is untouched; only the
redundant *body* is hidden. A cemented doublet then reads as two cemented
elements in 3D, matching 2D. Model fidelity is unchanged (the three glass volumes
still exist in `BBB`); this is purely a presentation choice in the renderer.

### Second half: the live inspector re-inflated the hidden body (rays on)

The opacity-0 above is set in `_iter_3d_side_body_meshes`, but the live "Open 3D"
view runs every mesh item through `open3d_scene_refresh.refresh_scene`, which —
**with rays visible** — clamps each analytic optic body back up to
`min(max(mesh_opacity, 0.26), 0.40)` so lenses read as glassy translucent glass.
That clamp silently re-inflated the cement body to a full-aperture slab **and**
redrew its rim outline (the rim block is gated on `analytic_optic_surface and
mesh_opacity > 0`). So the display-free fix held, yet the user's live rays-on
screenshot still showed the duplicate plus an extra edge line at the bond.

The completion (in `refresh_scene`) treats a side-body that **arrived already
invisible** (`is_body and mesh_opacity <= 1e-3`) as intentionally suppressed —
the same way the redundant analytic-STEP drum already was — and pins it at
opacity 0 through the ray-visibility clamp:

```python
body_pre_hidden = row_is_body and mesh_opacity <= 1e-3
keep_body_hidden = analytic_hidden_drum or body_pre_hidden
if keep_body_hidden:
    mesh_opacity = 0.0
```

Because the rim/feature-edge outline is gated on `mesh_opacity > 0`, holding the
body at 0 also drops its stray inner rim line. The legitimate per-surface rims
stay: the cemented doublet shows the crown-front line, the (two near-coincident,
7.5 µm-apart) cemented-interface cap rims that merge into one line edge-on, and
the flint-back line — i.e. two cemented elements, no duplicated slab, no extra
edge.

### Third half: the body-drum OD rim was a second ring per lens (5 rims, want 3)

The user then flagged (screenshots `3D-1.png` / `3D-2.png`) that an extra rim was
*still* present and "some unknown artefact at the edge." The cement body was now
genuinely hidden — but each glass **row** draws TWO round rims, not one: the
optical **cap** rim at the clear-aperture edge (~28.7 mm) *and* a separate
mechanical **body-drum** OD rim at the full diameter (30 mm), at slightly
different z. So the doublet drew five rim lines edge-on — crown-cap (z≈104.0),
crown body-OD (z≈106.1), the merged bond (z≈108.1), flint body-OD (z≈111.3),
flint-cap (z≈114.7) — and the two body-OD rings read as the "extra rim" plus the
axis-crossing edge sliver.

Fix (`open3d_scene_refresh.refresh_scene`, rim-drawing block): draw the round rim
circle for the optical **caps only** — `draw_round_rim = rim_is_round and not
row_is_body`. A round analytic **body** keeps its translucent glassy fill (the
shape silhouette still reads the lens curvature) but no longer paints a duplicate
OD ring, and the feature-edge fallback is skipped for round bodies
(`if not (row_is_body and rim_is_round)`). Plano-cyl / plate bodies are not round,
so they fall through to feature edges exactly as before. The doublet now draws
exactly **three** lens rim lines (crown front z≈104.0, merged bond z≈108.1, flint
back z≈114.7), matching the 2D profile, with the lens shapes unchanged. The live
snapshot guard pins this with a `rim_count == 3` assertion.

## Tests

`KrakenOS/UI/validate_cemented_doublet_body_count.py` (display-free; SKIPs if
PyVista/VTK is unavailable). It builds the flagged doublet via the real
`_iter_3d_side_body_meshes` against a `__new__`-built editor (no Tk root) and
asserts: (A) the doublet keeps **three** `BBB` bodies but exactly **two
visible** ones, with precisely the sub-0.05 mm cement layer hidden; (B) a clean
singlet keeps its one body; (C) a real cemented doublet with no modelled bond
keeps both bodies; (D) a thick triplet keeps all three (no false suppression);
(E) the doublet's two visible bodies render to a non-blank PNG
(`attachment/cemented_doublet_3d_bodies.png`) — inspected by eye: two abutting
cemented elements with a faint interface seam, no third slab.

A property-only test was **not** enough: this same display-free guard passed
while the live render still drew the slab (the rays-on re-inflation above) — the
exact "VTK-property assertions alone missed the ghost block" failure mode. So a
second, **live** guard `KrakenOS/UI/validate_cemented_doublet_body_count_snapshot.py`
boots the real inspector with **rays ON**, looks edge-on, and asserts at the live
actor level (and in a rendered PNG it eyeballs) that **no filled glass body is
confined to the sub-0.05 mm cement band** while the crown and flint stay visible.
The discriminator: a glass *body* carries polygon faces (`GetNumberOfPolys() > 0`)
whereas a rim is a polyline (0 polys), and a *strictly positive* sub-0.05 mm
axial extent separates a microns-thick slab from a flat reference disc
(thickness exactly 0). Both guards are folded into the comprehensive harness as
**Phase 51** (the live one reuses the shared harness inspector, so no second Tk
root; SKIPs without a renderer).

## Verification note

Rendered the visible bodies off-screen (display-free) and the full live rays-on
scene edge-on under Xvfb, and inspected both PNGs: the crown and flint draw as
one continuous cyan glass stack with a hairline cement interface — two cemented
elements, not a duplicated third block, and no extra edge line at the bond —
matching the 2D pane. The live actor dump confirmed the 7.5 µm cement body sits
at opacity 0.000 even with rays on, while the crown and flint bodies stay at the
glassy 0.26 clamp.
