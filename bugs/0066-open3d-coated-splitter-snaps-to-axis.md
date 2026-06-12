# 0066 — Open 3D: a coated beam-splitter snaps onto the optical axis after the Face Editor

## Symptom (user's words)

From the in-app repro bundle `attachment/recorded_bug_repros/flag_20260612_091552_059`:

> after face editor, the beam spliiter auto sanp to optical axis (should not be),
> and there are still some wiered thickness overlays shown.

The user parked a promoted beam-splitter cube **off to the side** of the optical
axis and assigned it a `Beam Splitter` coating in the Face Editor. After the
editor refresh the cube **jumped back onto the `X=0, Y=0` optical axis** instead
of staying where it was placed, and several thickness-dimension arrows were left
floating in odd, disconnected positions.

The recorded `scene_state` confirms the snap: row 6 (the cube) draws at
`X[-39, 39] Y[-38.98, 38.98] Z[556.6, 635.0]` — a ~78 mm cube centred exactly on
the axis — while `thickness_dimension_count = 14` and the capture flags one
`stray_props_above_body` at `X[82.8, 102.8] Y[52.2, 68.9] Z[399.3, 411.5]`,
floating up and to the side of the optics.

## Root cause

This is a **metadata-schema mismatch in the off-beam coating check** shipped with
bugs/0065. `offbeam_optical_solid.solid_has_active_coating` decided whether a
promoted solid is "coated" (Mirror / TIR / Beam Splitter / Absorber → stays in
the non-sequential trace) by reading the face list directly:

```python
faces = advanced.get("OpticalSolidFaces")
if not isinstance(faces, (list, tuple)):
    return False          # <-- real metadata is a dict, so we bail here
for face in faces:
    ...
```

But the **persisted** `OpticalSolidFaces` is a *dict*, not a bare list:

```python
{'version': 1, 'source_stl': '…', 'faces': [ {…}, … ], 'virtual_planes': []}
```

(`attachment/machine_vision_150mm_measured_test.py` row 6 is exactly this — its
`F001` face is a real `Beam Splitter`.) The `isinstance(faces, (list, tuple))`
guard is therefore **always false for real data**, so `solid_has_active_coating`
reported every genuinely-coated solid as **uncoated**.

Consequences, both flowing from that one wrong boolean:

1. **Snap to axis + dropped from the trace.** An uncoated-looking splitter is
   eligible for off-beam neutralization. Parked far enough off the beam, the
   builder swaps it for a flat zero-power AIR surface with `desp` **zeroed**
   (bugs/0065's `neutralize_offbeam_inert_solids`). The on-axis built surface
   then drives `TRANS_2A` / `EEE`, so the 3-D body is drawn at `X=0` — the snap.
   Worse, the **beam splitter is removed from the non-sequential trace** even
   though a Beam Splitter must always stay non-sequential (North Star): it stops
   splitting the beam.
2. **Weird thickness overlays.** The scene is rebuilt each refresh
   (`RemoveAllViewProps()` — no stale-actor leak), and every thickness dimension
   is recomputed from the surfaces' world reference points. With the body
   snapped onto the axis while the user's geometry was off-axis, the lens↔cube↔
   image span arrows were drawn against a displaced body and read as disconnected
   "floating" overlays.

**Why bugs/0065 didn't catch it:** the guard's `_COATED` / `_UNCOATED` fixtures
use a *bare list* for `OpticalSolidFaces`, which the buggy `isinstance` check
happens to read correctly. The real promote pipeline writes the dict schema, so
the fixture masked the production bug.

## Fix (files + lines)

`KrakenOS/UI/services/offbeam_optical_solid.py` — `solid_has_active_coating` now
reads through `normalize_optical_solid_face_metadata` (the same normalizer the
rest of the optical-solid code already uses), which accepts either the dict
`{"faces": […]}` schema **or** a bare list and returns a canonical
`{"faces": […]}`:

```python
metadata = normalize_optical_solid_face_metadata(advanced.get("OpticalSolidFaces"))
for face in metadata.get("faces", []) or []:
    ...
```

A real Beam-Splitter cube now reports `solid_has_active_coating == True`, so
`is_offbeam_inert_solid_spec` returns `False` at every off-beam distance: the
splitter keeps its `desp` coordinate break in the prescription (stays in the
non-sequential trace) and its body is placed by `TRANS_2A` at the true off-axis
station instead of snapping onto the axis. `normalize_optical_solid_face_metadata`
lives in `optical_solid_metadata.py` (imports only `numpy`), so there is no
import cycle through the `_build_system_from_specs` hot path.

The thickness overlays (symptom 2) are a **downstream visual consequence**: with
the cube restored to its true station the dimension arrows are recomputed against
the correct body, so the disconnected overlays resolve. No stale-actor leak is
involved (the renderer is fully cleared each refresh), so no dimension-service
change is made; the corrected overlays are confirmable only in-app.

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_coated_solid_schema_exempt.py` (new, display-free).
It exercises the real persisted **dict** schema (the case the old fixture
missed), the bare-list schema (backward-compat), and the live machine-vision
prescription row 6:

* **A** — `solid_has_active_coating` is `True` for a dict-schema Beam-Splitter
  solid, `True` for a bare-list one, and `False` when every face is uncoated.
* **B (killer)** — a dict-schema Beam-Splitter cube pushed far off the beam
  (`desp_x = −90, −120`) is **not** classified off-beam inert and is **not**
  neutralized: its `surface.DespX` coordinate break survives
  `_build_system_from_specs`, proving the body stays off-axis and the splitter
  stays in the trace. Stubbing the normalizer back to the bare-`isinstance`
  read fails B (the cube is neutralized and `DespX` collapses to 0).
* **C** — the real `attachment/machine_vision_150mm_measured_test.py` row 6 reads
  as coated (skips cleanly if the fixture is absent).

`KrakenOS/UI/validate_open3d_offbeam_solid_display_only.py` (bugs/0065) gains a
dict-schema check (`A2b`) so the fixture gap that hid this bug is closed
permanently.

## Integrated

Phase 71 of `validate_open3d_penta_telescope_comprehensive.py` (display-free
wrapper over the new guard). Baseline `tools/penta_validator_baseline.json`
updated (`"71": "pass"`).

## Verification note

The live render / Face-Editor refresh cannot be confirmed headless (this layout
class SIGSEGVs the offscreen Xvfb llvmpipe renderer). The fix is pinned by the
display-free classifier + `_build_system_from_specs` prescription guard above
(which proves the coated splitter is never neutralized and keeps its off-axis
coordinate break); the user confirms the body staying put and the overlays
clearing in-app.
