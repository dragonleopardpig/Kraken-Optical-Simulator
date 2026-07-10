# 0289 — Side-LED illumination: generalize the footprint pipeline + the honest physics answer

STATUS: **SHIPPED** (guard = the phase-253 `validate_open3d_illumination_footprint_projection`, updated
in place; baseline unchanged). Follow-up to 0288, driven by the user's question: *"Can I have a full
55x74 LED attach to the side of the BS and see the effects on the detector? I expect 2 side dark edges
(perhaps slightly)."* Also answers `flag_20260710_203703_468` ("detector hit map") and
`flag_20260710_205215_159` ("rays. … why the purple rays stop at BS").

## The two flags

- **203703 "detector hit map"** — the Normal-to-Sensor view of the 0288 overlay: a small soft-edged
  bright patch centred on a dark 23 mm sensor. **Correct**: the added LED is a 10×10 mm emitter ON the
  object plane; at |m| = 0.5908 it images to a ≈5.9 mm patch. The render matches the headless numbers
  (patch lights ~7 % of the sensor, soft penumbra, dark rim).
- **205215 "why do the purple rays stop at the BS"** — the purple bundle is the beam-splitter REFLECT
  arm of the illumination flood. Off the 45° diagonal it heads +x, straight into the cube's +x face,
  which the vendor STEP authors as **Absorber/Mechanical** (it models the opaque LED module mounted
  there — the bugs/0273 opaque-plate model). Absorbed ⇒ the rays terminate at the face. Working as
  authored; the same face is why light cannot ENTER from that side either (scenario A below).

## The experiment (headless, production pipeline: `bugs/diag_0289_side_led_probe.py`)

55×74 mm LED (`radius_x=37→y`, `radius_y=27.5→z`, the rectangle-source transverse mapping for aim
(−1,0,0)), 1 mm off the cube's +x face, 30° cone, 24 000 rays, real vendor scene:

| scenario | result |
|---|---|
| **A** face as authored (Absorber) | flood eaten at the face (23 861/24 000 absorb) → overlay **None** (honest blank) |
| **B** face flipped to Transmit | flood refracts in, folds down off the diagonal, exits to the object; relay lands 35 788 rays; footprint fills the clip window → **UNIFORM** (fold 1.09 / perp 1.05, corners 0.995 — noise around 1.0) |
| **C** B + a 30×78 aperture row 5 mm under the cube | **identical to B** — the inserted stop is never consulted (see engine limitation) |

**Physics of B (why UNIFORM is the correct answer, not a bug):** with the LED mounted AT the cube and
nothing between the cube and the object 202 mm below, EVERY point of the imaged 39×39 FOV sees the
WHOLE 55×74 LED — the acceptance window never slides off the emitter, so the irradiance varies only by
obliquity (~1 %). The 2-sided fold-dark edges of the real 25 MP image require a fold-axis LIMITING
APERTURE between the LED and the object (the ~30 mm illuminator window `machine_vision_150mm_coaxial_led.py`
models as its 30×78 exit stop — its acceptance clipping is what phase 175 verifies). Bare LED → uniform;
LED behind an under-filling window → 2 dark edges. "Dark edges if they exist" — here they genuinely don't
until the window is modeled.

**Engine limitation found by scenario C (documented, not fixed):** an aperture row inserted after the
cube (row index above, `desp_z` below) never vignettes the reflected flood — the SPLIT-BRANCH rays are
carried by the branching tracer against targets/hard-stops and do not re-scan later sequential rows
(the same family as the bugs/0287 trace-order wall; 330 stray hits vs ~36 000 crossings, zero
`aperture_stop_vignette` terminations). So reproducing the real illuminator's window on the vendor
import needs either an engine extension (branch rays honouring `IsApertureStop` surfaces) or the
window modeled as part of the solid itself. The teaching layout remains the working model of the
mechanism (sequential-index path: LED(0)→stop(1)→FOV(2)).

## Production fixes shipped here (all general, no scene constants)

1. **Imaged-FOV clip** (`_compute_coupled_object_illumination_overlay_spec` → `clip_radius`,
   `object_plane_illumination_samples`): samples clip to `1.3 × hypot(sensor_half_w, sensor_half_h)/|m|`
   — the imaged FOV — falling back to the object row radius only without a conjugate. The row's 32.6 mm
   disc is SMALLER than the 39 mm square the lens images (a drawing/launch extent, not a baffle);
   clipping there erased real in-FOV light and would have carved a fabricated radial rim onto any large
   footprint (the exact 4-sided-dark trap of the 0280/0282 saga). The 1.3 pad keeps binned data past
   the projection window so the boundary bin isn't half-filled (no fake dark rim on an over-filling
   flood); light entirely off-window (the 0286 marked-face ring) still dies at the projection's
   peak gate.
2. **Free-flight relay whitelist** (`_FREE_FLIGHT_TERMINATIONS`): only rays whose trace ended in free
   flight (`no_next_intersection`, `missed_image`, `miss`, `escape`, …) may be geometrically relayed.
   A ray that ended ON something — `absorb`, the bugs/0179 `aperture_stop_vignette`, hard-stop
   `target_termination`, `detector` — deposited its light there; extending it would shine through the
   blocker. (Replaces the absorb-only blacklist.)
3. **Isolated re-trace for launched sources** (`_isolated_scene_source_records`, wired into
   `_coupled_object_illumination_records`): same bundles + seeds as the preview, traced into an
   isolated keeper so records carry `traced_polyline_world`. The relay needs the true POST-EXIT
   direction: a hits-only last segment for a flood refracting out of a solid is the IN-GLASS leg,
   which under-spreads the exit cone by ~n. Falls back to the preview records during the bugs/0223
   async window or on failure. Never touches `_last_scene_bundle` (bugs/0266).
4. **Sensor-anchor preference order** (`_source_illumination_anchor_target` +
   `_imaging_detector_row_anchor_target`): (1) the analysis-target match only if it IS a detector
   (under "Auto" with a no-reach flood it resolved to the OBJECT row — the heatmap then binned the
   LED's own launch events into a stripe map); (2) non-parked detectors by RESOLVED dims (own or the
   bugs/0276 vendor override — a dim-less stub never outranks the real sensor); (3) a SYNTHESIZED
   Image-row anchor when its dims resolve — the sensor pose is an imaging property (bugs/0266), so a
   flood with no reached arm still drapes the heatmap at the true sensor plane (z≈657), not on a
   bugs/0285 default-distance park beside the cube; (4) dimmed parks as the legacy fallback (the
   phase-241 scatter fixture's parks carry the real 39×39 dims while its Image row carries none);
   (5) the flat best-focus anchor.
5. **Density gate counts in-window hits** (`_compute_detector_density_illumination_overlay_spec`):
   the ≥50-hits gate now counts hits INSIDE the drawn window. A 24 k-ray side flood leaks ~0.3 %
   strays; gating on the raw count let those bin a garbage density map that shadowed the honest
   coupled projection.

## The user's in-app recipe (side-LED test)

1. Face Editor on the BS cube → face **S001/F002** (+x) → function **Transmit / Port** (the LED
   shines through its own window; leave it Absorber and the flood is eaten — scenario A).
2. Source panel: origin `(28.6, 0, 229.646)`, direction `(−1, 0, 0)`, radius `27.5`, cone `30°` →
   browser → **Add Illumination Source (LED)** (mints a square 55×55 at that pose; the exact 74 mm
   perp half needs the pending scene-source RESIZE feature — the fold axis behaves identically).
3. Overlays → illumination heatmap → expect **UNIFORM** (the honest bare-LED answer), drawn at the
   real 23×23 sensor.

## Guard / phase
`validate_open3d_illumination_footprint_projection` (phase **253**, updated in place, baseline
unchanged): + imaged-FOV clip override kept/bounded; + free-flight whitelist (absorb / vignette /
hard-stop / detector all refused relay); + WIRING pins for `clip_radius`, the isolated re-trace, the
anchor ranking, and the in-window density gate. Full 19-guard illumination sweep green.

## Open follow-ups
- Model the real illuminator's fold-axis window on the vendor scene (needs the branch-vignette engine
  extension above, or window-as-solid). Ask the user for the module's real window dims if they want
  the 2 dark edges reproduced on the vendor import.
- Scene-source MOVE + RESIZE UI (the roadmap items the flags keep re-hitting) — resize would give the
  exact 55×74 from the panel.
