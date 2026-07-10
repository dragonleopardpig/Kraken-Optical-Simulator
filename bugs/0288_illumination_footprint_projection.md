# 0288 — The illumination footprint projects onto the sensor at its TRUE imaged size

STATUS: **SHIPPED.** Guard `validate_open3d_illumination_footprint_projection` = penta **phase 253**.

Closes `flag_20260710_170554_093` ("still a small patch launching from object plane") and
`flag_20260710_170627_720` ("heat map") — one root pair, two symptoms.

## What the user asked for

> "tell KrakenOS to launch rays within the 'limited projected area' so that it shows dark edges if exist."
> "no hardcoded value please, it is meant to be general, going to implement it on other setup as well."
> soft roll-off, not a hard mask.

## What the flags actually were (reproduced headlessly — never read off the screenshot)

`bugs/diag_0286_led_placement_probe.py` + `bugs/diag_0288_footprint_linchpin.py` on the real
`attachment/machine_vision_150mm_test.py`:

- The added LED (`add_illumination_led_source`) seats at `_current_source_origin()` = **(0, 0, 0) — the
  object plane** — a 10×10 mm emitter, 30° cone, aimed +z into the system. (The LED *STEP body* sitting
  beside the beam splitter in the flag screenshots is vendor CAD, **not** the scene source. That
  mismatch is what made the flag read as "coaxial".)
- Object surface = index 0, aperture radius **16.29 mm**; sensor half **11.52 mm** (23.04 mm square).

Two independent defects, both now fixed:

**(1) What counted as "illumination on the object" was the source's LAUNCH.**
KrakenOS records a scene source's launch as an object-surface (index 0) event *wherever the emitter
sits*. So `object_illumination_projection_map` → `_source_illumination_hit_samples(system, 0, …)` binned
the LED's own 10×10 mm emitting rectangle (measured: 1738 samples, x,y ∈ [−5, +5]). Park the same LED
coaxially at the beam splitter and its launch events are reported at **x = 90 mm, z = 260.9 mm** — still
"surface 0", still binned as object illumination until the aperture clip happens to drop them.

**(2) The projection stretched that footprint to fill the sensor.**
`project_object_map_onto_sensor` (bugs/0286) rescales the footprint's *own* edges to the sensor
half-extent, so the footprint **always** fills the sensor and under-fill is invisible. A ±5 mm object
patch was drawn across the whole ±11.52 mm sensor — the full-sensor radial bowl the user flagged as
"heat map". Measured: the rescale lights ~34–51 % of the sensor; the true-scale draw lights ~7 %.

## The 0287 "flood sprays ±1000 mm" conclusion was an artifact — corrected here

`bugs/diag_0288_relay_probe.py` traces the source into an **isolated keeper** (as bugs/0270/0272 do for
markers), which attaches the engine's real `traced_polyline_world`. Two findings that overturn 0287:

- Launched-source records carry **no** `traced_polyline_world`. The earlier 0287 probe therefore
  extended each ray's **launch** direction — which runs *parallel* to the object plane — so `|d_z| → 0`
  threw the intersection out to |x| ≈ 8×10⁵ mm. The "±1000 mm flood" was that blow-up, not physics.
- With the true terminal segment, a coaxial LED beside the beam splitter is **absorbed at the cube's +x
  mechanical face** (2-point polyline: launch → absorb). It never enters the cube. The real vendor scene
  has **no coaxial illumination path at all**, so nothing lights the object from there — blank is honest.

The trace-order wall (bugs/0287) itself still stands: KrakenOS traces in surface-index order, so a flood
reflecting off the beam splitter (index 1) back toward the object (index 0) is never re-tested against
surface 0. The relay below is what bypasses it.

## The fix (all in `KrakenOS/UI/services/source_object_coupling.py`)

- **`object_plane_illumination_samples`** — what reaches the object plane, two scene-derived mechanisms:
  - *DIRECT*: an object-surface event whose **world position really lies on the object plane**. This
    plane test is the load-bearing fix for defect (1): only an emitter genuinely on the object plane
    contributes directly (the physical statement "this patch of the object is self-luminous").
  - *RELAY*: otherwise geometrically continue the ray's terminal traced segment onto the object plane —
    the trace-order-wall bypass. `_terminal_ray` takes the engine polyline's last segment (best), else
    the last two `hits`, else the launch ray. **Absorbed** rays illuminate nothing and are skipped;
    **backward** segments are skipped; **near-parallel blow-ups** fall out at the object-aperture clip
    rather than needing a magic distance cut.
- **`object_footprint_irradiance_map`** — bins those samples over their **own** footprint (peak-normalized,
  with the shared 20 % zero border to ramp into), carrying the footprint's TRUE extent.
- **`project_footprint_onto_sensor`** — samples the object footprint at `o = s/|m|` for every sensor cell,
  using the scene's **own paraxial magnification** (`_current_finite_paraxial_magnification`, fixed for
  beam-splitter-cube scenes by bugs/0104). The lit region therefore lands at its real size with a **dark
  surround**. `_bilinear_zero_outside` pads the grid with a zero ring so the footprint edge is a smooth
  ramp — the requested **soft penumbra**, not a hard mask.
- **Gate falls out of the geometry** — no explicit rule: footprint **under-fills** the imaged FOV → dark
  edges; **over-fills** it → uniform. Exactly "shows dark edges if exist".

Dispatcher `three_d_scene_tools._compute_coupled_object_illumination_overlay_spec` now runs
samples → footprint map → true-scale projection, keeping the bugs/0286 rescale **only** as the fallback
for scenes with no computable paraxial conjugate. New `_object_surface_plane_z` gives the object plane in
the same cumulative-thickness frame the paraxial solve uses. Still render-only + cached (bugs/0166), still
gated on a live non-marker source (bugs/0280/0282), still never redefines the imaging conjugates (bugs/0266).

### No hardcoded value (the user's hard constraint)
object plane z ← rows; aperture radius ← object row; sensor half ← `_detector_target_half_extent`
(incl. the bugs/0276 vendor override); scale ← the scene's paraxial `|m|`; bins ← adaptive. The guard pins
this with a **scale-covariance** check: halving `|m|` halves the imaged patch. Nothing is tuned to a layout.
(`bugs/proto_bs_limiter_footprint.py` hardcodes teaching constants — it is a PROOF that the BS aperture is
the limiting stop, never the production path.)

## Measured result on the real vendor scene

| | before (0286) | after (0288) |
|---|---|---|
| object samples | 1738 launch events binned as object light | 1738 **DIRECT** (on-plane), 0 relayed |
| footprint on object | ±5 mm (the LED rectangle) | ±5 mm (unchanged — it *is* the illumination) |
| paraxial conjugate | unused | \|m\| = **0.5908** (sensor half 11.52 ↔ object half **19.50** = the 39 mm FOV) |
| drawn on sensor | ±5 mm **stretched** to fill ±11.52 mm | bright patch ≈ ±2.7 mm, rim **dark** |
| sensor area lit | ~34 % | **~7 %** |
| edge | full-sensor radial bowl | soft penumbra ring |

So the honest picture: **the added LED lights only a 10 mm spot on a 32.6 mm object.** The patch is
genuinely small — now it is *drawn* small, with a dark surround, instead of being stretched to fill the
sensor. To flood the FOV the user must enlarge or reposition the emitter.

**A faithful footprint on the real MV-150 shows no fold "dark edges"**: the 2-dark/2-uniform coaxial
pattern is a property of the *teaching* layout's compressed geometry (beam splitter close to the object,
illuminator sized to the FOV). On this vendor import there is no coaxial path at all (the flood is
absorbed at the cube's mechanical face). Dark edges appear only where a setup genuinely under-fills.

## Guard / phase
`KrakenOS/UI/validate_open3d_illumination_footprint_projection.py` (`run_checks()`, display-free) = penta
**phase 253**, baseline `253: pass`:
TERMINAL RAY tiers · SAMPLES (on-plane DIRECT kept, off-plane launch rejected, relay lands geometrically,
absorb/backward/blow-up/off-aperture dropped) · BILINEAR penumbra sampler (exact at bin centres, 0 outside,
monotone ramp) · PROJECTION (patch = footprint×|m|, rim dark, soft not hard, over-fill uniform,
|m|-scale-covariant, degenerate → None, footprint imaged off-sensor → None) · FOOTPRINT MAP · WIRING
(render-only) · REAL VENDOR SCENE (DIRECT-only, |m|≈0.59, patch lights <25 % of the 23 mm sensor).

Phase 252's dispatcher **contract** was updated to pin the new pipeline (it named the old functions).
All 19 illumination/coupling guards pass.

## Probes
- `diag_0288_footprint_linchpin.py` — the conjugate + why the naive relay fails.
- `diag_0288_relay_probe.py` — isolated trace → real polylines; proves the coaxial flood is absorbed.
- `diag_0286_led_placement_probe.py` — the flagged scene end-to-end through the production overlay.
- `diag_0286_flood_path_probe.py` — the trace-order wall (min z 202.2, 0 rays below z=100).

## In-app eyeball owed
Load `attachment/machine_vision_150mm_test.py`, add an Illumination LED, switch on the illumination
heatmap: expect a **small bright patch in the middle of a dark sensor** (≈5.9 mm across on the 23 mm
sensor), soft-edged — not a full-sensor radial bowl.
