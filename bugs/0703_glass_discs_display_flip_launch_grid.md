# 0703 — live follow-ups on the 80 mm swap (flags 103959 + live reports)

Live reports after 0702 shipped: "It is tracing 13878 rays, how come? I still
see the lens surrogate oversized. I am trying to flip the lens body, after
clicking flip, not functioning. Please make sure any STEP manipulation should
stop ray tracing." Then: "I can see only one point of ray launching from
object plane on each side A and B instead of 3."

## 1 — 13878 rays: expected counting, not a bug

The scene launches 9 bundles × 361 rays × 2 faces = 6498 rays; the status
counter counts NON-SEQUENTIAL rays including splitter-branch continuations
(~2.1× ≈ 13878). Same physics as before the swap.

## 2 — discs STILL oversized: the honest cap is the GLASS, not the collar

0702's cylinder barrel (46.0) is real body geometry, but the PYRITE STEPs
show only ~22–28 mm of GLASS inside that collar — the user reads the glass.
New `_step_glass_aperture`: the transverse extent of the largest substantial
spherical face in the vendor STEP (analytic-doc pickle cache when present;
area-gated so a protective window can't win). Clamp order at BOTH importer
sites: glass → cylinder barrel → bbox extent.

Measured: PYRITE 80 → 23.82, 85 → 22.29, 90 → 28.39, 67304 tele → 14.89
(still covers its 0662 object field 11/0.75 = 14.67 — the vendor's front
glass IS the field it guarantees; the old +stop pad exceeded the physical
glass). A corner ray drawn passing the glass rim is the vendor's own
vignette, honestly shown — the 0624 trace extension keeps it refracting.

## 3 — flip "not functioning": buried under the retrace

The flip handlers (0373/0615) PROMISE display-only, but called
`refresh_from_editor()`, which on a promoted-STEP scene forces the full NS
retrace — minutes on om05a, so the flip looked dead. New
`Kraken3DInspector.refresh_step_overlay_display_only`: the 0166 fast path
(re-render the cached system/rays/bundle; the flip's mesh memo keys on the
reverse flag, so the body redraws flipped) with the full refresh as fallback.
Both flip handlers route through it. This is the general pattern for "any
STEP manipulation should stop ray tracing" — other decoration-only
manipulations can adopt the same helper as they are flagged.

## 4 — ONE launch point per face: my own 0702 scene patch's regression

The launch grid spreads over `_imaging_fov_half_extents` = magnification ×
sensor; magnification needs `_shared_first_order_reference`. The vendor seat
is desp + the 0691 `ScenePlacement.frame_seat` breadcrumb TOGETHER — my 0702
patch restored the desp WITHOUT the breadcrumb, so the paraxial reference
read the datum as a hand-tilted prescription and REFUSED the layout
(`Paraxial solve supports centered refractive systems...`) → first order
None → mag None → all nine field pairs collapsed to (0,0). (The user's
pre-patch swap traced multi-field — the swap itself never had this half of
the bug, but a swap on a seated scene WOULD have hit it via the 0702 seat
carry, which also carried only desp.)

Fixes: the swap's seat carry now deep-copies the front datum's
`ScenePlacement` breadcrumb with the desp; the user's scene re-patched
(breadcrumb added, discs 46.0 → 23.8169). Verified: first order f = 82.39,
mag = 0.392 (the user's own header number), half extents 29.4.

## Guards (extends penta phase 511, `validate_open3d_0702_swap_seat_and_barrel`)

A2 breadcrumb carry, C1/C2 glass measure + import clamp, D glass-first
wiring at both sites, E1–E3 flip display-only routing + helper fast/fallback
behavior. `validate_open3d_0668_disc_barrel_clamp` B1/B2 re-pinned to the
glass contract — all green.
