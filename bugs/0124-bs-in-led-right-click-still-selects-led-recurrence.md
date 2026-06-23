# 0124 — BS-inside-LED right-click STILL selects the LED edge (0121 recurrence)

## Symptom

`flag_20260623_211941_929` → re-recorded as `flag_20260624_073033_166`:

> "after cube BS slide in overlapping the LED, not glued yet, mouse hover
> highlight the splitting plane, right click, the selection changed to LED edge
> instead."

This is the **same** failure bugs/0121 was meant to fix (commit `c441ebb`,
penta phase 113). bugs/0121 shipped with the live behaviour **in-app eyeball
owed** (headless Xvfb can't drive the embedded-VTK hover + right-click), and the
eyeball showed the fix did not resolve the live case.

`step_actor_bounds` confirms the overlap is the 0121 class: `optical` (BS)
x[-27.5, 27.5] y[-39, 39] z[207.7, 262.7] sits fully inside `led`
x[-32.2, 78.0] y[-45, 45] z[192.0, 268.4].

## What the instrumentation revealed

bugs/0124 first shipped **instrumentation, not a fix** (commit `6250b5f`):
`_right_click_pick_context` records `self._last_right_click_debug` and the
recorder carries it into `state.json` as
`scene_state.right_click_diagnostics`. The re-recording pinned the branch:

```json
{
  "cursor_xy": [456, 425],
  "prior_hover_key": "(None, 'passive', 'S001/F001')",
  "hovered_label": null,
  "vtk_step_label": "led",
  "override_eligible": false,
  "override_fired": false
}
```

So the gold outline **was** recorded (`prior_hover_key` is not None — the BS
splitting face `S001/F001`), but `hovered_label` resolved to **null**, so the
0121 override was never `override_eligible`. This is a **fourth** no-op path, not
one of the three the diagnostic commit hypothesised: the hover key is present yet
*unrecoverable*.

## Root cause

The passive STEP hover key is built in
`KrakenOS/UI/services/open3d_interaction.py` (idle-hover handler):

```python
step_label = self._actor_step_map.get(actor_key) if actor_key is not None else None
if step_label is None:
    fallback_step_pick = self._step_feature_pick_any_for_display_xy((x, y))
    if fallback_step_pick is not None:
        step_label = str(fallback_step_pick.get("label"))   # resolves "optical"
...
hover_key = (actor_key, "passive", face_id or int(cell_id))  # <- BUG: actor_key head
```

When the BS is buried in the LED, the VTK cell picker lands on the **LED shell**
(or nothing), so `actor_key` is `None` / the LED's, and `step_label` ("optical")
is recovered from the deterministic **fallback feature pick**. But the hover key
still leads with the raw `actor_key`. At right-click,
`_hovered_step_label_and_row_from_key` parses the head:

```python
head = hover_key[0]                       # None  (this flag) — or the LED's actor key
...
if not isinstance(head, str):
    return None, None                     # None head -> hovered_label is None
label = self._actor_step_map.get(head)    # an actor key -> resolves "led" (WRONG body)
```

Both broken heads defeat the override:

- **`actor_key is None`** (this flag) → head is not a str → `hovered_label = None`
  → `override_eligible = False`.
- **`actor_key` = the LED shell** → `_actor_step_map[head] = "led"` →
  `hovered_label == vtk_step_label == "led"` → override correctly skipped but for
  the wrong body.

Either way the gold outline sits on the BS while the right-click commits the LED.
The resolved label was in hand at construction time and thrown away.

## Fix

Lead the passive STEP hover key with the **resolved** label, the form
`_hovered_step_label_and_row_from_key` maps back directly (its `("step", label,
…)` branch), independent of which actor the VTK picker latched onto:

```python
hover_key = ("step", str(step_label).strip().lower(), face_id or int(cell_id))
```

Now `("step", "optical", "S001/F001")` → `("optical", None)`, so with the LED
under the VTK picker (`vtk_step_label == "led"`) the override is eligible
(`"optical" != "led"`) and `_right_click_context_for_hovered_step("optical", …)`
rebuilds the context on the BS splitting face — the same deterministic
display-ray feature pick that drew the gold outline. The promoted-row hover
branch already used a recoverable `("row", row_index, …)` head, so only the
STEP-overlay branch needed the change.

## Test

`KrakenOS/UI/validate_open3d_hover_key_carries_step_label.py::run_checks` —
display-free, drives the REAL `_hovered_step_label_and_row_from_key`:

- the fixed `("step", "optical", "S001/F001")` key recovers `("optical", None)`;
- both broken heads reproduce the live no-op — `(None, "passive", …)` →
  `(None, None)` (unrecoverable), `("0xLED", "passive", …)` → `("led", None)`
  (wrong body);
- the 0121 override is `eligible` only with the fixed key (`optical != led`);
- source contract — the passive STEP hover branch builds the key with the
  `("step", label, …)` head and the buggy `(actor_key, "passive", …)` head is
  gone.

Penta **phase 116** runs the guard. (Mutation-tested: reverting the construction
to the actor-key head flips the guard to FAIL.)

## Note — in-app eyeball owed

Headless Xvfb can't drive the embedded-VTK hover + right-click, so the live
"right-click on the BS-in-LED splitting plane selects the BS, not the LED" is
verified in-app. The guard pins the regression-critical invariant: the hover key
carries the resolved label so the 0121 override can fire. If the live case still
misses, the `right_click_diagnostics` block now shows `hovered_label: "optical"`
and `override_eligible: true`, isolating any remaining miss to the override's
re-pick (branch 3) rather than the hover key.
