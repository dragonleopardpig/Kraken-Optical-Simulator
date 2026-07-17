# bugs/0335 — Right-click on the selected CA opening must show the opening menu, not "hop" to the STEP

**Flag 3 of the three-flag recording** (`recording_20260717_121101.json`):
*"Right click on the selected CA edge: the selection hop, causing the right click
to show the menu of the STEP instead of the edge."*

Pairs with bug 0334 (left-click pins the opening) — this is the right-click on
that pinned opening.

## The "hop"

`_right_click_pick_context` (`open3d_inspector.py`) runs a **fresh**
`picker.Pick()` at the cursor. Over a clear-aperture opening that ray passes
**through** the see-through hole and latches onto a recessed body cell *behind*
it, so the right-click menu resolves the **whole STEP body** (promote / assign-
face items) instead of the opening the user just selected. The selection appears
to "hop" from the rim to the body.

## Fix — drive the menu from the pinned opening, ahead of the re-pick

Because bug 0334 leaves the opening pinned in a **persistent** slot, the menu no
longer needs to re-pick anything. `_show_surface_function_context_menu`
(`open3d_face_assignment.py`) gains a guard **before** it calls
`_right_click_pick_context`:

```python
if self._has_selected_step_opening() and self._show_selected_opening_context_menu(event):
    return "break"
```

`_show_selected_opening_context_menu(event)` builds the menu straight from the
pinned geometry (`_selected_opening_label` / `_face_id` / `_center` / `_normal`)
— **no cell pick**, so nothing can fall through the hole. It offers the
clear-aperture actions **only**:

- **"Snap Clear Aperture -> Optical Axis (center + normal)"** — the 0333 action,
  using the opening's own centre + normal (armed only when the normal is finite).
- **"Set Clear Aperture (pick window face)..."**
- when a CA is already set: **"Center Clear Aperture -> Optical Axis"** +
  **"Forget Clear Aperture"**.
- **"Deselect opening"** — a menu affordance for the same click-elsewhere clear.

It deliberately omits the whole-body **"Promote and set …"** / **"Center Picked
Face"** items — a pinned opening is not a body selection. Returns `False` if the
pinned geometry can't be resolved, so the caller falls back to the normal path.

The pre-existing 0333 behaviour (a right-click while *hovering* an opening, with
nothing pinned, still surfaces the CA snap inside the full STEP menu) is
unchanged; this bug is specifically the **pinned/selected** case that flag 3
describes.

## Guard & regression

`KrakenOS/UI/validate_open3d_led_ca_persistent_select.py` (penta **Phase 293**),
display-free, **Section 2**:
- source contract: the opening menu is guarded **ahead of**
  `_right_click_pick_context` (so it cannot hop);
- behavioural: `_show_selected_opening_context_menu` builds the CA snap +
  Set/Center/Forget + Deselect items and **no** "Promote" item from the pinned
  geometry, posts through `_popup_context_menu`, and returns `False` (no post)
  for empty geometry.

## Files touched
- `KrakenOS/UI/services/open3d_face_assignment.py` —
  `_show_selected_opening_context_menu` + the guard in
  `_show_surface_function_context_menu`.
- `KrakenOS/UI/validate_open3d_led_ca_persistent_select.py` — new guard (Section 2).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 293.
- `tools/penta_validator_baseline.json` — Phase 293 = pass.
