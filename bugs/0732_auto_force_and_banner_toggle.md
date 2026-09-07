# 0732 — apply the forced move without a second click; let the banner get out of the way

Two live asks on build ce8c82d3, plus a wart the user's own screenshot exposed.

## 1. "There is no need to have additional click on Force, just do it."

A COLLISION refusal used to stop the solve and wait for the user to pick
"Force FOV (show collision)" from a right-click menu. Now `fov_solve` escalates by itself: when
`translate_lens_block_along_leg` refuses for ROOM, it re-runs the move with `force=True` and
reports what happened. Every other refusal still stands (no lens block, a parked solid inside the
block, no conjugate at all) — only the room gate escalates, and only after the plain attempt has
been tried.

Measured on om05a, FOV 5 × 5 (needs 192.3 mm of leg against 158.9 mm of room):

```
ok=True   gaps (180.47, 17.93) -> (0.001, 198.399)
FORCED SOLVE APPLIED -- the lens PENETRATES hardware (inspect the 3D overlap)
lens must move -192.3 mm along its leg; room available 158.9 mm (short by 33.32)
FORCED: lens PENETRATES RA mirror 1 (50 mm) by 21.53 mm (158.9 mm of physical room)
FORCED: move capped at the fold mirror station (requested 192.3 mm, drawn 180.5 mm)
trace deferred = True
```

The trace deferral now follows what ACTUALLY happened rather than the caller's `force` flag —
`solve_fov_to_inspection_face` reads `solve_banner_outcome(...) == "forced_crash"`, so an
auto-applied crash still gets the bugs/0718 protection (a crashed geometry hangs the
non-sequential trace).

This supersedes the "offer FORCE-bypass so the user SEES the collision" half of
[[feedback_no_silent_solve_failure]]: the collision is still shown, it just no longer needs a
second click.

## 2. "the red banner is kind of static on the screen, blocking the view"

* `Solve / focus banner` is now a checkbutton in the 3D view menu (default ON). Hiding it costs
  nothing — the same text stays on the status line.
* the background opacity drops 0.92 → 0.78 so the scene shows through.

## 3. The contradiction in the user's "after the Force" screenshot

The banner read `FORCED SOLVE APPLIED -- the lens FITS: nothing collides` **and**
`SOLVE: ... the lens did not move -- the field was already delivered` together. The FORCED lines
were preserved state from an earlier Force (bugs/0727 keeps a forced banner across a no-op).
A forced move that merely FITS is finished business, so a no-op now preserves only a forced
CRASH — that overlap is still on screen and must stay called out.

## Guard

`validate_open3d_0732_auto_force_and_banner_toggle` = penta phase 531: A the escalation is wired
to the room refusal only, after the plain attempt, and a failed forced attempt leaves the original
refusal standing; B the deferral follows the actual outcome; C the banner toggle, its menu entry
and the lighter background; D a no-op keeps only a forced crash.
