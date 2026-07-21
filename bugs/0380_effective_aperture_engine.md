# 0380 — General effective-aperture engine (illumination path)

**Origin:** user architectural correction (2026-07-21), following the 0379 CA-pick work and the
verification that the BS does not clip the coaxial illumination in the non-seq trace.

> "Picking CA is one thing. Determine the whole system clipped aperture is another. The dark side
> may be caused from other clipped CA, which is not from LED as general. This is [two] separate
> two issues."

**Two separate issues:**
1. **Pick a CA** (bugs/0379) — an *input*: declare one physical aperture from clicked geometry.
2. **Determine the whole-system effective clipped aperture** (this bug) — a general *computation* over
   ALL apertures on the path. The dark edges come from whichever aperture is most restrictive, which
   can be ANY element (LED opening, beam-splitter, lens stop, mount, picked CA), **not assumed to be
   the LED**.

The old coaxial heatmap hard-codes issue 2 as the LED's `aperture_fold_mm=55` (→ 38.9 foreshortened),
because the non-seq folded trace structurally will not clip the illumination (a split-branch ray never
consults a downstream limiting aperture — bugs/0287/0289). This engine replaces that one hard-coded
guess with a general geometric computation.

## The engine (general-not-special-case)

```
inventory every aperture (a convex shape at a plane)
  -> project each onto a common reference plane along the beam (unfolding any folds)
  -> INTERSECT them
  -> the effective footprint, with each boundary edge attributed to the aperture that limits it
```

The per-edge attribution is the "who clips" diagnostic the user has been chasing: the engine reports
*which* aperture makes each dark edge. It reduces to the old foreshortened-LED answer when the LED is
in fact the limiter, but no longer assumes it.

**v1 projection model:** orthographic along the reference-plane normal, after unfolding each aperture
across the fold plane(s) between it and the reference. Tilt foreshortening is inherent (a 45°-tilted
aperture projects to cos45 of its extent — the fold foreshortening falls out geometrically, computed
once, not double-counted). Source-distance magnification and penumbra softening are documented
refinements, not v1.

## Layers

- **L1 — pure engine** (`services/effective_aperture.py`): `rect_boundary` / `circle_boundary`,
  `reflect_points_across_plane` (unfold), `project_onto_plane_2d`, `clip_convex` (Sutherland-Hodgman),
  `effective_footprint` (project → intersect → attribute). Display-free, numpy only. **SHIPPED**,
  guard `validate_open3d_effective_aperture` (intersection + attribution + foreshorten + unfold +
  empty + circle).
- **L2 — inventory** (`three_d_scene_tools._illumination_effective_aperture`): builds the
  illumination-path apertures as co-centred shapes in the object plane's (fold, perp) frame — the LED
  source (from the descriptor, tilted so the engine foreshortens the fold axis) + every recorded/picked
  clear aperture (0134 + 0379) — intersects them, and returns the effective half-extents + the limiting
  aperture(s). **SHIPPED.** (BS / lens-stop / true off-axis placement are documented refinements.)
- **L3 — wire to the heatmap** (`_coaxial_illuminator_overlay_spec`): when the engine yields a
  footprint, draw THAT (already projected → `fold_angle=0` so it is not foreshortened twice) and log the
  limiting aperture; else fall back to the LED-only synthetic (unchanged when the LED is the sole
  limiter). **SHIPPED.**

**Verified on the real `machine_vision_150mm_test.py`:** no CA → 38.9×74 limited by *led source* (== old
behaviour, no regression); a 30×30 CA → 30×30 limited by *clear aperture 1* (the CA takes over); a
fold-only 20×100 CA → 20×74 with **mixed per-edge attribution** (fold = CA, perp = LED — the "who clips
each edge" answer); a 200×200 CA never limits (LED still wins). Live in-app eyeball owed.

## Files

- `KrakenOS/UI/services/effective_aperture.py` — the pure engine (L1).
- `KrakenOS/UI/services/three_d_scene_tools.py` — `_illumination_effective_aperture` (L2) +
  `_coaxial_illuminator_overlay_spec` wiring (L3).
- `KrakenOS/UI/validate_open3d_effective_aperture.py` — display-free guard, penta **phase 321** (pure
  engine + inventory/wiring).
