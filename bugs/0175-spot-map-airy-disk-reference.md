# 0175 — FEATURE: Airy-disk (diffraction-floor) reference on the Spot map

## Insight (user)

> The lens vendor spec says resolution: 4.5 µm — how can you focus to sub-pixel? Because
> this surrogate is far from the real prescription?

Right on two counts: the surrogate is an ideal `Thin Lens` (no aberration) AND geometric
ray-tracing has no **diffraction** floor. So a geometric spot can shrink to ~0, which is
unphysical — no real lens beats the Airy disk.

## What was added

The Spot map now draws the **Airy disk** (diffraction limit) as an orange circle at every
spot, magnified by the same factor as the spots. `airy_radius = 0.61 λ / NA`, with `NA` the
largest image-space ray angle of the on-axis bundle (so it's the *actual* working NA, not an
assumed f/#). The label gains `Airy ⌀<d> µm (orange) = diffraction floor`.

Reading it: a geometric spot drawn **inside** the orange circle is below the physical limit
— a tell-tale of ideal/surrogate optics. On the MV-150 (a finite conjugate, working ~f/13)
the Airy diameter is ~21.6 µm (≈ 5 px); the focused surrogate spot (0.1–1 µm) sits ~10×
inside it, i.e. unphysically sharp. The real resolution floor is the Airy disk, which is
roughly what the vendor's "resolution" figure reflects.

`build_spot_field_map` gains `airy_radius_mm` -> `airy_circles`; the editor computes the NA
from the traced on-axis rays (`_airy_radius_mm_from_rays`); the inspector draws the orange
circles + label. Guard `validate_open3d_spot_field_map` extended (Airy radius sane, one
circle per field); penta phase 162 covers it.

## Note on "improving the surrogate" / black box

The "Blackbox Group" elements in the scene are just `Thin Lens` (ideal) — the name is a
label, not a real aberrating black-box model. The analysis *does* trace through them (they
give the EFL) but they contribute zero aberration. A true vendor black box (hidden but
ray-traceable real surfaces) or the real prescription is what yields real image quality;
there is no way to recover aberrations from the first-order surrogate itself.
