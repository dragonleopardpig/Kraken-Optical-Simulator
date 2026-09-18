# 0818 -- the Show Rays box states the scene, on every path

User, after bugs/0801: "I still see Rays ON is tick but no rays is actually on. I have to untick and
tick to make it work. I randomly open .py files."

## Measured

A fresh load then Open 3D, settled 8 s (past the STEP cache warm-up), on `attachment/om05a_folded.py`:

| | ticked | fast-load gate | ray actors |
|---|---|---|---|
| after open | **True** | True | **0** |
| after loading another .py into the open window | **True** | True | **0** |
| after loading the first one back | **True** | True | **0** |
| after the user's untick + tick | True | False | 12 |

The same probe on `machine_vision_double_gauss.py` opened correctly -- box off, and the status line
explaining why. The difference is the point.

## Why bugs/0801 did not cover it

0801 put the rule in the right place for the case it measured -- `open_3d_view` calls
`_pending_rays_note`, which unticks the box when the bugs/0646 fast-load gate is set. Two paths walk
around it:

* **The 3D-session sidecar re-ticks it.** `refresh_from_editor` begins with
  `_maybe_restore_open3d_session_state()`, which re-applies every saved overlay toggle --
  `_SESSION_TOGGLE_VAR_NAMES` includes `show_rays_var`, and `attachment/om05a_folded.open3d.json`
  carries `"show_rays_var": true`. So the refresh that follows the untick puts the tick straight
  back. A scene with no sidecar (double_gauss) was fine, which is exactly the "I randomly open .py
  files" pattern: it depends on the file, not on what the user did.
* **A load into an already-open inspector never runs the open path.** The status line says "Loaded
  b (rays not traced -- fast load). Click Trace Now for rays" while the box still reads on.

Both leave a control claiming something the scene does not show, which is the complaint 0801 was
raised on in the first place.

## Fix

`Kraken3DInspector._sync_show_rays_toggle_to_scene()` holds the rule, and `refresh_scene` -- the one
painter both the sync and the async (bugs/0223) traces funnel through -- calls it after each paint.
The session restore no longer gets the last word, a load into an open window is covered, and any
future refresh entry inherits it. `_pending_rays_note` now delegates to the same implementation
instead of repeating it.

It can only turn the box **off**. Asking for rays stays the user's: ticking is still the deliberate
request that clears the gate and traces (bugs/0801), which is what keeps bugs/0718's protection --
the in-process non-sequential trace can wedge the UI on crashed geometry, so no incidental refresh
may clear the gate.

## Measured after

| | ticked | gate | ray actors |
|---|---|---|---|
| after open | False | True | 0 |
| after ONE tick | True | False | **12** |
| after an ordinary repaint | True | False | 12 |
| after untick | False | False | 0 |
| after loading another .py into the open window | False | True | 0 |

## Guard

`validate_open3d_0818_the_rays_box_states_the_scene` (penta phase 597), display-free, the real
method driven through a shim:

* A: the box goes off exactly once when the gate is set and it reads on, with a note saying how to
  get rays; nothing is written when it is already off or when the scene traced; the implementation
  contains no `set(True)` at all.
* B: the painter enforces it, the session restore runs at the start of a refresh (so the painter has
  the last word), `show_rays_var` really is among the restored toggles -- the root cause, pinned --
  the open path delegates, and bugs/0801's tick-clears-the-gate is intact.

Phase 584 (the bugs/0801 guard) failed on this change for a reason worth recording: its fake
inspector carried only `show_rays_var`, so once `_pending_rays_note` delegated, the call raised
inside the guard's own fixture and the untick never happened. The fixture now carries the real
method bound to the fake ([[a guard must keep up with what it guards]]). Phases 8, 584 and 597 pass.
