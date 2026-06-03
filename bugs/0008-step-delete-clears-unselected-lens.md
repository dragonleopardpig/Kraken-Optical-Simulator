# 0008 — Delete/BackSpace erases the imported lens when nothing is selected

**Status:** Fixed. A bare `Delete`/`BackSpace` in the Open 3D view no longer
removes the imported optical STEP overlay unless it is actually selected (or
mid-rotation / mid-carry). `delete_selected_step` now resolves its target
through a delete-only candidate list with no hardcoded `"optical"` fallback.
**Component:** Open 3D inspector — STEP overlay delete
(`Kraken3DInspector.delete_selected_step` /
`_selected_imported_step_label_candidates`).
**Reported via:** in-app recorder, flag `flag_20260603_133557_341`
("lens element dissapear" / "missing element").

## Symptoms (user's words)

> lens element dissapear

The imported lens body that was on screen a moment earlier is simply gone, with
nothing selected.

## State evidence

`flag_20260603_133557_341/state.json` (captured 2026-06-03T13:35:57, recording
already stopped):

* `step_actor_counts: {}`, `step_actor_bounds: {}` — **no** STEP body actors
  remain (the transient optical body was removed and not re-added).
* `selected_step_label: null`, `picked_step_label: null`,
  `selected_step_rotation_active_label: null`, `rotation_handle_count: 0` —
  nothing is selected or being manipulated.
* `show_rays: false`, `ray_actor_count: 0`.
* The analytic rows survive: row 0 Object ⌀25 at z=0 (thickness 100), row 1
  Image at z=100; the global optical axis still spans z=-65..165
  (`optical_axis_records`) and `thickness_dimension_count: 2`.

So the lens import vanished while **everything else** (rows, axis, dimensions)
was preserved — exactly the footprint of clearing only the optical overlay.

The only event log around this flag,
`attachment/recorded_bug_repros/recording_20260603_133545.json`, is actually the
*earlier* `flag_20260603_133340_743` (the separate "thickness dimension skips
the lens" complaint, candidate 0009): it ends ~11 s before this snapshot with the
optical body **present** and the overlay **selected and rotating**. The
disappearance therefore happened in an unrecorded gap, after the user had been
manipulating the selected overlay.

## Behaviour before

`delete_selected_step` is bound to `Delete` / `BackSpace`:

* Tk widget bindings (`open3d_inspector.py:616-619`) route through
  `_delete_selected_step_event` (4740), which only suppresses the key when focus
  is on a text entry/combobox/spinbox.
* The VTK render-window key handler `_on_key_press`
  (`open3d_inspector.py:6715-6716`) calls `delete_selected_step()` directly with
  **no focus guard** — so any `Delete`/`BackSpace` while the 3D view has focus
  deletes.

`delete_selected_step` resolved its target with
`_selected_imported_step_label_candidates()`:

```python
(self.editor._selected_step_label,     # None when nothing is selected
 self._step_rotation_active_label,      # None
 self._step_carry_active_label,         # None
 "optical")                             # hardcoded fallback — always present
```

`Open3DStepStateService.selected_import_label` (`open3d_step_state.py:212`)
returns the first candidate that names a *loaded* overlay, regardless of whether
it is selected. With nothing selected the three real slots are `None`, but the
`"optical"` fallback is loaded, so the resolver returned `"optical"` and
`resolve_delete_selection` reported `import_label="optical"` — and the overlay
was deleted.

## Root cause

The destructive delete shared its target resolver with the **non-destructive**
carry/promote actions. The hardcoded `"optical"` fallback is correct for those
(they explicitly act on "the current overlay", and are only reachable from
deliberate toolbar clicks), but it turns a stray `Delete`/`BackSpace` — with
nothing selected — into a silent deletion of the imported lens. The user, who
had been rotating the overlay and then clicked away (deselecting), pressed Delete
or BackSpace and lost the lens with no selection feedback to explain it.

## Fix

`KrakenOS/UI/open3d_inspector.py`:

* New `_delete_target_import_label_candidates()` — the genuine selection slots
  only, **without** the `"optical"` fallback:

  ```python
  (self.editor._selected_step_label,
   self._step_rotation_active_label,
   self._step_carry_active_label)
  ```

* `delete_selected_step` now resolves through that list. With nothing selected
  the import resolves to `""`, so the delete falls through to promoted-row
  deletion (also empty) and ends on the existing guidance status — a no-op. The
  shared `_selected_imported_step_label_candidates` is untouched, so carry,
  promote, accept, and native/analytic promotion keep their "current overlay"
  fallback.

A genuinely selected overlay (or one mid-rotation / mid-carry) still resolves and
deletes as before.

## Tests

* **`validate_open3d_step_delete_requires_selection`** (display-free) — pins the
  seam without a display: the delete candidate list omits `"optical"` and is
  exactly the three selection slots; the carry/promote list still keeps its
  fallback; at the resolver level an unselected delete yields no import target
  while the old fallback list resolves the loaded `"optical"`; and it
  source-couples `delete_selected_step` to `_delete_target_import_label_candidates`
  (and away from the permissive list) so a refactor can't quietly reintroduce the
  footgun. Fails before the fix (the method doesn't exist / the source still uses
  the permissive list).
* **`validate_open3d_step_delete_requires_selection_snapshot`** (image-snapshot,
  boots its own Xvfb) — imports the tracked prism overlay onto an Object+Image
  chain and renders three frames: (A) lens present, deselected; (B) after
  `delete_selected_step` with nothing selected; (C) after selecting then
  deleting. The fix keeps B identical to A and collapses C to the bare axis
  (verified by eye and by self-calibrating pixel ratios B≈A, C≪A, B≥1.5·C).
  Frame C reproduces the flag-341 state and proves the metric detects a real
  disappearance.
* **Regression / end-to-end** — `Phase 15` in
  `validate_open3d_penta_telescope_comprehensive.py`: imports a STEP overlay,
  deselects everything, fires `delete_selected_step`, and asserts
  `imported_optical_step_path` survives; then selects and deletes to confirm a
  genuine delete still clears it; source-couples the destructive path. Uses the
  tracked prism fixture, so it always runs.
