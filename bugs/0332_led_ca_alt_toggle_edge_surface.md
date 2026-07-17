# bugs/0332 — Alt over a clear-aperture opening should toggle Edge ↔ Surface

**Issue 1 of the two-issue request:** *"How should the ALT + Hover function now?
Toggle between Surface and Edge highlight?"*

## Desired behaviour

The LED clear-aperture (CA) opening became a first-class hover target across
0327–0331: a plain hover snaps to the opening's **EDGE** (its closed rim loop).
The Alt modifier should make hover a **toggle between granularities**, exactly
like the existing body-face path:

| cursor over…            | plain hover      | Alt hover              |
|-------------------------|------------------|------------------------|
| a body FACE (existing)  | whole FACE       | nearest drawn EDGE     |
| a CA OPENING (this bug) | EDGE (rim)       | owning SURFACE (face)  |

Both read as one consistent rule — *Alt toggles Surface ↔ Edge* — so the user
has a single mental model regardless of what the cursor is over.

Before this fix Alt did nothing over an opening: the opening branch returned the
edge feature and ignored `_edge_pick_alt_active` entirely.

## Fix

`KrakenOS/UI/services/open3d_round_lens_pick.py`,
`step_feature_pick_for_display_xy`: when the opening hover pick fires and Alt is
held, resolve the SURFACE that owns the opening and return it instead of the rim:

```python
alt_active = bool(getattr(inspector, "_edge_pick_alt_active", False))
ca_feature = _step_opening_hover_pick(inspector, label, display_xy)
if ca_feature is not None:
    if alt_active:
        surface_feature = _opening_owning_surface_feature(inspector, label, ca_feature)
        if surface_feature is not None:
            return surface_feature
    return ca_feature
```

New helper `_opening_owning_surface_feature(inspector, label, opening_feature)`:
- parses the opening feature's `face_id` (e.g. `"F053"` → `53`),
- fetches the shared display mesh via
  `inspector.editor._transformed_imported_step_mesh_for_label(label)`,
- builds the whole-face outline `face_outline_from_face_indices(mesh, (face_index,))`,
- resolves centroid + normal with the existing
  `inspector.editor._step_overlay_fine_face_centroid_normal(label, face_index)`
  (same face-index space as the outline — verified across 0327–0331),
- returns a feature dict shaped like the per-cell body pick
  (`{"feature": (centroid, overlay_mesh, normal), "surface_center": …,
  "face_id": …, "through_pick": None}`).

**Graceful degradation:** if the owning face index can't be resolved (empty /
malformed `face_id`, missing mesh, non-finite centroid) the helper returns
`None` and the caller keeps the edge feature — so Alt is *inert*, never blank.

## Why no new event wiring was needed

The Alt-transition re-fire from **bug 0324** already re-runs the hover pick when
the modifier state flips without any mouse motion:
`_refresh_edge_pick_alt_state(active)` → `_refire_scene_hover_pick()` → resets
the throttle and fires a synthetic `interactor.MouseMoveEvent()`. So pressing or
releasing Alt while the cursor rests on the opening immediately re-runs
`step_feature_pick_for_display_xy` and swaps the highlight. The toggle rides that
existing path.

## Guard & regression

`KrakenOS/UI/validate_open3d_led_ca_axis_snap.py` (penta **Phase 292**),
display-free, **Section 1**:
- `_opening_owning_surface_feature` resolves the owning face on a synthetic
  single-face mesh and returns `None` for an empty `face_id` (Alt-inert path).
- the branch in `step_feature_pick_for_display_xy` returns the EDGE feature on a
  plain hover and the SURFACE feature under Alt (with `_step_opening_hover_pick`
  monkeypatched to a known opening). Teeth proven: patching the resolver to
  return `None` fails the section.

## Files touched
- `KrakenOS/UI/services/open3d_round_lens_pick.py` — `_opening_owning_surface_feature`
  helper + Alt branch in `step_feature_pick_for_display_xy`.
- `KrakenOS/UI/open3d_inspector.py` — `"opening": True` marker on the two opening
  hover builders (shared with 0333 so the right-click menu can detect an opening).
- `KrakenOS/UI/validate_open3d_led_ca_axis_snap.py` — new guard (Section 1).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 292.
- `tools/penta_validator_baseline.json` — Phase 292 = pass.
