# 0290 — "still a small patch of illumination"

Flag `flag_20260713_073358_441` (description: *"still a small patch of illumination."*), following the
0288/0289 illumination-footprint work on the MV-150 coaxial scene.

## Symptom
On the real vendor scene the detector's **Relative illumination** overlay is a tiny central patch
(~5.9 mm) instead of a filled 39×39 mm FOV, even though a big physical LED module is visible near the
beam-splitter cube.

## Root cause (confirmed end-to-end through the real API)
`add_illumination_led_source` (`KrakenOS/UI/services/source_modeling.py:982`) seeds the emitter from the
**imaging Source panel**:

```
ox,oy,oz = _current_source_origin()      # (0,0,0)  = the object plane
dl,dm,dn = _current_source_direction()   # (0,0,+1) = +z, AWAY from the object
half     = max(_current_source_radius(), 5.0)   # 5 mm  -> a 10×10 mm square
```

So the added illuminator is a **10×10 mm square sitting on the object plane aimed +z** — the imaging
field-point settings, not an illuminator. The overlay then *honestly* images that tiny emitter → a
~5.9 mm patch (|m| = 0.5908). The emitter is **decoupled** from the big physical LED module the user
placed (`led_step_path` = `OPT-CO90-X-V1.6.2-H.STEP`, glued at `led_object_edge_distance_mm=200`, moved
+22.9 x). Moving/resizing the module glyph is cosmetic — it never feeds the launch origin.

### Definitive as-file confirmation (`bugs/diag_0290b_asfile.py`)
```
1. vendor AS-FILE (scene_sources:[])                       -> PRODUCTION OVERLAY None (blank)   ✓ gate holds
2. + add_illumination_led_source()  (source:led-1,
     origin (0,0,0) dir +z rx=ry=5)                        -> dims(33,33) fold=perp=0.000        ← THE FLAG
```

### Placement/aim matrix (`bugs/diag_0290_small_patch_probe.py`, real vendor scene)
| # | emitter (origin / aim / half-size) | overlay |
|---|---|---|
| A | (0,0,0) / +z / 5×5   *(= real default)* | **small patch**, fold=perp=0.000 |
| B | (0,0,0) / +z / 55×45 | uniform (1.089 / 1.035) |
| C | (0,0,225) / +z / 55×45 (toward lens) | blank |
| D | (0,0,225) / −z / 55×45 (toward object) | fills FOV, soft dark edges (0.876 / 0.849) |
| E | (28.6,0,229.6) / −x / 37×27.5 (into +x face) | blank (absorbed at authored Absorber face — 0289) |

Only a **big source seated near the module aimed toward the object** (D) produces the filled FOV with
soft edges the user expects.

## Physics notes
- The module is a **coaxial** illuminator (OPT-**CO**90): its net output is down the optical axis. Its
  object-facing (min-z) face is at z≈187, *below* the promoted BS cube (z 202–257), so an emitter there
  aimed −z reaches the object cleanly **without re-tracing the BS** (no double-count).
- The true side-in → BS-reflect → object path with the illuminator's ~30 mm limiting window (the source
  of the *hard* fold dark edges) remains 0289's documented **future engine work** (split-branch rays
  don't consult later aperture rows).

## Fix (SHIPPED — bounded, general, display-follows-physics)
`add_illumination_led_source` now **seeds the emitter from the physical LED module when one is present**:
origin = module object-facing (nearer-object z) face centre, half-extents = module transverse world
bounds, aim = face → object-plane point on the optical axis. Falls back to today's panel-derived values
only when no module exists. Reads the same transformed CAD mesh the 3D scene draws (no hardcoded
size/position); the emitter then coincides with the visible physical LED, killing the tiny-patch default.

- **Pure geometry**: `illumination_emitter_seed_from_module_bounds(bounds, object_plane_z)` in
  `KrakenOS/UI/services/source_modeling.py` — object-facing face + aim toward the FOV axis + per-axis
  half-extents; face/aim flip with the object side; degenerate/non-finite/mis-shaped → None.
- **Instance wiring**: `_illumination_emitter_module_seed` — gated on `imported_led_step_path`, reads the
  transformed mesh bounds + object-plane z (`_object_surface_plane_z`), fails soft to None.
- **Rewire**: `add_illumination_led_source` uses the module seed when present, panel fallback otherwise,
  and writes per-axis `radius_x`/`radius_y`.

### End-to-end outcome (real vendor scene, synthetic OPT-CO90 injected — `bugs/diag_0290c_module_seed.py`)
| emitter | origin / aim / half | overlay |
|---|---|---|
| panel default (no module) | (0,0,0) / +z / 5×5 | dims(33,33) fold=perp=0.000 **lit 7%** (tiny patch) |
| module seed (bugs/0290) | (28.6,0,187) / toward object / 27.5×39 | dims(12,12) fold 1.14 perp 1.11 min_rel 0.93 **lit 100%** (filled FOV) |

The filled FOV is *uniform with a soft ~7% roll* (fold/perp > 1), **not** hard 2-side dark edges: with no
limiting aperture on the vendor import every FOV point sees the whole LED. The hard-edge window remains
0289's documented future engine work (split-branch rays don't consult later aperture rows).

Guard: `KrakenOS/UI/validate_open3d_illumination_emitter_module_seed.py` (`run_checks()`), penta
**phase 254**, baseline updated. Non-regression: phase 253 (bugs/0288) stays green — headless has no
module, so it exercises the unchanged panel-fallback path.
