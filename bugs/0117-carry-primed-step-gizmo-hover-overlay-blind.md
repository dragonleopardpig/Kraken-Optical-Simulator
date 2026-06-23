# 0117 — A carry-primed STEP (freshly imported LED) cannot hover-highlight its gizmo

## Symptom

Import an LED STEP. It auto-selects, self-positions on the optical axis, and its
move/rotate gizmo is drawn. Hovering the LED **highlights its edges/faces**, but
hovering directly over a **gizmo handle does nothing** — no gold hover affordance.

Reported (flag `flag_20260623_135922_403`):

> "freshly imported LED, already self position at the optical axis, mouse hover
> can highlight LED edges, but not the gizmo."

The re-recorded flag confirmed the live state: `interaction_mode: idle`,
`selected_step_label: 'led'`, `rotation_handle_count: 6` — i.e. the six handles
ARE present and live; only the hover highlight is suppressed.

## Root cause

A freshly imported/selected STEP is **carry-primed**: `import_step_overlay`
(`open3d_inspector.py`) sets `_step_carry_active_label = label`, so
`_step_carry_label()` is non-None at idle.

The hover handler `Open3DInteractionService._on_mouse_move`
(`services/open3d_interaction.py`) resolves a `target_label`. When nothing else
is active it falls back to the carry label:

```python
if target_label is None and not axis_pick_any:
    carry_label = self._step_carry_label()
    if carry_label is not None:
        target_label = str(carry_label)     # 'led'
```

A non-None `target_label` then **skips the idle-hover block** (gated
`if target_label is None and not axis_pick_any:`). That idle block is the only
one that hover-picks handles via `_passive_hover_pick_rotation_handle` — an
**overlay-aware** pick that restricts the pick list to handle actors and picks
them from the dedicated gizmo overlay renderer (`_gizmo_overlay_renderer`,
bugs/0112, `vtkRenderer` at `SetLayer(2)`).

The carry-primed path instead lands in the second hover block, which picks via
the **main renderer**:

```python
_traced_pick(self._picker, x, y, 0.0, self._renderer, site="hover_default")
actor = self._picker.GetActor()
actor_key = self._actor_key(actor)
step_rotate = self._actor_step_rotate_map.get(actor_key) ...   # always None
```

Gizmo handles register **only** on the overlay renderer
(`_register_overlay_actor`: `overlay_on_top and _gizmo_overlay_renderer is not
None` -> `_gizmo_overlay_renderer.AddActor(actor)`, never the main renderer), so
a main-renderer pick can never return a handle. The four gizmo-map lookups always
yielded `None` and fell through to the STEP edge/face hover — which DID work,
hence "edges highlight, gizmo doesn't."

The **click** path was unaffected: `_on_left_button_press` already picks the
gizmo overlay first (bugs/0112), and the carry-primed idle state sets no active
pick mode, so a handle CLICK still grabbed it. Only HOVER was overlay-blind.

## Fix

In the carry-primed hover branch, resolve the gizmo maps from the overlay-aware
`_passive_hover_pick_rotation_handle` instead of the main-renderer `actor_key`,
gated to the carry-primed case so the explicit axis-pick / led-edge hover paths
are untouched:

```python
carry_primed_target = False
... target_label = str(carry_label); carry_primed_target = True
...
actor_key = self._actor_key(actor)
handle_key = None
if carry_primed_target:
    _ha, handle_key, _hc = self._passive_hover_pick_rotation_handle(x, y)
step_rotate = self._actor_step_rotate_map.get(handle_key) if handle_key is not None else None
...   # the four handle branches now highlight via handle_key
```

`_passive_hover_pick_rotation_handle` uses `_prop_picker` (a real
`vtkPropPicker`), so it leaves `self._picker` untouched — the main-renderer pick
above still drives the STEP face/feature hover that follows. The main `actor_key`
remains the source for the body/face hover; only the gizmo-handle lookups become
overlay-aware.

## Test

`KrakenOS/UI/validate_open3d_carry_primed_gizmo_hover.py::run_checks`
(display-free; embedded-VTK hover picks cannot be driven headless):

1. the carry branch sets a `carry_primed_target` flag when `target_label` comes
   from `_step_carry_label()`;
2. the carry-primed hover branch resolves the gizmo maps from
   `_passive_hover_pick_rotation_handle` (overlay-aware), gated on
   `carry_primed_target`, and reads all four handle maps with `handle_key`;
3. no regression — the second hover block no longer sources its gizmo-map reads
   solely from the main-renderer `actor_key`;
4. `_passive_hover_pick_rotation_handle` is genuinely overlay-aware (its body
   picks from `_gizmo_overlay_renderer`) and is referenced by `_on_mouse_move`
   in both the idle and carry-primed branches.

Penta phase 109 runs this guard.

## Note — in-app eyeball owed

Headless Xvfb cannot drive an embedded-VTK hover pick, so the gold highlight
itself is verified in-app, not by the guard. The guard pins the source contract
that makes the carry-primed hover overlay-aware.
