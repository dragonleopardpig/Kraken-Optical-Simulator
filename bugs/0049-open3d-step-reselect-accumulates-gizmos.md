# 0049 — Open 3D: selecting a new STEP keeps the previous one's rotation gizmo

## Symptom (user's words)

Three consecutive in-app flags on the `machine_vision_150mm_test` layout
(Allied Vision hr25MCX camera + 15056 imaging lens + OPT-CO90 LED):

1. `flag_20260610_152343_579` — "Imaging lens STEP selected."
2. `flag_20260610_152400_230` — "Camera selcted, but the Imaging Lens still get selected."
3. `flag_20260610_152431_320` — "LED STEP selected, previous two selection are not cleared."

Clicking a different imported STEP solid leaves the previously-selected
solid's combined Move/Rotate gizmo on screen. Pick three solids in a row
and three gizmos stack up.

## Repro bundle

`attachment/recorded_bug_repros/flag_20260610_152343_579`,
`…_152400_230`, `…_152431_320`. The recorded `scene_state` is the smoking
gun — `selected_step_label` correctly tracks the latest pick
(lens → camera → led) but `rotation_handle_count` climbs **6 → 12 → 18**:
each pick adds another six rotate-pick arrowheads without removing the
prior label's six. (`display_orientation: 'YZ'` — this is the Open 3D
inspector in an orthographic side view, not the 2D editor.)

## Root cause

`Kraken3DInspector.show_step_rotation_handler(label)` only ever *added*
the clicked label's handles. The chain was
`show_step_rotation_handler → _ensure_step_rotation_handles_for_label →
Open3DStepRotationHandleService.ensure_for_label`, and `ensure_for_label`
is a no-op-or-add: it returns early when the label already has handles and
adds six when it has none. Nothing in that path removed the *previous*
label's actors, and `_close_step_rotation_handler` only nulled
`_step_rotation_active_label` without touching actors. So body highlight
was already single-select-correct (`apply_step_selection` deselects every
other body) but the gizmo actors leaked, one ring of six per pick.

## Fix

Reconcile the live gizmos to a selection *set* instead of additively
ensuring a single label. Files:

- `KrakenOS/UI/services/open3d_step_rotation_handles.py` — new
  `remove_for_label(label)` (mirrors `remove_actors()` but filtered to the
  actors that follow one label) and `reconcile_to_labels(labels)` (removes
  handles for any label not in the target set, ensures handles for each
  label in it). A `_handle_keys_for_label` / `_labels_with_handles` pair
  backs them off the existing rotate / translate / visual actor maps.
- `KrakenOS/UI/open3d_inspector.py` —
  - new `_selected_step_labels: set[str]` state (the multi-select set;
    `_step_rotation_active_label` stays the primary / last-clicked member);
  - `show_step_rotation_handler(label, *, additive=False)` now computes the
    selection set (plain click → `{label}`, collapsing prior gizmos;
    Shift+click → toggle the label in/out), reconciles handles to it, and
    highlights the whole set;
  - `_update_step_rotation_handler_state` reconciles to the validated set
    (drops labels whose STEP path vanished, re-syncs the primary) so a
    scene refresh preserves multi-select;
  - `_close_step_rotation_handler` clears the set;
  - `_set_step_highlight_set` / `_reconcile_step_rotation_handles` facades.
- `KrakenOS/UI/services/open3d_selection_representation.py` — new
  `apply_step_selection_set(labels)` highlights every body in the set.
- `KrakenOS/UI/services/open3d_scene_refresh.py` — the post-rebuild
  highlight uses the set so extra multi-selected bodies keep their glow.
- `KrakenOS/UI/services/open3d_interaction.py` — `_on_left_button_press`
  reads `GetShiftKey()` into `shift_additive` and threads it into the plain
  STEP-body select branch. **Ctrl is left untouched** — it is already the
  camera-orbit modifier (`_ctrl_left_camera_active` + the `GetControlKey()`
  early return), so overloading it would break orbit; Shift was free.

Behavior: plain click = single-select (tears down the prior solid's
gizmo — the reported fix); Shift+click = intentional multi-select (toggle a
solid into/out of the set, multiple gizmos coexist); Ctrl = camera orbit
(unchanged).

## Tests

- `KrakenOS/UI/validate_open3d_step_reselect_single_gizmo.py` —
  display-free. Drives `show_step_rotation_handler` against a stub
  inspector with real rotate/translate/visual actor maps: plain reselect
  keeps the handle count at six and swaps the label; Shift+click grows to
  twelve and back; plain click after a multi-select collapses to one. Run:
  `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_reselect_single_gizmo`.
- Phase 54 in `validate_open3d_penta_telescope_comprehensive.py` —
  end-to-end on the penta cascade: select element A then element B; assert
  the rotation-handle count does not accumulate across the reselect.

## Regression-sweep notes

- `validate_3d_interaction_contract.py` — the "STEP reselect rebuilds
  rotation handles after blank deselect" check asserted the old additive
  `_ensure_step_rotation_handles_for_label(label)` call in
  `show_step_rotation_handler`. That call is the leaky path this bug
  replaced, so the assertion was retargeted to `_reconcile_step_rotation_handles(`
  (the new rebuild mechanism — reconcile still routes through
  `ensure_for_label → add_handles`, so the downstream assertions are
  unchanged). `_ensure_step_rotation_handles_for_label` itself is kept:
  `validate_open3d_scene_browser_hide_delete.py` guards that it exists and
  carries the bugs/0027 `is_step_label_hidden` suppression.
- `validate_step_rotation_handles.py` — pre-existing failure unrelated to
  this bug: the `Kraken3DInspector.__new__` stub never set
  `_hidden_step_labels`, which `is_step_label_hidden` (added by bugs/0027,
  after this test) reads. Added `inspector._hidden_step_labels = set()` to
  the stub.
- Pre-existing `validate_3d_interaction_contract` failures (10, e.g. "fixed
  drag preserves focal point") are branch debt on `nonseq-display-refactor`
  and are out of scope for 0049 — confirmed identical with this fix stashed.
