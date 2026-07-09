# 0283 — scene sources are first-class Open 3D objects (glyph + browser + hide/unhide)

## Motivation (piece 1, increment 1 of 4)

The user asked to promote the **parametric scene source** — the "real emitting LED" that drives the
illumination trace behind the coaxial-LED heatmap (bugs/0259–0282) — into a first-class Open 3D object.
Their four requirements:

1. **Addable** from a menu ("Add Illumination Source (LED)").
2. **Shown in the Right Browser** with hide/unhide.
3. **Movable** to illuminate from other angles.
4. **Resizable.**

Until now a scene source existed only as a `layout_scene_source_specs` entry consumed by the trace — it
had **no presence in the viewport or the browser**, so it could not be seen, hidden, moved, or resized.
This increment (**0283**) lays the foundation: **draw each source as a 3D glyph** and give it a **"Scene
Sources" browser group with per-source hide/unhide**. The remaining increments follow: **0284** add
entry point, **0285** move gizmo, **0286** resize handles. Then piece 2 closes the
illumination→object→detector loop.

## What ships in 0283

### 1. Drawable descriptor enumerator (`services/source_modeling.py`)

`_drawable_scene_source_descriptors(wavelength=None) -> list[SceneSource3D]` normalizes
`layout_scene_source_specs` and yields **only the sources that should appear as objects**:

* **face-bound markers are excluded** — a marked CAD face (bugs/0264) is drawn *on its face*, and it is
  already excluded from the imaging trace (bugs/0266); it is not a free-standing emitter.
* **disabled sources are excluded** (`enabled == False`).
* each surviving spec is resolved through the existing `_scene_source_from_spec` into a `SceneSource3D`
  (origin / direction / settings / source_id / name).

Both the browser rows and the 3D glyphs consume this one enumerator, so the tree and the viewport stay
in lock-step by construction.

### 2. Source glyph (`open3d_inspector.py`)

`_add_scene_source_glyphs` iterates the descriptors and draws, per source, an **amber emitting-aperture
glyph** built from the source's own geometry:

* a **translucent aperture panel** — a rectangle sized `radius_x × radius_y` in the plane perpendicular
  to the emission direction (`_scene_source_glyph_basis` returns an orthonormal `(d, u, v)`; corners at
  `origin ± rx·u ± ry·v`);
* a **bright border loop** around that rectangle (wireframe);
* an **emission-direction arrow** from the origin along `d`, scaled to the aperture size.

Each actor is registered with `track_source_id=source_id` (a new `_add_mesh_actor` parameter that
mirrors `track_row_index`): it populates `_source_actor_map` / `_actor_source_map` for hide/unhide but
leaves the actor **non-pickable** — selection/picking is deferred to the move-gizmo increment (0285).

### 3. Browser group (`panels/open3d_step_admin.py`)

A new **"Scene Sources"** category (`CATEGORY_SPECS`) is populated from
`_scene_source_browser_rows()` (same descriptor enumerator). Each row uses a `source:<id>` iid.
Right-click → **Hide/Show** routes through `_resolve_iid_target` (now a 4-tuple
`(rows, label, display_key, source_id)`) and `_set_element_hidden(..., source_id=…)` to the inspector's
`set_source_hidden`. Hidden rows grey out via the existing `hidden` tag.

### 4. Visibility survives rebuilds (`open3d_inspector.py` + `services/open3d_scene_refresh.py`)

Actors are rebuilt on every scene refresh, so `_apply_scene_element_visibility` now re-hides any
`source_id` in `_hidden_source_ids` after each rebuild (the same pattern the row/step hides use). The
per-source actor maps are cleared alongside the other actor maps at the top of a refresh, and
`_add_scene_source_glyphs` is called unconditionally during the refresh (glyphs always draw; visibility
is applied afterward).

## Verification

New display-free guard `validate_open3d_scene_source_object` = penta phase **249**:

* **DESCRIPTORS** — from a spec list of {real LED, face-bound marker, disabled source} only the LED is
  returned, and it round-trips origin / direction / radius_x / radius_y from the spec.
* **BASIS** — `_scene_source_glyph_basis` returns an orthonormal `(d, u, v)` for three emission
  directions (u·d ≈ v·d ≈ u·v ≈ 0), so the aperture plane is perpendicular to the emission.
* **VISIBILITY** — `set_source_hidden(id, True)` makes the source's actors invisible, the state
  **survives a refresh** (`_apply_scene_element_visibility` re-hides), and `set_source_hidden(id, False)`
  restores them.
* **RESOLVER** — `source:led1` → `([], None, None, "led1")`; `scene-row:5` → `([5], None, None, None)`
  (the sibling browser guard's 2-tuple `_selection_rows_and_label` contract is preserved).
* **WIRING** — `inspect.getsource` asserts the end-to-end plumbing: `track_source_id` in
  `_add_mesh_actor`; `_hidden_source_ids` re-applied in `_apply_scene_element_visibility`;
  `_add_scene_source_glyphs` + map reset in the refresh; the "sources" category + `source:` rows in the
  browser; `set_source_hidden` in `_set_element_hidden`.

Sibling guards still pass: `validate_open3d_normal_to_sensor_gesture_leave`,
`validate_open3d_illumination_heatmap_marker_gated`, `validate_open3d_scene_browser_hide_delete`.
Baseline: phase/title **249** added (pass).

## Notes

* **In-app eyeball owed.** Load the coaxial-LED layout (`machine_vision_150mm_coaxial_led.py`): the LED
  should appear as an amber aperture panel + arrow, listed under **Scene Sources** in the browser, and
  right-click **Hide** should make it vanish (and survive a rebuild) while the imaging scene is
  untouched. A pure imaging scene (`scene_sources: []`) shows no such object.
* **Not yet wired:** add-from-menu (0284), move gizmo (0285), resize handles (0286). Glyph actors are
  intentionally left non-pickable until 0285.
