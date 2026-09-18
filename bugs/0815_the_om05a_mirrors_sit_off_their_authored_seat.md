# 0815 -- OPEN: the om05a scene's two big RA mirrors sit 3.563 mm off their authored seat

Found by the validation census ("fix them all"): penta phases 505 and 541 both read the user's
`attachment/om05a_folded.py`, and both report the same thing from different angles.

## Measured

`scene_placement_audit.pinned_placement_drifts` on the saved scene (2026-09-11 21:33):

| row | name | authored centre | live centre | drift |
|---|---|---|---|---|
| 7 | RA mirror 1 (50 mm) | (0, **52.800**, -25) | (0, **56.363**, -25) | **3.563 mm** |
| 16 | RA mirror 2 (40 mm) | (-272.7, **52.750**, -25) | (269.12, **56.313**, -26.7) | 541.8 mm (long-known stale snapshot; its y offset is the same 3.563 mm) |
| 3, 5, 17, 18, 19, 20, 21, 22, 23 | BS cubes, centre mirrors, LED panels | -- | -- | **0.000 mm** |

So both big RA mirrors sit 3.563 mm high in y while every other promoted row sits exactly on its
authored placement. The guard for bugs/0750 exists to catch precisely this ("an edit that moves rows
off their AUTHORED placement is caught"); it was written 2026-09-08 and the scene was saved on the
11th, so the drift arrived with that save.

## Consequence (phase 505)

With the two mirrors off the arm, the chain no longer delivers:

| check | measured |
|---|---|
| B1: the chain delivers the arm-A strip at z ~ -28.9 | **6 of 1103 rays reach; 0 on-strip** |
| B2: central-field waist < 200 um | best y -1.18, **rms 127273.6 um** |
| B5: faceB reaches its strip at z ~ -21.6 in focus | **0 reach** |
| A8 / A8b: both part faces carry the calculated FOV band and its measured cover strip | not authored |

The scene is otherwise intact: twelve optical-solid rows, mirror2 free-placed at the part-anchored CAD
pose, the three B-side stations end-inserted, the SV25 camera registered, the faceB source additive and
mirrored, the part anchoring the world, and the chief folding the true S (+z, +y, -z) -- A1-A7, B3 and
B4 all pass.

## Not fixed here -- it is the user's hardware placement

Re-seating the two mirrors is a change to the user's scene, and vendor hardware is theirs to move
([[vendor hardware is immutable]]). The options are:

* re-seat rows 7 and 16 onto their authored y (52.800 / 52.750) -- restores the authored geometry;
* re-author the snapshots at the live y (56.363) if the 3.563 mm is a deliberate adjustment -- then
  the rest of the arm needs the same offset, or the beam still misses;
* leave it and treat phase 505 as a red flag on the scene, which is what it now is.

Phase 541 no longer hides it: its check reports EVERY row off its authored placement (rows 7 and 16),
where it used to name row 16 alone.
