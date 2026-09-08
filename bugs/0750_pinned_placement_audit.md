# 0750 -- a guard for the edit that moves rows off their authored placement

bugs/0748 changed the SUM of the two lens sliding gaps in `om05a_folded_80mm.py`. Rows after those
gaps inherit the change through their station, so the whole arm-B block slid 8.54 mm while arm A
stayed put. The user flagged it twice -- "hay wired prism assembly", "Both big RA mirror is not
aligned as well" -- before it was found. bugs/0749 reverted it and established the rule: **the gap
SUM must stay invariant**, which is why the bugs/0719 FOV solve moves a thickness PAIR.

This is the guard. It keys on `advanced["StepOverlayPromotion"]["center_world"]` -- each promoted
row's AUTHORED world placement -- against the live follower-walk pose.

## Three designs measured and rejected first

The obvious guard was "check the arm A/B pairs stay mirror-symmetric about the split plane". A
parallel investigation plus three adversarial critics killed all three variants of it, on
measurement rather than opinion:

| design | why it fails |
|---|---|
| pair rows by an " A"/" B" name suffix | a relationship the codebase uses NOWHERE else; every existing A/B pairing is a hardcoded literal in a validator. Misfires on any unrelated pair ("Filter A"/"Filter B"). |
| absolute `z_a + z_b == 2 * split_plane` | red **at rest** on 2 of 8 pair-bearing scenes -- historical backups carry 1.0-2.9 mm of authored slop, and one authors `mirror_launch_plane_z = -28.9`, not -25. No single tolerance is both quiet on the corpus and able to catch a 1 mm typo. |
| "spread" of the pair midpoints | **blind to common-mode drift.** Measured: bump row 0's thickness +5 mm and all four pairs slide together -- spread stays 0.000000 while every mirror has moved 5 mm relative to the device it images. |

A fourth idea -- a banner note -- was rejected on evidence too: bugs/0745's MODEL MISMATCH **was
already on screen in the user's own screenshot** of this very bug and it still cost two flags. More
decisively, the actor who broke it was editing the `.py` file outside the app. A 3D-window banner
cannot reach that actor. The guard has to be runnable from a script.

## The invariant that survived

Measured on `attachment/om05a_folded_80mm.py`:

| | reading |
|---|---|
| promoted rows carrying an authored `center_world` | 12 (11 with a walked pose) |
| drift at HEAD | **0.000000 mm** on 10 of 11 |
| the exception, row 16 `RA mirror 2 (40 mm)` | 545.39 mm -- a pre-existing stale snapshot (authored x -272.7 vs live +272.683, a sign flip), NOT a new break |
| under the bugs/0748 gap-SUM edit | **exactly 7 rows at 8.5400 mm** -- the whole arm-B block |

No pairing, no split plane, no tolerance-vs-slop problem, and a 0.000000 floor against an 8.54 mm
signal. Use the **DELTA form**: a stale snapshot like row 16 makes an absolute reading red for
reasons that predate the edit, while the delta is silent by construction and still shows
0.0000 -> 8.5400.

## Shipped

* `KrakenOS/UI/services/scene_placement_audit.py` -- `pinned_placement_drifts`, `compare_drifts`,
  and two formatters. Pure, display-free; the follower walk can be driven from statically parsed
  rows, so no app is needed.
* `bugs/0750_check_scene_placement.py` -- the CLI for the actor who actually breaks this:

      python bugs/0750_check_scene_placement.py --check   <scene>
      python bugs/0750_check_scene_placement.py --compare <before> <after>

  `--compare` exits 1 when a row moved, so it can gate a commit. On the real defect it prints the
  eight moved rows and names the likely cause (the gap sum) and the safe alternative (the 0719
  thickness pair).
* `KrakenOS/UI/validate_open3d_0750_pinned_placement_audit.py` (penta phase 541), 13 checks
  including **D3: a thickness PAIR that keeps the SUM invariant moves nothing** -- the converse
  that proves why the FOV solve was always safe.

## A trap worth recording

A scene file stores each thickness TWICE -- `s8.Thickness = ...` and `'thickness': ...` inside the
`surfaces.append({...})` dict -- and the loader reads the DICT. My first attempt to build a broken
fixture edited only the `sN.Thickness` lines, so the "broken" scene loaded identical to the healthy
one and the guard correctly reported nothing. Edit both, or edit through the editor.
