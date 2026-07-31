# 0493 — a Live-Mode drag ended without ever redrawing the carried leg

`flag_20260731_222802` (build `141abba7`) — *"glued BS + LED dragged down, no elements follow."*
Recorded on the build whose bugs/0491 guard passes.

Its sibling `flag_20260731_222930` — *"glued → save layout → restart, still glued, it works"* — is a
**confirmation**, not a defect: bugs/0492 verified in the live app.

## Why the 0491 guard passed while the app was broken

That guard drives the programmatic apis (`translate_scene_row_pose`, `translate_step_overlay`), and
through those everything follows. The user drives the gizmo, and with **Live Mode on** the release
path is different:

1. `_flush_pending_placement_drag_for_live` commits the accumulated offset **mid-drag** and zeroes
   `pending_translate_mm` — bugs/0024, so the live trace reflects the dragged pose.
2. That commit runs the fold carry: the whole emitted leg moves in the model and
   `_fold_carry_pending_rebuild` goes up.
3. `_refresh_live_preview_scene` mid-drag refreshes **rays only**:

   > `# bugs/0024: mid-placement-drag, the bodies/handles don't change (the dragged one tracks the`
   > `# cursor via its cheap actor transform) ... The full scene rebuilds on release.`

   True when it was written. False from the moment a carry started moving *other* bodies.
4. On release `_finish_placement_drag` reads `pending ≈ 0` — already flushed — so it skips the
   commit **and `_apply_scene_placement_translate_handle` with it**, which is the only thing on that
   path that would have called `refresh_from_editor`. The full rebuild the comment promises never
   happens, nothing consumes the marker, and the drawing never catches up.

Reproduced headlessly by holding the button (letting queued refreshes fire while the drag state is
still set, which is what routes them into the rays-only branch):

```
MODEL row3 / row5 / row7 desp_z   +13.681      the whole leg, not just promoted rows
row actors 0..8, 100000            unchanged
STEP lens / camera / led           unchanged
axis:global:split                  still z 53.80
marker still pending at the end    True
```

which is `flag_20260731_222802` exactly — its row 3 actor sits at z[30.31, 105.97], the same value
this reproduction produces. Not a slow rebuild either: 88 s and a second drag later,
`flag_20260731_222930` still showed the same stale chain.

## Reading the flags: what the recorder does and does not dump

`state.json` records `desp` only for rows carrying a `StepOverlayPromotion`
(`open3d_event_recorder.py`), and rows 3 and 7 are the only promoted rows in this scene. Rows
1,2,4,5,6,8 have **no model field in the snapshot at all**. So "only the promoted rows moved" is an
artifact of what the recorder dumps, not of the carry — an inference I made from
`flag_20260731_222930` and had to withdraw. The carry moves every row on the emitted leg:
`rows_on_emitted_leg(3)` returns `[1,2,4,5,6,7,8]`, membership decided geometrically by
nearest-segment projection in `optical_axis_tree.snap_rows`, not by promotion. Everything else in a
snapshot (`row_actor_bounds`, `step_actor_bounds`, `optical_axis_records`) is drawn state, and that
is where the defect actually was.

## Fix

`left_release` has **eight** `return "break"` exits across its branch chain. Patching the one that
mattered would have been the fifth time this family was fixed one entry point at a time (bugs/0487
hooked only `translate_scene_row_pose_vector`; bugs/0488 then omitted both rotate forms; bugs/0491
took three attempts). So the branch chain moved into `_left_release_body` and `left_release` became
a wrapper:

```python
try:
    return _left_release_body(event)
finally:
    self._flush_fold_carry_rebuild_after_drag()
```

`_flush_fold_carry_rebuild_after_drag` returns immediately unless every drag state is clear **and**
`_fold_carry_pending_rebuild` is set, then calls `refresh_from_editor` — which consumes the marker
and promotes itself to a forced retrace. Keying on the marker keeps bugs/0024's bargain: a drag
that carried nothing pays nothing, and only a fold move buys the rebuild.

After the fix, on the same reproduction: rows 1–8 and 100000 `+13.68`, STEP lens and camera
`+13.68`, all three axis records `+13.68` with `axis:global:split` 53.80 → 67.48, row 0 and the LED
housing correctly still, and the marker consumed.

## Guard

`validate_open3d_0493_live_drag_release_redraws.py`, penta phase 398 — the path bugs/0491's guard
does not exercise. Section A holds the structure: the try/finally wrapper exists, the chain lives in
`_left_release_body` so a *new* branch is covered by construction, and the flush is keyed on the
marker and never fires mid-drag. Section B drives the real gesture with Live Mode on — mid-drag
flush, held button, release — and asserts on the DRAWING. Against the pre-fix code section A fails
and section B cannot even run (the method does not exist).

## Still open, found alongside

Four more writers move rows or overlays **without** the carry. None is implicated in this flag, and
each needs its own scene to provoke:

| path | file:line |
| --- | --- |
| `_carry_glued_optical_led`, overlay-partner branch — an *un-promoted* `optical` STEP BS writes its placement offset and returns | `scene_placement_commands.py:3616` |
| `translate_step_overlay` detector-thickness write — `rows[-2].thickness +=` relocates the Image row and every station downstream | `scene_placement_commands.py:3895` |
| `translate_step_overlay` lens front-gap write — same class | `scene_placement_commands.py:3903` |
| `slide_lens_along_axis` — rewrites preceding/trailing thicknesses, no carry hook | `scene_placement_commands.py:611` |

A thickness write is the common shape: it relocates fold rows without ever touching `desp`, so no
`translate_*`/`rotate_*` hook sees it. The carry is currently wired into exactly four methods —
`translate_scene_row_pose_vector`, the axis-form `translate_scene_row_pose`, `rotate_scene_row_pose`
and `rotate_scene_row_pose_world_axis`.
