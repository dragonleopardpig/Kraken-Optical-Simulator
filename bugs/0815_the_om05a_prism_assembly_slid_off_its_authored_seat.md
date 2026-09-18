# 0815 -- the om05a prism assembly slid off its authored seat, and a save that wrote the table

User: "I examine om05a_folded.py, the Prism Assembly itself hay wired, the prisms are all off
centered, this is previous bug. I think we already have a correct prism assembly, just copy the prism
assembly from om05a_folded_80mm.py." -- then "the 80mm .py file is where I purposely inverted the big
RA mirror and changed a imaging lens", and "have you updated om05a_folded.py prism assembly? Can I
examine the file on 3D scene?"

## Correction to the first draft of this bug

The first version of this file reported "row 7 RA mirror 1 3.563 mm, row 16 RA mirror 2 541.8 mm" as
drifts of `attachment/om05a_folded.py`. They are not: those numbers come from penta phase 541, whose
guard reads

```python
# validate_open3d_0750_pinned_placement_audit.py
SCENE = PROJECT_ROOT / "attachment/om05a_folded_80mm.py"
```

-- the **80 mm bench**, where the 541.8 mm is the user's deliberate inversion of the big RA mirror
(authored -272.7, live +269.12). Phase 505's guard is the one that reads `om05a_folded.py`.

## Measured -- on om05a_folded.py itself

`scene_placement_audit.pinned_placement_drifts` on the saved scene:

| row | name | authored centre | live centre | drift |
|---|---|---|---|---|
| 7 | RA mirror 1 (50 mm) | (0, 52.800, -25) | (0, 56.363, -25) | 3.563 mm |
| 15 | RA mirror 2 (40 mm) | (-272.7, 52.75, -25) | (-269.14, 56.31, -25) | 5.039 mm |
| 16-22 | First RA mirror B, BS cube B, Centre RA mirror B, **both** BS far halves, **both** LED panels | -- | 8.82 mm low in z | **8.820 mm each** |
| 3, 5 | BS cube A, Centre RA mirror A | -- | -- | 0.000 mm |

Seven rows -- the whole B-side train plus the two far halves and the two LED panels, i.e. every
promoted row after RA mirror 2 in row order -- sat 8.820 mm off in z. That is the bugs/0748 shape: an
upstream chain edit slides the station every free-placed follower is placed against, and each one
keeps its `desp_z`, so the assembly walks off the part.

**The two files record the SAME authored centres** -- all twelve promoted rows, |Δ| = 0.000 mm -- and
in `om05a_folded_80mm.py` those seven rows read 0.000 mm drift. So "re-seat each row onto its own
authored placement" and "copy the prism assembly from the 80 mm file" are the same instruction, and
the result can be checked against the bench pose for pose:

```
First RA mirror B (0, 0.42, -59.0)    BS cube B (0, 12.52, -57.25)   Centre RA mirror B (0, 14.0, -30.97)
BS cube A far half (0, 12.59, 7.32)   BS cube B far half (0, 12.59, -57.32)
LED panel A (0, 27.07, 4.95)          LED panel B (0, 27.07, -54.95)
```

## The repair reported success and saved nothing

The first pass loaded the scene, corrected the seven rows' `desp_z`, re-measured (`drift 8.820 ->
0.000000` on every one) and called `_write_layout_file`. The saved file still carried the old
placement -- identical `desp_z` to the backup, and the audit read 8.820 again.

`LayoutFileWriterService._write_layout_file` starts with

```python
def _write_layout_file(self, path: Path) -> None:
    self._read_rows_from_table()
```

The **table** is the writer's source of truth. Rows edited in memory and saved without
`_sync_table()` are overwritten by the stale table, with no error and no note -- the measurement
before the save is of rows the save then discards. The lens refit hit this in bugs/0591/0608 and left
the sync in with a comment naming it; it is now a test (below).

Re-seated through `_sync_table()`, the file on disk carries the move: seven `desp_z` values +8.82 mm,
every one of the seven rows at drift 0.000000 and on the 80 mm bench's pose. Backup of the scene as
it was: `attachment/om05a_folded.pre0816_backup.py`.

## What the re-seat did to the physics

| | before (backup) | after |
|---|---|---|
| 3D scene banner | "no ray reaches the sensor, so the image plane cannot be measured (1464 missed image, 742 stopped at surface 0)" | "the image forms 0.4566 mm in front of the sensor -- spot 0.199 um there vs 18.9 um on the sensor" |
| phase 505 B1 | 6 of 1103 reach, 0 on-strip | **644 of 1103 reach, 644 on-strip** |
| phase 505 B2 | best y -1.18, rms 127273.6 um | best y 2.27, **rms 0.7 um**, 212 rays |
| phase 505 B5 | 0 reach | 644 reach |

The scene was never mis-traced: the prisms were in the wrong place and the light went where they sent
it. Rendered both ways (`scratchpad/om05a/before_left.png`, `after_left.png`).

`split_field_arm_offset_mm` is now declared (8.778, the value the 80 mm bench declares). It is
bugs/0776's scene-declared ruler for the strip-position law, a property of this bench, and both files
are the same bench; it adds a check and moves nothing.

## Still open -- the two big RA mirrors' authored snapshot is stale

Rows 7 and 15 keep their 3.563 mm gap, and phase 505's A8b now reports the same 3.563 mm on the
measured cover strip: live A centre (-269.087, 1.822) vs the authored (-272.650, -1.655).

The evidence says the **snapshot** is stale, not the mirror: `om05a_folded_80mm.py` carries the same
live pose (56.363) for RA mirror 1 and images through it, and this scene now delivers 644 on-strip
rays with it. `StepOverlayPromotion.center_world` is only ever written at promotion time, so a row
seated after promotion keeps a snapshot that nothing refreshes -- and every consumer anchored on it
(the authored cover strips, the 0750 audit) stays 3.563 mm behind. Moving vendor hardware to satisfy
a snapshot is exactly what [[vendor hardware is immutable]] forbids; the missing piece is a
user-invoked "pin the current placement as authored". That is the next item, not this fix.

## Guards

`validate_open3d_0815_a_save_writes_the_table` (penta phase 594):

* A1: an edit made on `editor.rows` alone does NOT reach the saved file (the writer re-reads the
  table first) -- the trap, stated as a contract;
* A2: `_sync_table()` then save persists it;
* B1: `_write_layout_file`'s first act is still `_read_rows_from_table()`;
* B2: the bugs/0591/0608 lens refit still syncs before it returns;
* C1: all seven re-seated assembly rows sit on their authored centre (SKIP when the Filen-synced
  scene is absent).

`validate_open3d_0672_om05a_folded_scene` (phase 505):

* A8 asserted the pre-bugs/0721 band range (v -5.25..+3.1) although `symmetrize_face_bands` centres
  every device-face band on its face at load -- the scene has read -4.175..+4.175 since 0721 and now
  saves that way. It asserts the 8.35 mm SPAN and the symmetry instead, and passes.
* A8b prints what the live strip measured and by how much it misses the authored one, so the red row
  names the 3.563 mm above instead of a bare label.
