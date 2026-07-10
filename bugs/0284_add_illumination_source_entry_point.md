# 0284 — "Add Illumination Source (LED)" entry point

## Motivation (piece 1, increment 2 of 4)

bugs/0283 made a parametric scene source a **first-class Open 3D object** — drawn as an amber
emitting-aperture glyph and listed under a **"Scene Sources"** browser group with per-source
hide/unhide. But there was still no way to *create* one from the app: sources only appeared if a scene
script pre-seeded `layout_scene_source_specs`.

This increment (**0284**) satisfies requirement 1 of the four — **addable from a menu**. Right-click the
browser's **"Scene Sources"** group → **"Add Illumination Source (LED)"**. The editor appends a physical
area-LED and the inspector re-traces, so the 0283 glyph + browser row appear immediately. The remaining
increments follow: **0285** move gizmo (this is where glyph actors become pickable), **0286** resize
handles.

## The physics trap this avoids

A **physical** scene source **replaces** the imaging rays: `trace_preview` clears `rays` and traces only
the scene-source bundles when `_build_scene_source_bundles` returns non-empty. So adding a physical LED
legitimately turns an imaging scene into an illumination trace — the emitter starts illuminating the
moment it is added. That is the point.

The trap is *where the add-action reads its starting specs from.* The row-action helpers
(`duplicate/delete/move_scene_source_by_id`) start from `_scene_source_specs_for_direct_editing()`, whose
**empty-scene fallback injects the current Source panel** as a spec. On a pure-imaging scene that panel
is a **NON-physical `Pupil / field` reference** — a paraxial sampling stand-in, not an emitter. If the
add-action started there, adding one LED to an imaging scene would yield `[pupil_field_ref, led]`: a
**supernatural glyph** with no emitter behind it, and (bugs/0282) a re-opened illumination-heatmap gate.

So the add-action starts from `_normalize_scene_source_specs(layout_scene_source_specs)` **directly** —
never the panel fallback — and adding to an imaging scene yields exactly `[led]`. The same reasoning
tightens the 0283 drawable filter to **PHYSICAL-only**, matching exactly what
`_build_scene_source_bundles` launches (a non-physical reference is never an emitter, so it is never a
glyph).

## What ships in 0284

### 1. Editor add-action (`services/source_modeling.py`)

`add_illumination_led_source(*, record_history=True) -> str`:

* starts from `_normalize_scene_source_specs(layout_scene_source_specs)` (the REAL specs, **not** the
  panel fallback);
* mints a unique `source:led-N` id (scans existing ids for the first free ordinal);
* appends a physical `Random rectangle source` seated at the current source-panel **origin**, aimed along
  the current source **direction**, with a **5 mm square** aperture (`half = max(radius, 5)`), **30°**
  cone, `ray_count 2000`, `power 1.0`, at the current wavelength;
* dedupes and commits through `_apply_scene_source_row_action_specs` (the same normalize/dedupe/sync path
  the other row-actions use), returning the new source_id.

Also tightened in this file: `_drawable_scene_source_descriptors` now skips any non-`physical` spec.

### 2. Inspector wrapper (`open3d_inspector.py`)

`add_illumination_led_source()` calls the editor add, then `refresh_from_editor(force_retrace=True)` (the
canonical re-trace+rebuild) so the new glyph + row draw, and sets a status line. A physical source drives
the preview trace, so a full re-trace — not just a display refresh — is required.

### 3. Browser entry point (`panels/open3d_step_admin.py`)

`_on_tree_right_click` intercepts the **"Scene Sources"** group iids (`category:sources` /
`empty:sources`) and pops `_show_scene_sources_context_menu`, whose one command **"Add Illumination
Source (LED)"** calls `_add_illumination_led_source` → `inspector.add_illumination_led_source()` then
`refresh()` (re-lists the tree). This matches the existing right-click-menu idiom (e.g. "Set as
Illumination Source").

## Verification

New display-free guard `validate_open3d_add_illumination_source` = penta phase **250**:

* **ADD-SCHEMA** — adding to an empty scene yields exactly one physical, enabled `Random rectangle
  source` LED that resolves to the seeded origin/direction and a 5 mm **square** aperture (rx == ry),
  30° cone.
* **NO-FALLBACK** — adding to an EMPTY spec list yields `[led]` (length 1), never `[pupil_field, led]`;
  adding to an existing source preserves it (length 2).
* **UNIQUE-ID** — consecutive adds mint `source:led-1` then `source:led-2` (no id collision).
* **DRAWABLE-GATE** — the new LED is drawable; a non-physical `Pupil / field` reference and a face-bound
  marker are NOT (the tightened, physics-matching filter).
* **WIRING** — `inspect.getsource` asserts the browser right-click → menu → inspector → editor chain, the
  "start from real specs" rule (guards the **call** site, not the docstring's explanatory mention), and
  the physical-only drawable filter.

Sibling 0283 guard `validate_open3d_scene_source_object` still passes. Baseline: phase/title **250**
added (pass).

## Notes

* **In-app eyeball owed.** On any scene, right-click **Scene Sources** in the browser → **Add
  Illumination Source (LED)**: an amber aperture glyph + arrow should appear at the Source-panel pose,
  listed under **Scene Sources**, and the scene should switch to the illumination trace. On a
  pure-imaging scene the result must be exactly one LED (no phantom `Pupil / field` glyph).
* **Not yet wired:** move gizmo (0285), resize handles (0286). Glyph actors remain non-pickable until
  0285, so the freshly-added LED is created at the Source-panel pose and moved by editing its spec until
  the gizmo lands.
