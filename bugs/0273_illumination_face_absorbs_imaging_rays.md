# 0273 — an illumination-marked face ABSORBS imaging rays (drop the reflection-arm Image/detector)

User flag `flag_20260709_075456_691` on the MV-150 coaxial-LED scene, two parts:

> *"Not sure the illuminating ray is correct, please check. Also, the Image Plane and detector shows up again
> in Imaging Reflecting Arm (although that surface already promoted to Illumination surface)."*

## Part 1 — the illuminating ray IS correct (no code change)

Verified headlessly on the promoted BK7 prism (the +X face marked illumination-inward). The emission:

* launches **into** the solid — `launch · outward_normal = −1.000` for the default `aim="inward"` (bugs/0269),
  `+1.000` for `aim="outward"`; the aim control is honoured;
* **reflects** off the internal beam-splitter diagonal (each drawn polyline is ≥3 vertices), and
* **exits** the solid toward the object (drawn span 540 mm ≫ the 50 mm cube on the inward aim, bugs/0272).

What the user sees is the honest **full-surface source emission** — the whole marked face floods (bugs/0271
area-matched disk), so it renders as a broad fan, not a focused beam. That is source physics, not a defect.
It is NOT yet the through-object illumination *coupling* onto the detector (that is Stage 3, still to come).

## Part 2 — root cause: an Illumination face is a scene marker, so it kept its optical behaviour

"Illumination Source" is **not** a coating / face-function. Selecting it in the Face Editor binds a
scene-level `SceneSource3D` marker to the face (keyed `face_anchor_row` / `face_anchor_face_id` /
`face_anchor_aim`, bugs/0264/0268) — **disjoint** from the `OpticalSolidFaces` face-function metadata. So the
marked face KEEPS its beam-splitter optical behaviour in the **imaging** trace: the reflection arm still
traces through it and `derive_branch_detectors` spawns a phantom branch detector / Image Plane on that arm
(bugs/0088, row-base 100000). The user's directive: the reflection-arm sensor is dropped only when the face
is **Absorption**; an Illumination face is the opaque LED emitter plate, so it must drop the same way.

## Fix — the marked face absorbs imaging rays (display follows physics)

The illumination face is physically backed by the **opaque LED plate**, so imaging rays hitting it are
**blocked**. Rather than a display-only branch-drop (which would let the reflection rays escape unbounded —
the branch detector doubles as a ray hard-stop), we model the block and let the existing machinery drop the
detector:

* **build resolver** (`services/analysis_compute_workflow._serializable_specs_for_rows`) — resolves the
  face-bound illumination markers onto the row spec as `illumination_block_face_ids` (via the new
  `_illumination_block_face_ids_by_row`, which reads `layout_scene_source_specs`, physical + enabled markers
  only).
* **cache signature** (`services/row_spec_contracts._row_specs_signature`) — now keys on
  `illumination_block_face_ids`. **Without this the fix silently no-ops**: marking a face left the signature
  unchanged, so `build_system` returned a *stale* cached system built before the marker (the same
  cache-fingerprint footgun as bugs/0267).
* **build** (`layout_editor._build_system_from_specs`) — stashes `surface.OpticalSolidFaceIlluminationBlock`
  (a frozenset of the marked face ids) on the beam-splitter surface.
* **interaction hook** (`KrakenSys.__OpticalSolidFaceInteraction`) — a ray onto a marked face gets
  `override["force_absorption"] = True`, which hits the **same** absorb terminal event as an
  `Absorber/Mechanical` face (`__NsTraceTerminalEvent`, `interaction_type="absorb"`). The absorbed reflection
  leaf then feeds the existing bugs/0108 chain (`_leaf_fully_absorbed` → `derive_branch_detectors` drops the
  phantom detector/Image Plane). The transmit arm (through the lens to the real detector) is untouched.
* **emission suppression** (`services/three_d_scene_tools._compute_illumination_marker_rays_overlay_spec`) —
  the isolated emission pass (bugs/0272) sets `system._suppress_illumination_face_absorption = True` around
  its trace, so the flood does **not** self-absorb at launch. Physically: the LED plate EMITS in the emission
  pass and ABSORBS imaging rays in the imaging pass.

## Verification

* `bugs/repro_0273.py` — the quick repro: row spec carries `illumination_block_face_ids`; the surface attr is
  stashed; the marked face forces absorption (an unmarked reflecting face does not); the suppress flag
  disables it; the emission still exits (540 mm ≫ 50 mm, bugs/0272 intact).
* Guard `validate_open3d_illumination_face_imaging_absorb` (phase **240**): WIRING (the cache signature keys
  on the new spec — else stale-cache no-op; the interaction hook keys on the block AND honours the suppress
  flag; the emission overlay sets the flag) + BINDING (real promoted face: spec + surface attr set; marked
  face forces absorption while an unmarked reflecting face does not; suppress flag disables it; a real absorb
  terminal event drops the reflection branch detector — with a live-arm control proving the drop is the
  absorb, not a vacuous harness; emission still exits). Baseline updated in place (240 → pass). The absorbed
  reflect-arm → 0-branch-detector drop is itself already guarded by
  `validate_open3d_beam_splitter_branch_detectors` case 3b (bugs/0108).

## Notes

* **In-app eyeball owed:** headless can't reproduce the exact MV-150 embedded-VTK scene. The user should
  reopen the coaxial scene, mark the BS illumination face, and confirm the "Image (via BS)" plane + detector
  no longer appear on the reflecting arm (the transmit-arm detector stays). Requires an app restart to pick up
  the fix.
* **Unblocks Stage 3 (0274 — Option-B coupling):** the marked face now correctly EMITS (emission pass) and is
  OPAQUE to imaging (imaging pass); the next step traces the emission through the Object scatter (bugs/0271)
  onto the detector, irradiance-weighted.
* Still deferred (bugs/0270): the emission footprint is an area-matched **disk** that over-sizes a rectangular
  face; per-face scatter params dialog.
