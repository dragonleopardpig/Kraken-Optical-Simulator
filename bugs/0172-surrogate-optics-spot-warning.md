# 0172 — FEATURE: warn when a spot diagram comes from SURROGATE (ideal) optics

## Insight (user)

> This is ultimately just a surrogate, and I can see a uniform spot diagram over the field.
> I don't think it represents the real lens without a real prescription.

Exactly right. The MV-150 "lens" in the scene is a **surrogate**: two KrakenOS `Thin Lens`
(paraxial, ideal) elements named "Blackbox Group 1/2" between `Lens Front/Rear Datum`
planes. A Thin Lens is aberration-free **by construction**, so a ray-traced spot can only
ever be perfect-focus + **defocus** — and defocus is field-independent, hence the *uniform*
spot map. It cannot represent the real lens's coma / astigmatism / field curvature without
the real prescription. (Confirmed: on the real double-gauss the spot map varies correctly —
round on-axis, coma teardrops at the edge.)

## What was added

`services/surrogate_optics.py` `detect_surrogate_optics(surface_types, element_names)` flags
ideal optics. The strongest, most general signal is the surface **type** `Thin Lens` —
definitionally an ideal lens, so it never false-trips a real prescription (which images
through curved `Standard` glass); a row named/grouped "Blackbox" corroborates. Editor
`_scene_surrogate_optics_info()` runs it on the live rows.

When detected, a warning rides on the spot views:
- **3-D Spot map** label: *"⚠ Surrogate optics (ideal lens) — defocus only, NOT real
  aberrations; load the real prescription"* (alongside the defocus readout).
- **2-D Spot Diagram**: an amber banner: *"Surrogate optics (ideal Thin Lens): spots are
  defocus only, not real aberrations — load the real prescription for image quality."*

So a uniform spot map / diagram is never mistaken for real image quality. The surrogate stays
correct for what it is for — layout, track length, image position, FOV, packaging, the
beam-splitter geometry — just not image quality.

## Guard

`validate_open3d_surrogate_optics_warning` (display-free): the detector (Thin Lens trips it,
all-`Standard` does not, "Blackbox" name trips it); the real measured MV-150 surrogate (2
Thin Lens) vs a real double-gauss (not a surrogate); and both spot-view warning contracts.
Penta phase 166. In-app eyeball owed (the banner/label text on screen).
