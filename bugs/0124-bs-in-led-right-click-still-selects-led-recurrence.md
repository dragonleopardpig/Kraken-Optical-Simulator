# 0124 — BS-inside-LED right-click STILL selects the LED edge (0121 recurrence) — diagnostic step

## Symptom

`flag_20260623_211941_929`:

> "after cube BS slide in overlapping the LED, not glued yet, mouse hover
> highlight the splitting plane, right click, the selection changed to LED edge
> instead."

This is the **same** failure bugs/0121 was meant to fix (commit `c441ebb`,
penta phase 113). The user has rebuilt (the 0122 / 0123 changes are live, so 0121
is too), yet the bug recurs. bugs/0121 shipped with the live behaviour **in-app
eyeball owed** (headless Xvfb can't drive the embedded-VTK hover + right-click),
and the eyeball now shows the fix does not resolve the live case.

`state.json` confirms the overlap is the 0121 class: `optical` (BS)
x[-27.5, 27.5] y[-39, 39] z[205.8, 260.8] sits fully inside `led`
x[-32.2, 78.0] y[-45, 45] z[191.7, 268.1].

## Why the 0121 fix can silently miss

`_right_click_pick_context` only overrides to the hovered face when

```python
hovered_label, _ = self._hovered_step_label_and_row_from_key(prior_hover_key)
if hovered_label is not None and hovered_label != vtk_step_label:
    hovered_context = self._right_click_context_for_hovered_step(...)
    if hovered_context is not None:
        return hovered_context
```

There are three independent ways this no-ops, and the static evidence can't
distinguish them:

1. **`prior_hover_key` is None** at right-click time — the gold splitting-face
   highlight wasn't recorded in `_hover_step_cell_key`, or it was cleared before
   the right-click resolves. (`state.json` shows `hover_step_cell_key: None`, but
   that is captured *after* the right-click, so it is only suggestive.)
2. **`hovered_label` already resolves to `"led"`** (== `vtk_step_label`) — then
   the override is correctly skipped but for the wrong body.
3. **`_right_click_context_for_hovered_step("optical", …)` returns None** — the
   deterministic display-ray feature pick misses the BS at that pixel (occluded
   by the LED shell), so the override is eligible but yields nothing.

A blind re-fix would again risk "guard passes, live still broken."

## This commit — instrumentation, not a fix

Record what every right-click actually resolved so the next recording pins which
branch fires:

- `Kraken3DInspector._right_click_pick_context` writes
  `self._last_right_click_debug = {cursor_xy, prior_hover_key, hovered_label,
  vtk_step_label, vtk_actor_key, override_eligible, override_context_label,
  override_fired}` on every right-click (before returning).
- `SceneSnapshot.right_click_diagnostics` (new field) carries it into the
  bug-repro `state.json` via the existing `asdict` serialization; the recorder
  populates it next to `hover_step_cell_key`.

## Next step (owed by the user)

Re-record the exact gesture: slide the BS into the LED, hover the splitting plane
until the gold outline is on it, **right-click**, then flag. The new
`right_click_diagnostics` block will show which of the three branches fired, and
the real fix (with a display-free guard + penta phase) follows from that.
