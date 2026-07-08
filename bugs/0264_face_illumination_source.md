# 0264 — mark a CAD/STL face as an illumination source (Feature B, the 0263 follow-up)

0263 made the "Illum rays" overlay robust (it no longer collapses to `None` when the source role isn't
the literal `"illumination"` tag). But 0263's NOTES flagged the deeper ergonomic gap: **a user has no
first-class way to *mark* a face as the emitter**, so `source_role="illumination"` only ever got attached
by a pre-built layout (`machine_vision_150mm_coaxial_led.py`), never by the user's own scene. This change
closes that gap.

## Feature — right-click a face → "Set as Illumination Source"

Two entry points now create a real, face-anchored illumination emitter:

* **Open 3D right-click** — `services/open3d_face_assignment.py`: the CAD/STL face context menu offers
  **"Set as Illumination Source"** (`_assign_row_face_illumination_from_context`). If the picked face isn't
  yet an anchor it is first registered with the default face function, then bound.
* **Face-roles dialog** — `panels/main_optical_solid_face_roles_dialog.py`: a **"Set as Illumination
  Source"** footer button (`use_selected_face_as_illumination_source`), mirroring "Use Face As Source
  Target".

Both call the new editor method `create_illumination_source_at_face(row_index, face_id=…)`
(`services/source_modeling.py`), which builds a `SceneSource3D` spec:

* **origin** = the face centroid (`anchor_world` / `centroid_world`);
* **direction** = the **OUTWARD** face normal — `_outward_face_normal` flips the raw normal to point away
  from the solid-body centre (`_surface_reference_world_point(row)`), so the light leaves the surface;
* `role="illumination"`, `physical=True`, `enabled=True`, `model="Collimated disk source"` (minimal
  first-cut beam: `radius=2.0`, `cone_deg=20.0`, `ray_count=400`);
* tagged with the face anchor **`face_anchor_row`** (int) + **`face_anchor_face_id`** (str).

Re-marking the SAME face **updates the existing source in place** (matched on row+face_id) rather than
piling up duplicates.

## Tracking — the source follows the face on moves

`resync_face_bound_scene_sources()` walks the specs, and for each one carrying `face_anchor_row` refreshes
its origin/direction from the face's **live** world pose (`_surface_reference_world_point` /
`_surface_reference_world_normal` + the outward flip). It is geometry-only, history-free, mutates in place,
and is a **no-op when no source carries a face anchor** (the common case — it `continue`s past every spec
without the key and returns `False`).

The resync is injected at the **top of `_collect_layout_settings`**
(`services/layout_settings.py`) — the single choke point that packs `scene_sources` for **both** the
preview trace and the file save. So a bound source tracks its face automatically before every trace/save;
no caller has to remember to resync. (Wrapped in `try/except` and gated on `hasattr`, so it can never
break a snapshot.)

The anchor keys are flat scalars, so they survive `normalize_scene_source_specs`, ride into
`SceneSource3D.settings` via `scene_source_from_spec` (`settings = dict(spec)`, unread by the emitter
dispatch — harmless), and round-trip through `scene_sources_from_settings`. The result is exactly what
0259–0263 need: an **active, physical, `role="illumination"` emitter**, so the "Illum rays" overlay
(phase 232) now lights up for a **user-authored** scene.

## Verification (display-free)

* `KrakenOS/UI/validate_open3d_face_illumination_source.py` — new guard, two parts:
  * **WIRING** (pure source inspection): the editor exposes `create_illumination_source_at_face`,
    `resync_face_bound_scene_sources`, `_outward_face_normal`; `LayoutSettingsService._collect_layout_settings`
    calls the resync; the right-click menu offers the item and its handler calls create; the face-roles
    dialog offers the button.
  * **BINDING** (real promoted-prism STEP fixture `PRISM_42779_STEP`; **SKIPs** when the gitignored STEP
    isn't checked out): promote the prism, assign a face, create the source, and assert
    role/physical/enabled + anchor keys + origin==centroid + **unit OUTWARD** direction
    (`dot(dir, centroid−body) > 0`); re-marking updates in place (no duplicate); a **+10 Y row move is
    tracked by `_collect_layout_settings`** (proves the injection fires, not an explicit resync); the anchor
    keys survive normalization; and the settings round-trip yields an active physical illumination emitter.
  * Run: `OK binding OK: illum_face:1:S001/F001 @ S001/F001 tracks the face; emits as illumination` →
    `[PASS]`.

## Guard / baseline

* **Phase 233** (`phase_233_face_illumination_source`) in the comprehensive penta harness wraps the guard's
  `run_checks()`. Registered in the `phases` list and added to `tools/penta_validator_baseline.json`
  (233 → pass). All prior phases untouched: the resync is a verified no-op when no scene carries a
  face-anchored source, so no existing phase changes behaviour.

## Notes

* Minimal first cut by design: default disk beam (radius/cone/ray-count), no new beam-model dialog — the
  goal was the *authoring* path (mark a face → it emits + tracks), not a full emitter editor. A richer
  per-source beam UI is a later follow-up if wanted.
* **In-app eyeball owed**: headless can't drive the embedded-VTK right-click / dialog. The user should
  right-click a CAD/STL face → "Set as Illumination Source" (or use the dialog button), then confirm the
  "Illum rays" overlay lights up and the source follows the element when it's moved.
