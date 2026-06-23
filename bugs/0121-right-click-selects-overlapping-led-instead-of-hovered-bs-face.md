# 0121 — right-click jumps to the LED edge instead of the hover-highlighted BS splitting face

## Symptom

`flag_20260623_164923_514` — "slide the BS to the LED, not glued yet. Highlight BS
splitting surface, right click, selected surface change to LED edge."

The user slid the beam splitter (the `optical` STEP overlay) along the axis until it
sat **inside** the LED enclosure (the `led` overlay), then hovered the BS's 45° coated
splitting face. The gold hover outline correctly landed on the splitting surface. On
**right-click**, the highlighted/selected surface jumped to a **LED edge** — the menu
operated on the wrong body.

`state.json` confirms the overlap:

- `optical` (BS) bounds `x[-25.8, 29.2] y[-39, 39] z[213.8, 268.8]`, offset
  `[1.68, 0, 202.3]`;
- `led` bounds `x[-32.2, 78.0] y[-45.0, 45.0] z[200.0, 276.4]`, offset `[22.9, 0, 0]`.

The LED's bounding box fully **encloses** the BS in x/y/z, so the two translucent
bodies overlap heavily where the user is working.

## Root cause

The BS's 45° coating is an **internal** face. The VTK cell picker (`self._picker`)
only ever reports the nearest **external shell** face for a translucent solid, and for
**overlapping** translucent bodies it latches onto a **pixel-varying** actor — sometimes
the BS shell, sometimes the LED wall.

A prior fix (`open3d_round_lens_pick.py::step_feature_pick_for_display_xy`, lines
233-253) made the **hover** path deterministic: for a clean solid (few faces) it prefers
the internal display-ray pick, so the gold outline reliably lands on the 45° coating.

But the **right-click** resolves *which element* to act on **upstream** of that
deterministic pick. `_right_click_pick_context` reads the picked label straight from the
flaky VTK actor:

```python
self._picker.Pick(x, y, 0.0, self._renderer)
actor_key = self._actor_key(self._picker.GetActor())
step_label = self._actor_step_map.get(actor_key)   # <- LED when the picker lands on the LED wall
```

With the BS inside the LED, the picker returned the **LED** actor, so `step_label`
became `"led"` and the whole menu (including the re-highlight at
`open3d_face_assignment.py:260`) operated on the LED — even though the user was looking
at the BS face highlighted in gold. The hover recovered from the flaky picker; the
right-click committed to the wrong **label** before the deterministic preference could
apply.

## Fix

`_right_click_pick_context` now prefers the element the user **currently sees
highlighted**. The live `_hover_step_cell_key` is the single source of truth for the
gold hover outline, so capture it **before** re-picking and prefer it:

1. **`_hovered_step_label_and_row_from_key(hover_key)`** maps the hover key back to a
   `(step_label, row_index)`. Hover keys come as `("step", label, …)`,
   `("row", row_index, …)` or `(actor_key, …)` (every idle/mode hover —
   `"passive"`/`"display"`/`"ray"`/cell-id tails); the actor-key head resolves through
   `_actor_step_map` / `_actor_row_map`. A Measure re-anchor key
   (`(handle_key, "reanchor", …)`) maps to `(None, None)` so it is never hijacked.
2. **`_right_click_context_for_hovered_step(label, display_xy, event)`** rebuilds the
   menu context for the hovered STEP label using the **deterministic** display-ray
   feature pick (`_step_feature_pick_for_display_xy`), which prefers the BS's internal
   45° face. It carries no VTK actor/cell, just the resolved face point/normal.
3. **`_right_click_pick_context`** captures `prior_hover_key` at the top, computes the
   VTK-resolved label, and when the **hovered** STEP label differs from the VTK one,
   returns the hovered context instead. Non-overlap / row / programmatic right-clicks
   (no prior hover, or hover == VTK) fall through to the existing path unchanged.

Net: a right-click acts on the face shown by the gold hover outline, even when a beam
splitter is buried inside the LED enclosure.

## Test

`KrakenOS/UI/validate_open3d_right_click_prefers_hovered_face.py::run_checks` —
display-free:

- **key parse** — all hover-key forms map to the right `(label, row)`; a `"reanchor"`
  Measure handle key maps to `(None, None)`;
- **hovered-context build** — an internal feature pick on the hovered label yields a
  context with that label, the face point, a unit normal, no row/actor; a hidden or
  invalid label yields no context (graceful fall-through);
- **behavioural override** — with the BS hovered and the LED under the (faked) VTK
  picker, the resolved context is the **BS**;
- **source contract** — `_right_click_pick_context` captures `_hover_step_cell_key`
  **before** `.Pick(`, and consults the hovered-face helpers **before** trusting the
  raw `_actor_step_map` label (anchored on the bugs/0089 comment).

Regression-proofed: removing the override block trips the guard
("does not consult the hovered-face helpers").

Penta **phase 113** runs the guard.

## Note — in-app eyeball owed

Headless Xvfb cannot drive the embedded-VTK hover + right-click pick on overlapping
translucent bodies, so the live menu behaviour is verified in-app. The guard pins the
hover-key parsing, the deterministic hovered-context rebuild, the override decision, and
the capture-before-repick ordering.
