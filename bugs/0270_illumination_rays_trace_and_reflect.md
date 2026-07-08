# 0270 — the face illumination emission is TRACED and REFLECTS (not stubs)

User flag `flag_20260708_204136_690` (testing the illumination arc):

> *"The rays do not respect physics, they don't reflect!"*

bugs/0267 drew the face illumination emission as **straight stubs** (origin → launch-direction segment), a
simplification I chose after a mid-system face source appeared to "Stop @ S0". The user (correctly) expects
the illumination to be **real traced rays that reflect** through the scene, and picked "real traced
illumination" over the stub patches.

## Root cause of my stub detour — a bare-scene artifact

The "Stop @ S0" that pushed me to stubs was **not fundamental**. Verified: in a genuinely non-sequential scene
(a solid with reflecting faces), a mid-system face source **traces and reflects** — 400 marker rays produced
3-segment paths, 48 reflecting off surfaces, only 26 hitting S0. My earlier failing test used a **bare prism
with all-Uncoated faces** (no non-seq surfaces), so the launch collapsed at S0. The coaxial LED (a working
non-seq source) sits at the front and traces fine; the marker just needed a real non-seq scene, which the
user's beam-splitter provides.

(Also cleared up: the force-non-seq flag DID work — inside the trace **service**, `self.editor` resolves to
the app, unlike the editor's own `.editor` attribute which is None in headless.)

## Fix — revert the stubs to the isolated traced path

The emission overlay now traces the marker into a **separate keeper** (forced non-sequential) and draws each
ray's full traced polyline (origin + every surface hit), so the rays reflect:

* `_compute_illumination_marker_rays_overlay_spec(system, wavelength)` (`services/three_d_scene_tools.py`) —
  builds the marker bundles, `Kos.raykeeper(system)`, sets `_force_nonseq_preview_trace` around
  `_trace_preview_bundles`, extracts records via `_isolated_ray_analysis_records`, and builds the overlay.
  Guarded against the async capture/replay window (bugs/0223).
* `_isolated_ray_analysis_records` (`services/analysis_reports.py`) — restored: builds the record set for the
  isolated trace WITHOUT writing `self._last_scene_bundle`, so the imaging image-plane / detector / optical
  axis stay fixed on the object-driven trace (**bugs/0266 preserved even though the marker now traces**).
* `_force_nonseq_preview_trace` override (`services/trace_preview.py`) — restored: forces NsTraceLoop for the
  isolated marker trace (a sequential launch stops mid-system sources at S0).
* `build_illumination_marker_rays_overlay(records, ...)` (`services/source_illumination_rays_overlay.py`) —
  back to record-based: one emission-coloured polyline per ray (origin + hits), axis-agnostic span gate so a
  face emitting along any axis is kept and only source-aperture collapses are dropped.

## Verification

* Guard `validate_open3d_illumination_marker_emission` (phase **236**, updated in place — same title, baseline
  unchanged): WIRING now asserts the compute traces in ISOLATION (`_trace_preview_bundles` + `raykeeper` +
  `_isolated_ray_analysis_records` + the force-non-seq flag) and does NOT use the mutating
  `_ray_analysis_records_for_trace` or write `_last_scene_bundle`; BINDING (real promoted prism with reflecting
  faces + a marked face aimed inward) asserts the traced emission is drawable, **REFLECTS** (≥1 polyline with
  >2 vertices), and leaves `last_rays` / `_last_scene_bundle` untouched. Siblings 0266/0268/0269 + the coaxial
  0259 overlay re-verified — no regression.

## Deliberately deferred (noted to the user)

* **Footprint** — the emission is still an area-matched **disk** (`optical_solid_face_effective_radius_mm`), so
  it over-sizes a rectangular face at the corners ("the illumination source area is bigger than the launching
  Cube surface"). Sizing to the true face u/v rectangle needs the promoted-solid mesh extents — next refinement.
* **Branch-sensor suppression** — an illumination-marked face should terminate imaging rays so the
  beam-splitter reflection branch drops its sensor (like an Absorber). Independent of this trace; a focused
  follow-up (needs the system-build absorb hook).
* **In-app eyeball owed** — with 0269 (direction) + 0270 (reflection), the marked face should flood emission
  INTO the BS and the rays should reflect off the diagonal. Requires an app restart to pick up 0269 + 0270.
