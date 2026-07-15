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

## Shipped this pass — Components 2–4 (the rest of the pipeline)

### C2 — LED clear-aperture auto-detect (+ manual fallback)
`KrakenOS/UI/services/led_clear_aperture_detect.py` — pure-geometry (no OCC, no editor)
scorer for the opening signature: a planar, axis-aligned, window-sized face that is a
**rim around a hole** (`bbox_fill = area / (span_a·span_b)` low, ~0.15, vs ~1.0 for a
solid panel). Ranks every qualifier (square outranks rectangular), so an LED that
already carries a BS (two openings) and the bare illuminator (one) are both handled.
- Grounded on the real `OPT-CO90-X-V1.6.2-H.STEP`: the object-facing square window
  **F112** is the clear #1 candidate (score 0.933, squareness 1.0, fill 0.15).
- Service side (`scene_placement_commands.py`): `auto_detect_step_clear_aperture_candidates(label)`
  reads the overlay's analytic B-rep faces, scores them, and **verifies** each analytic
  enumeration index still resolves cleanly on the displayed *selection* mesh (an
  axisymmetric-grouped face would collapse to a larger cluster → area mismatch → dropped),
  so the returned `face_index` is exactly what `set_step_clear_aperture` consumes.
  `auto_set_step_clear_aperture(label)` persists the best; **`[]`/None falls back to the
  manual `STEP_CLEAR_APERTURE_PICK`** — the dependable path the user asked for.

### C3 — orchestration `add_beam_splitter_to_led(kind)`
`scene_placement_commands.py` — runs the whole pipeline:
generate BS sized to the opening span → `import_optical_step(path=…)` (new programmatic
bypass, mirrors `import_camera_step`) → `set_step_clear_aperture("led", opening)` →
`center_clear_aperture_on_optical_axis("led")` (opening → `(0,0,z)` on the global axis) →
place the origin-centred BS at that on-axis opening centre → `set_optical_led_glue(True)` →
`promote_imported_step_to_optical_solid_row("optical", clear_overlay=True)` →
`_flag_beam_splitter_coating_face(row)` marks the largest ~45° face
`Partial Reflecting / Transmitting` (decision 1). Unknown kind / missing LED / no opening
all stop gracefully with a status line (glue survives promotion, bugs/0127).

### C4 — menu wiring
`open3d_face_assignment.py` — the LED overlay's right-click / tree menu gains
**"Add Beam Splitter to LED ▸ Cube / Plate"** (`_add_beam_splitter_to_led_from_context`).

### Verified (display-free)
- `validate_open3d_led_clear_aperture_detect.py` — **PASS** (pure scorer ranks two rim
  windows + rejects panel/sliver/wall/thick face; real LED top candidate = F112, score 0.933).
- `validate_open3d_led_beam_splitter_orchestration.py` — **PASS** (spy editor: the pipeline
  fires generate→overlay→centre→place→glue→promote→coat *in order* with the right args;
  BS sized to the opening; coating on the biggest 45° face, never a plain box; graceful stops).
- Penta **phase 282** (`phase_282_led_clear_aperture_detect`) + **phase 283**
  (`phase_283_led_beam_splitter_orchestration`); baseline updated (`"282"/"283": "pass"`).

## Remaining — in-app eyeball owed (no GLX render on this box)
The generator, detector, and orchestration wiring are all verified display-free. What I
**cannot** check here is the *visual result on the real LED module*: that the BS looks
right, lands centred on the LED clear-aperture opening, glues, folds the beam, and
promotes correctly on `attachment/LED/OPT-CO90-X-V1.6.2-H.STEP`. Size defaults to the
opening's smaller in-plane span (user-resizable); the exact size/seat is an eyeball call.

## Files
- `KrakenOS/UI/services/beam_splitter_factory.py` — parametric cube/plate generator + cache (C1).
- `KrakenOS/UI/services/led_clear_aperture_detect.py` — pure clear-aperture opening scorer (C2).
- `KrakenOS/UI/services/scene_placement_commands.py` — auto-detect service + `add_beam_splitter_to_led` (C2/C3).
- `KrakenOS/UI/services/step_overlay_import.py` — `import_optical_step(path=)` bypass (C3).
- `KrakenOS/UI/services/open3d_face_assignment.py` — the "Add Beam Splitter to LED" menu (C4).
- `KrakenOS/UI/validate_open3d_beam_splitter_factory.py` — C1 guard (`phase_281`).
- `KrakenOS/UI/validate_open3d_led_clear_aperture_detect.py` — C2 guard (`phase_282`).
- `KrakenOS/UI/validate_open3d_led_beam_splitter_orchestration.py` — C3 guard (`phase_283`).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_281`–`phase_283`.
- `tools/penta_validator_baseline.json` — phases 281–283 baseline + titles.
