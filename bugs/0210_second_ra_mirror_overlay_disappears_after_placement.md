# 0210 — a re-imported RA mirror (same STEP as an already-promoted mirror) disappears after it is placed

**Status: FIXED (code + display-free guard + penta phase 187 + baseline). The 2nd optical
overlay now keeps drawing after the carry-drop instead of collapsing onto the promoted solid.**

## Flag

`attachment/recorded_bug_repros/flag_20260703_073100_231` (state.json):

> *"imported RA mirror disappear after random placed."*

This is a **different** failure from bugs/0209 (which was the 2nd mirror landing off-beam as a
*promoted row* and spraying rays, since fixed by 0208). Here the user imports the 2nd RA mirror as a
**STEP overlay**, carries it, drops it at an arbitrary pose — and it **vanishes on the drop**, while
its placement state is intact.

The captured flag state is the smoking gun:

- `step_actor_counts = {'lens': 1, 'camera': 1}` — there is **no `optical` actor drawn**.
- `step_overlay_poses['optical'].placement_offset_xyz = [42.0261, 144.9484, 123.863]` — yet the
  overlay's **placement survives**. It was placed, then dropped from the draw.

So the body is not deleted or moved off-screen; the refresh simply **stops drawing** the `optical`
overlay after the carry ends.

## Root cause

There is only **one** optical STEP-overlay slot (`STEP_OVERLAY_LABELS = ("lens", "optical",
"led", "camera")`; lens/led/camera are decoration labels). A generic optical STEP — an RA fold
mirror — can only occupy the single **`optical`** slot.

The scene refresh (`services/open3d_scene_refresh.py` ~986) skips any overlay whose source **FILE**
matches a promoted row:

```python
if (label != carry_label
        and self.editor._step_overlay_matches_promoted_row(label, promoted_step_source_keys)):
    continue   # do not draw this overlay body
```

`_step_overlay_matches_promoted_row` (`services/three_d_scene_tools.py` ~780) matches the overlay's
resolved source **path** (`_step_source_key`) against the set of promoted rows' source paths
(`advanced['OpticalSolidSourcePath']` &c.). That gate was added by commit **95615f05 "Suppress
promoted STEP overlay ghosts"** to kill the persisted **save/reload ghost**: a `.py` that keeps
`imported_optical_step_path` alongside a promoted row of the *same* file would otherwise double-draw
(overlay + promoted solid).

But the user's 2nd RA mirror is imported from the **same STEP file** as mirror 1, which is already
promoted to row 1 (carrying that file as its `OpticalSolidSourcePath`). The fresh `optical` overlay
shares that path, so `_step_overlay_matches_promoted_row("optical")` **false-positives**: it treats a
distinct live instance the user is placing as if it were the promoted row's leftover ghost.

While the overlay is **carried**, the gate's `label != carry_label` guard is False, so it draws.
The instant the carry ends (**drop**), the gate fires and the refresh drops the body onto the
promoted solid — the overlay "disappears after placed," exactly as flagged, with the pose left behind.

File-path matching cannot tell a *reload ghost* (same file, no live import) from a *live duplicate*
(same file, freshly imported this session). That missing object-identity bit is the bug.

## Fix

Supply the missing identity bit with a **runtime-only** flag. A fresh import that duplicates an
already-promoted part is marked an *independent live instance*; the gate returns False for a flagged
label so it keeps drawing.

- `services/three_d_scene_tools.py`: `_mark_/_clear_/_step_overlay_is_independent_instance(label)`
  over a `_step_overlay_independent_instance_labels` set; `_step_overlay_matches_promoted_row`
  short-circuits to `False` when the label is flagged (before the file-path compare).
- `services/step_overlay_import.py`: `import_optical_step` sets the flag when the freshly imported
  path is already a promoted source key, else clears it; `clear_imported_step_overlay_state` clears
  it (so **promote** or an explicit **clear** removes it).

The flag lives only in memory. The **persisted save/reload ghost is never freshly imported in the
session**, so it never sets the flag → it still matches by file and stays suppressed. The 95615f05
contract is preserved: `validate_open3d_saved_step_native_trace` (which sets
`imported_lens_step_path` for a promoted `lens` and asserts the ghost is suppressed) still passes,
and only the `optical` slot is ever flagged.

## Why not a pose / instance-id approach

- **Pose-coincidence gate** (draw the overlay only when its pose differs from the promoted solid)
  would break the reload-ghost contract test, which sets **no pose** — the ghost and the solid
  coincide there, yet it must stay suppressed. It would also fail the moment a user drops the live
  duplicate *onto* the promoted solid.
- **Instance-id threaded through persistence** is far more invasive and touches the penta-shared
  promote path; the runtime flag is the minimal change that adds exactly the missing bit.

## Verification

Display-free guard `validate_open3d_second_optical_overlay_survives_placement` (7/7 pass), on the
AZ85 scene, at the exact gate the draw loop consults:

1. row 1 is a promoted optical solid with a recorded STEP source path;
2. the reload ghost (same file, **not** freshly imported) stays **suppressed** (95615f05 contract);
3. a **live re-import** of the same part is flagged independent and **keeps drawing** — the fix;
4. **clearing** the flag reverts to suppression — non-vacuous / causal: proves the pre-fix path
   really dropped the overlay;
5. a **non-duplicate** optical import is never flagged and draws on its own merits (fix inert
   outside the duplicate case);
6. decoration labels (lens/led/camera) are never flagged (reload-ghost contract intact);
7. the refresh draw loop actually gates the overlay body on
   `_step_overlay_matches_promoted_row(label, promoted_step_source_keys)` (not vestigial).

**Penta-safe.** The gate/flag are STEP-overlay-label machinery the penta cascade never exercises
(the prisms use explicit output ports and never import a duplicate optical STEP);
`penta_cascade_prism_by_prism` PASSES under Xvfb after the fix. Registered as **phase 187**
(`phase_187_second_optical_overlay_survives_placement`), baseline set to `pass`. The full validator
marathon still SIGSEGVs on llvmpipe, so phases 0–186 are carried forward.

## Known limitation

The flag is runtime-only, so an **unpromoted** 2nd instance will not survive a save/reload (on reload
it matches by file and is suppressed again). That is acceptable for this unfinished workflow: the 2nd
mirror must be **promoted** to become a real optical element, and that promote+fold (the 2nd mirror's
CAD cube ref-point + detector fold-direction) is the deferred CAD-side task (#77, from 0208/0209).
Until then the placed overlay is a live decoration that draws correctly within the session.
