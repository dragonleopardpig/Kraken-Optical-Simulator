# 0546 — "tried to swap lens, but got error"

**Flag:** `attachment/recorded_bug_repros/flag_20260804_204450_689` (build `f0a4df6a`, dirty)
**Scene:** `attachment/machine_vision_AZ85_RA_Mirror_BS.py` — AZ85 (ELS-85-4.5V16K) + RA mirror +
cube beam splitter + hr25MCX camera + LED.
**Reported:** *"tried to swap lens, but got error, attachment/error.png."*

`attachment/error.png`:

> This scene has no imaging-lens surrogate (Front/Rear Vertex Datum) to swap.
> Use Add Imaging Lens to add one first.

…on a scene whose imaging lens is plainly in the 3D view, rays running through it.

## Root cause

`_imaging_lens_block_indices` finds the tight block correctly — `S1 Front Optical Vertex Datum`
… `S6 Rear Optical Vertex Datum` — and then **vetoes it**, because bugs/0381 taught it to refuse
a block whose interior holds a foreign element so a swap could never splice one away. The
foreign row here is `S3 Promoted OPTICAL STEP optical solid`: the beam-splitter cube.

The cube is not *inside* the lens in any physical sense. Row stations and poses from the flag:

| row | station | desp_z | pose z | name |
|----:|--------:|-------:|-------:|------|
| S1 | 130.635 | −76.831 | 53.803 | Front Optical Vertex Datum |
| S2 | 148.273 | −94.470 | 53.803 | Blackbox Group 1 |
| **S3** | **158.135** | **−103.676** | **54.459** | **Promoted OPTICAL STEP optical solid (BS cube)** |
| S4 | 158.135 | −104.332 | 53.803 | Aperture Stop F/4.5 |
| S6 | 185.635 | −131.832 | 53.803 | Rear Optical Vertex Datum |
| S7 | 288.905 | −235.102 | 53.803 | Promoted OPTICAL STEP optical solid (RA mirror) |

Its displayed bounds are x −38…45 while the lens sits at x 94…149 — the cube is **upstream of
the whole lens**. It landed at row index 3 only because `_step_overlay_insert_index` drops a
promotion after the **current selection**, and a promoted optical solid is **absolutely placed**
(`axis_move = 0`, pose = `station + desp_z`) so its row index carries no geometry at all.

So the 0381 veto fires on scenes it was never meant to protect: *any* scene where the user
promoted a solid while a lens row happened to be selected. Adding the BS is what broke the swap
on this scene — the earlier RA-mirror-only AZ85 scene put its promoted row at S7, outside the
block, and swapped fine.

## Fix

Refusing is the wrong answer; **preserving** is. The swap now lifts the foreign rows out and
re-seats them:

* `_imaging_lens_block_foreign_rows` splits the block interior into **preservable** (a promoted
  optical solid, and the in-path AIR spacer bugs/0079 pairs with one) and **blocking** (an
  Object / Image row — that span is not a lens block at all). Only *blocking* still vetoes.
* `_swap_preserved_block_rows` snapshots each preservable row with the **absolute** pose it
  holds now (`station + desp_z`).
* the splice becomes `rows[:front] + new_block + preserved + rows[rear+1:]` — the same row
  objects, so every `advanced` payload (face roles, splitter flags, glue, ScenePlacement) rides
  along untouched.
* `_swap_downstream_gap(..., extra_after=Σ preserved thickness)` — that thickness was already
  inside `downstream_start_z`, so the rear-datum gap must discount it or the whole downstream
  arm walks by it (18 mm in the guard's in-path case).
* `_swap_reseat_preserved_rows` runs **last**, after the gap write settles the stations, and
  rewrites `desp_z = pose_before − station_now`. Same compensation as bugs/0526's composite.

The block also comes out **clean**: the preserved rows now sit after the rear datum, so the next
swap on that scene sees no foreign interior at all.

## Scope note — fold sources

`build_optical_solid_output_port_pose_overrides` picks a fold source's followers by walking
rows FORWARD, so re-seating a lifted row after the block removes the lens's own rows from that
row's follower set. That is a non-issue here and for every beam splitter: bugs/0398 excludes a
marked BS from being a fold source at all, and the flag's own diagnostics confirm it —
`row 3: is_marked true, is_fold_override false`, `override_keys: []` (the scene is 0433-frozen,
so there are no overrides to disturb). A promoted **mirror** parked inside a lens block would
have its follower set change — but that configuration refused to swap at all before this fix,
and a fold source whose followers are the back half of a lens is incoherent either way.

Row-index-keyed leftovers (`last_constraint_target_row` and friends) can go stale after a swap.
That is pre-existing and general: any swap whose replacement lens has a different row count
already shifts every downstream index.

## Guard

`KrakenOS/UI/validate_open3d_0546_swap_keeps_inblock_solid.py` (penta phase 433) drives the
**real** `swap_imaging_lens_from_folder` with only the file I/O stubbed, over two scenes — the
flagged one and a variant whose in-block solid carries real chain thickness plus its trailing
spacer. It asserts the block is detected, both promoted rows survive, their poses hold to 1e-9,
the front datum and the downstream RA mirror keep their absolute stations, and the block comes
out clean. Non-vacuity checked by neutering each mechanism in turn:

| neutered | symptom the guard catches |
|---|---|
| `_swap_reseat_preserved_rows` | BS pose z 54.459 → 185.229 (jumps by the block length) |
| `_swap_preserved_block_rows` | the BS row is gone from the scene entirely |
| the `extra_after` discount | downstream station 301.043 → 319.043 |

`validate_open3d_lens_swap_block_safety` (phase 322) was updated: the promoted-inside case now
asserts the block IS exposed and the row is classed preservable, with a fresh case for the
scene-end veto that remains.

## Drive-by

`validate_open3d_swap_imaging_lens` (phase 318) had been **failing since bugs/0381** — its STEP
rewire section still asserted the pre-0381 "carry the fresh folder's pose" behaviour, reading an
attribute the rewire no longer sets, which on a bare stub recursed into Tk's `__getattr__`. It
now asserts the shipped contract (path + largest-component flag switch; the user's scene pose
preserved), and phase 318 passes.

## Repro

`bugs/repro_0546_swap_blocked_by_inblock_solid.py` — reads the user's saved layout, prints the
station/desp/pose table above, and shows `_imaging_lens_block_indices() -> (None, None)`.
