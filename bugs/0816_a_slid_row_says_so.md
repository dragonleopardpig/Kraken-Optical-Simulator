# 0816 -- a slid row says so

Follows bugs/0815, where the user found the om05a prism assembly haywire. The repair was the easy
part. The question this bug answers is why nobody knew.

## What went unsaid

bugs/0769 gave `om05a_folded.py` the sensor-standoff row the 80 mm bench already had:

```
RA mirror 2 (40 mm)  45.13  ->  36.31  +  sensor standoff 8.82      (sum preserved: 45.13)
```

The sum is preserved AT THE SENSOR, so everything that rides the chain to the end stays put, and
the note recorded "Nothing moves". Seven free-placed prism rows sit BETWEEN the row that lost the
8.82 mm and the row that gained it; their station, and their world z, dropped by exactly that.
bugs/0756 made the identical split on the 80 mm bench, saw it coming, and corrected those rows'
`desp_z` by the same amount. That correction never came over.

The scene then traced **6 rays of 1103** for weeks. The app drew it, solved on it and exported it
without a word, until the user opened it and said the prisms looked off centre.

## The instrument already existed

bugs/0750 built `scene_placement_audit` for exactly this class and measured **0.000000 mm on a
healthy scene against 8.5400 mm for the real defect**. Its own docstring says the ABSOLUTE reading
is red on rows whose authored snapshot is merely stale -- om05a has two such rows, the big RA
mirrors that bugs/0760 deliberately re-seated 3.563 mm to the vendor clearance -- and that the
DELTA form (`compare_drifts`) is "silent by construction on an unmoved scene and still shows
0.0000 -> 8.5400 on the break".

Silent on an unmoved scene, silent on a stale snapshot, loud on the break: that is a check that can
run on every model change. It was wired into guards only.

## Fix

* `services/scene_placement_audit.py` (pure, display-free):
  * `moves_since(before, after)` -- `compare_drifts` restricted to rows that are still the SAME
    row. `compare_drifts` pairs by row INDEX, which an edit preserves and a scene LOAD or a row
    insert does not; without the name check a load would report every renumbered row as moved.
  * `prune_resolved_moves(moved, current)` -- a flagged row stops being flagged once it is no
    further from its authored placement than it was before the edit, so an undo, a re-seat or a
    compensating edit clears the notice by itself.
  * `format_placement_move_lines(moved)` -- the in-scene notice, worst first, four rows then
    "... and N more". Micron resolution, and the walk's 1e-14 noise prints as the 0.000 it means.
* `open3d_inspector.py`:
  * `_pinned_placement_reading()` -- the per-row drift, row math only, never raises;
  * `_note_pinned_placement_moves()` -- called from `_apply_model_change` BEFORE the redraw, so
    the stored baseline is the scene as the user last saw it. Flags, writes the status line and
    the debug log;
  * `_refresh_pinned_placement_baseline()` -- called from `refresh_scene`, the single painter
    both the sync and the async (bugs/0223) traces funnel through: the painted scene becomes the
    next edit's baseline, and resolved rows drop out;
  * the notice rides the bugs/0717 solve banner.

It **reports**. Nothing is moved back: a promoted row is usually vendor hardware and where it sits
is the user's call ([[vendor hardware is immutable]]) -- bugs/0760's 3.563 mm is exactly such a
deliberate move, and this check stays quiet about it.

## Measured

Rendered with bugs/0769's edit re-applied at 5 mm through the real `_apply_model_change`
(`bugs/0816_placement_notice.png`):

```
PLACEMENT: the last edit slid 7 pinned row(s) off the authored placement they carry (worst 5.000 mm)
  row 16 First RA mirror B: 0.000 -> 5.000 mm off (+5.000)
  row 17 BS cube B: 0.000 -> 5.000 mm off (+5.000)
  row 18 Centre RA mirror B: 0.000 -> 5.000 mm off (+5.000)
  row 19 BS cube A (far half): 0.000 -> 5.000 mm off (+5.000)
  ... and 3 more
  Undo the edit, or move them back yourself -- the scene changed where they sit, and nothing was moved for you
```

The same scene before the edit, and after undoing it, shows no PLACEMENT line at all.

## Guard

`validate_open3d_0816_a_slid_row_says_so` (penta phase 595):

* A (pure): the slid row is reported while om05a's stale 3.563 mm row stays silent; an unmoved
  scene and a reading taken across a load report nothing; a returned row clears, a still-off row
  stays; the notice names row and amount and proposes no move.
* B (live, SKIP when the Filen-synced scene is absent): the REAL inspector methods on the user's
  scene -- a freshly painted scene is quiet, the sum-preserving leg split is caught on all seven
  prism rows at the right amount, undoing it clears the notice at the next paint, and an edit
  downstream of every pinned row says nothing.
* C: the wiring -- the chokepoint reads, the painter re-baselines, the banner carries the lines.

Phases 0-12 and 262 (the 2D-stale gate that shares `_apply_model_change`) pass unchanged.

## Still open

A seat that moves ON PURPOSE still has no way to be re-recorded: `StepOverlayPromotion.center_world`
is written only at promotion time, so bugs/0760's move left a snapshot nothing refreshes, and the
consumers anchored on it (the authored cover strips, phase 505's A8b) stay 3.563 mm behind. A
user-invoked "pin the current placement as authored" closes that; never automatic.
