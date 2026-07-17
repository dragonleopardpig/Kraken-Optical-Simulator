# bugs/0340 — a pinned FACE and a pinned OPENING/edge can be selected together

**Flag `flag_20260717_135830_322`** (latest live test, imported LED):

> "face and edge can be selected in sequence, which shouldn't be the case."

## The defect

After bugs/0338 there are two independent *persistent* STEP selections, each in its
own slot on the inspector:

- a clear-aperture **opening** pin — `_set_selected_step_opening` (bugs/0334),
- a STEP **face** pin — `_set_selected_step_face` (bugs/0338).

Each setter cleared **only its own** slot before drawing the new outline:

```python
# _set_selected_step_opening
self._clear_selected_step_opening(render=False)   # opening slot only
...
# _set_selected_step_face
self._clear_selected_step_face(render=False)      # face slot only
```

So a left-click that pinned a **face** left an already-pinned **opening** (or edge)
lit, and vice versa — two cyan outlines at once, exactly the "face and edge selected
in sequence" the user flagged. The screenshot shows the whole LED side face pinned in
cyan with an edge selection still live from a prior click.

Only `_clear_open3d_selection` (the click-elsewhere / mode-flip path) dropped both;
the *pin* path never crossed slots.

## Fix — one persistent feature at a time (`open3d_inspector.py`)

Each setter now also clears the **other** slot, so pinning one feature drops the
other:

```python
# _set_selected_step_opening
self._clear_selected_step_opening(render=False)
self._clear_selected_step_face(render=False)      # bugs/0340

# _set_selected_step_face
self._clear_selected_step_face(render=False)
self._clear_selected_step_opening(render=False)   # bugs/0340
```

At most one persistent selection (face **or** opening) is ever live — the same
"single selection" model the user expects, matching the checkbox's face/edge mode.

## Guard & regression

`KrakenOS/UI/validate_open3d_single_persistent_feature_selection.py` (penta
**Phase 295**), display-free (renderer=None → pure state round-trip):
- pin an opening → opening pinned, face not;
- pin a face while the opening is pinned → face pinned, opening **cleared**;
- pin an opening again while the face is pinned → opening pinned, face **cleared**;
- neither order (face→opening, opening→face) ever leaves **both** pinned.

## Files touched
- `KrakenOS/UI/open3d_inspector.py` — `_set_selected_step_opening` /
  `_set_selected_step_face` each clear the opposite slot.
- `KrakenOS/UI/validate_open3d_single_persistent_feature_selection.py` — new guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 295.
- `tools/penta_validator_baseline.json` — Phase 295 = pass.
