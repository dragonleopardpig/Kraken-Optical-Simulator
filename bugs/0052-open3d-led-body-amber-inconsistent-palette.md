# 0052 — Open 3D: the LED body is amber, inconsistent with the rest (and kills the gold hover contrast)

## Symptom (user's words)

> Why only the LED body still orange? and the highlighted edge is yellow, hard
> to see. Some highlight are not exactly the edge, some offset.

Flag `flag_20260610_203054_550` (2026-06-10T20:30:54), `machine_vision_150mm`,
`interaction_mode: idle`, **`selected_step_label: null`** — nothing selected,
yet the LED housing renders a saturated amber while the camera/lens are
grey-blue glass. (Earlier flag `192640` raised the same "why is this orange"
about the LED while it was *selected*; 0051 fixed the *selection* styling, but
this flag is unselected, so it exposed the **base** body color.)

## Root cause

The imported-STEP overlay body colors are a per-label palette, and the LED was
given a saturated amber:

```python
"led": (..., (0.95, 0.62, 0.16), 0.35),   # amber; lens/camera are grey-blue
```

That amber was a deliberate "this is the light source" cue, paired with the
app's *"click the orange LED edge"* object-to-LED-distance affordance. But it
read as an odd, inconsistent orange block ("different from the rest"), and the
shared **gold** face-hover accent `(1.0, 0.78, 0.08)` is nearly invisible on an
amber body (warm-on-warm) — hence "the highlighted edge is yellow, hard to see."

The color was **duplicated in two draw paths** (this is why an earlier partial
fix wasn't enough):

- `open3d_step_overlay_refresh._step_overlay_display_spec` — the per-label
  *partial* refresh, and
- `open3d_scene_refresh` — the inline per-label spec list used by the *full*
  `refresh_from_editor` rebuild (the path that actually renders normally).

## Fix

De-amber the LED to the shared grey-blue glass palette `(0.30, 0.36, 0.46)` (the
same family as `lens`/`camera`) in **both** paths, so all imported solids read
as one palette and the gold hover edge regains contrast. The user chose this
("De-amber to match the rest") over keeping the amber light-source cue.

Reworded the now-inaccurate Open-3D status/hint strings that promised an
"orange" LED:

- `open3d_interaction.py` — *"Click the LED edge used for Object-to-LED
  distance."* / *"Click the {label} feature to center it on the optical axis."*
- `open3d_inspector.py` — *"OBJ -> LED\nClick the LED object-edge feature."*

The **legacy** 3D renderer is left untouched: it still draws the LED amber
(`legacy_3d_scene.py` `led_color="#f59e0b"`) and its matching "orange LED"
strings stay accurate there; this flag and fix are the Open-3D inspector.

Files: `KrakenOS/UI/services/open3d_step_overlay_refresh.py`,
`KrakenOS/UI/services/open3d_scene_refresh.py`,
`KrakenOS/UI/services/open3d_interaction.py`, `KrakenOS/UI/open3d_inspector.py`.

## Tests

- `KrakenOS/UI/validate_open3d_led_overlay_palette.py` — display-free: asserts
  `_step_overlay_display_spec("led")` is the grey-blue glass color (matches
  `lens`/`camera`'s family) and is not the old amber.
- Phase 57 in `validate_open3d_penta_telescope_comprehensive.py` — imports the
  prism as the `led` label, runs a full `refresh_from_editor`, and asserts the
  rendered LED body actor color is grey-blue (covers the full-refresh path that
  the partial-refresh-only fix would miss).

Visually verified by rendering the LED overlay before/after: amber block ->
grey-blue glass body with teal edges, matching camera/lens.

## Known follow-up (not in this fix)

"Some highlight are not exactly the edge, some offset" — for display-only solids
the face hover outline is built from the coarse planar-clustering metadata, so
it traces a triangle *cluster* boundary rather than the crisp CAD feature edge
(the recorded outline covered only z[213.6, 276.4] of the face's true
z[200, 276.4]). De-ambering restored contrast so the outline is at least
legible; aligning it precisely to CAD feature edges for tessellated display-only
bodies is a separate geometry effort.
