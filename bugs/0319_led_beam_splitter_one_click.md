# 0319 — One-click "Add Beam Splitter to LED" (parametric cube / plate)

## Request
Follow-up to the 0317/0318 LED work, from the user: a one-click way to drop a beam
splitter onto an imported LED module and have it end up as a real non-sequential
optical element — "clone-and-resize a template ... centered to the Clear Aperture
Opening of the LED STEP." Context: the LED module is *"an array of small LEDs located
at one side ... probably with a diffuser in front of it."*

The command generates a parametric BS (cube or plate), overlays it on the imported
LED STEP, centers it on the LED clear-aperture opening, glues it to the LED, and
promotes it to a non-sequential optical element — reusing the existing overlay →
center → glue → promote pipeline.

## User decisions (2026-07-15)
1. **Auto-flag the diagonal as the BS coating on promote** — *"No harm to auto-flag
   since it is a BS anyway."* (Overrides the usual promote-default-Uncoated rule for
   this command's diagonal face only.)
2. **Centering: auto-detect the LED opening WITH a manual fallback** — *"Auto-detect
   is good but not sure how reliable, give user manual option also or a fallback to let
   user select manually."* The existing manual clear-aperture pick
   (`STEP_CLEAR_APERTURE_PICK`, bugs/0134) is the fallback.
   - **Domain fact (non-obvious):** an LED STEP that carries a BS *always* has **two**
     clear-aperture openings — auto-detect must find both and pick/choose one; the
     manual fallback resolves the ambiguity.
3. **Regenerable cache** — *"Cache is OK as long as user can re-generate in case the
   cache not found."* Generate **parametrically**, not from `attachment/prisms/*`
   (those vendor STEPs are gitignored → absent on a fresh clone). Cache under
   `attachment/cad_cache/` (gitignored, Filen-synced) and **regenerate from parameters
   when the cache is missing**.

## Pipeline (reuses existing APIs)
```
generate BS solid (parametric OCC)
  → set as the "optical" overlay          (import_optical_step, path= bypass)
  → set clear aperture on the LED opening  (auto-detect ▸ manual STEP_CLEAR_APERTURE_PICK fallback)
  → center_clear_aperture_on_optical_axis("led")
  → set_optical_led_glue(True)             (BS↔LED glue = the "optical"+"led" label pair)
  → promote_imported_step_to_optical_solid_row("optical")  + auto-flag the 45° diagonal coating
```

## Shipped this pass — Component 1: the parametric BS generator (verified)
`KrakenOS/UI/services/beam_splitter_factory.py` — pure-geometry, display-free,
in-process (pythonocc-core), the only part fully verifiable without a GLX display.

- **cube** = two cemented right-angle prisms sharing a **real** 45° diagonal
  hypotenuse face. The XZ square is split by the diagonal `X = Z` into two right
  triangles, each extruded along +Y into a prism; the compound of the two solids
  keeps the diagonal as a genuine face. *A plain `BRepPrimAPI_MakeBox` has no
  diagonal* — and the resize/coupling detector (`detect_coupling_from_faces`) plus
  the auto-flag-the-coating promote step both expect that face.
- **plate** = a thin `(w × h × t)` box centered at the origin, rotated 45° about +Y
  so its large-face normal folds the Z beam.
- Canonical output: origin-centered, optical axis = +Z, coating plane at 45°.
  The returned `BeamSplitterSolid` carries the coating normal/point + bbox so the
  orchestration can place, glue, and auto-flag without re-reading the STEP.
- Cache: `attachment/cad_cache/beam_splitter_templates/bs_<kind>_<digest>.step`,
  keyed on kind + rounded params, **regenerated when missing** (mirrors bugs/0021).
- Parameter guards: non-positive side, a plate as thick as its face, or a tilt
  outside (0°, 90°) all raise `ValueError`.

### Verified (display-free)
`KrakenOS/UI/validate_open3d_beam_splitter_factory.py` — **PASS**:
- **A** metadata math (OCC-free): cube + plate coating normals are 45° to +Z; the
  canonical solids are origin-centered; bad parameters raise.
- **B** the written cube STEP re-reads to **≥ 2 solids** with a genuine planar face
  **~45° to +Z** (the coating diagonal) — the load-bearing "not a plain box" check.
- **C** the plate STEP has a large face **~45° to +Z**.
- **D** a present cache is reused (`regenerated=False`); deleting it and calling
  again **regenerates** the STEP (`regenerated=True`).
- **E** the returned `coating_normal` matches a real face in the written STEP.

Penta **phase 281** (`phase_281_beam_splitter_factory`) delegates to the guard;
baseline updated (`"281": "pass"`).

## Remaining — need the user's in-app eyeball (no GLX render on this box)
- **C2 — LED clear-aperture auto-detect** (find the two openings) + wire the manual
  `STEP_CLEAR_APERTURE_PICK` fallback. Reliability is exactly what the user was unsure
  about; the manual pick is the dependable path.
- **C3 — orchestration** `add_beam_splitter_to_led(kind="cube"|"plate")`: run the
  pipeline above end-to-end + auto-flag the 45° diagonal as the coating on promote.
- **C4 — menu wiring** "Add Beam Splitter to LED ▸ Cube / Plate" in
  `append_element_context_actions` (open3d_face_assignment.py).
- **In-app eyeball owed:** that the generated BS *looks* right, centers on the LED
  opening, glues, folds, and promotes correctly on the real LED module
  (`attachment/LED/OPT-CO90-X-V1.6.2-H.STEP`). The generator's geometry is verified;
  its *placement* on a real LED is a visual check I cannot make here.

## Files
- `KrakenOS/UI/services/beam_splitter_factory.py` — parametric cube/plate generator + cache.
- `KrakenOS/UI/validate_open3d_beam_splitter_factory.py` — display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_281`.
- `tools/penta_validator_baseline.json` — phase 281 baseline + title.
