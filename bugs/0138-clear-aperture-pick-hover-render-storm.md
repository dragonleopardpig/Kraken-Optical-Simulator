# 0138 — Set-Clear-Aperture pick mode renders on every mouse move (slow hover)

## Symptom

Recording `recording_20260625_073038.json`, flag `flag_20260625_072628_272`:

> *"significantly slow down after previous actions."*

After a run of operations (orient-row-to-ray, normal-axis pick, carry-hold, and arming
the clear-aperture pick), the cursor became sluggish. The flag's `scene_state` shows the
slowdown was felt while `interaction_mode == "step_clear_aperture_pick"`: from the flag
onward **every remaining mouse-move event** (~350 of them) is in that mode. Scene actor
counts were *not* accumulating (step bodies ~3, dims ~18, rays 0, handles steady) — so it
was per-move work, not a leak.

## Root cause

`open3d_inspector.py::_update_clear_aperture_hover_highlight` runs on every mouse-move
while the pick is armed (`open3d_interaction.py:832`). Its tail did two wasteful things:

```python
self._set_step_hover_outline(outline, ("clear_aperture", wanted, int(cell_id)))
...
try:
    self.render()        # <-- unconditional, every mouse pixel
except Exception:
    pass
```

1. **Unconditional `self.render()`** — a *full VTK scene render fired on every mouse-move*
   regardless of whether the highlighted face changed. `_set_step_hover_outline` already
   change-gates its own render (`_set_step_hover_outline_impl` returns early when the hover
   key is unchanged, and only renders when it actually swaps the outline actor), so this
   trailing render defeated that gate entirely. A render is O(whole scene); doing it per
   pixel is the slowdown.

2. **Per-pixel hover key** — the key embedded `int(cell_id)`, the picked **cell** under the
   cursor. `cell_id` differs pixel-to-pixel even when the cursor is on the body but **off**
   any clear-aperture window (`outline is None`). So the key kept changing, and
   `_set_step_hover_outline_impl` never hit its early-return — it re-cleared/re-rendered
   every pixel even when nothing was highlighted.

The Measure hover (`_update_measure_hover_highlight`) renders unconditionally too, but it is
justified there — Measure draws a rubber-band preview line that must track the cursor every
frame. The CA-pick hover shows only a **static face outline** that changes only when the
cursor crosses a face boundary, so a per-pixel render is pure waste.

## Fix

Key the hover on the **resolved face id** (a stable `None` whenever the cursor is off any
clear-aperture window) instead of the per-pixel `cell_id`, and **drop the unconditional
render** — let `_set_step_hover_outline`'s change-gate own it (`open3d_inspector.py`):

```python
outline = None
face_id = None
if hit_label ... and cell_id >= 0:
    fid = self.editor.clear_aperture_face_index_for_display_cell(wanted, cell_id)
    if fid is not None and int(fid) >= 0:
        outline = self._clear_aperture_outline(wanted, int(fid))
        if outline is not None:
            face_id = int(fid)
self._set_step_hover_outline(outline, ("clear_aperture", wanted, face_id))
# (no trailing self.render())
```

Now a render happens only on an actual highlight **transition** — face↔face or
face↔none — because the hover key only changes then; intra-face and off-face moves
early-return in `_set_step_hover_outline_impl` with no render. Many cells share one face
`fid`, so moving within a window no longer re-renders either. The picker `Pick()` per move
stays (it is the unavoidable cost of hover feedback, same as Measure), but the per-pixel
full-scene render is gone.

## Test

- `KrakenOS/UI/validate_open3d_clear_aperture_hover_render.py::run_checks` — display-free,
  source-contract:
  - `_update_clear_aperture_hover_highlight` no longer calls `self.render()` (it must defer
    to the change-gated `_set_step_hover_outline`).
  - its hover key is `("clear_aperture", wanted, face_id)` (the resolved face id), not
    `int(cell_id)`.
  - `_set_step_hover_outline_impl` still early-returns on an unchanged key and only renders
    under `if render:` (the gate this fix now relies on).
- Penta phase **128**.

## Status

Fixed; guard green standalone and in the penta harness (phase 128, display-free). In-app
eyeball owed — headless cannot drive the embedded-VTK hover, and the win is a *felt*
responsiveness gain (renders only on face transitions, not per pixel). The user should
confirm that, with Set-Clear-Aperture armed, sweeping the cursor over the body is smooth
and the window outline still appears/updates as faces are crossed.
