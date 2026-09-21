# 0845 -- a gap the scene declares signed survives a reload

Found by refusing to ship bugs/0844 on a reconstruction. The stage-first fix worked on the path
I rebuilt (shipped scene -> 21 mm solve -> 52.5 mm solve) and did **not** work on the user's own
saved `attachment/om05a_folded_refusal.py`: the predicted stage move came out -2.99 mm where
+75.35 mm was needed, and a 21 mm solve from that file parked the Filter **3.9 mm inside the lens
barrel**.

## What was measured

The file differs from the shipped one in five numbers. Four are the solve's; the fifth is

    row 23  sensor standoff   thickness   8.82  ->  -78.3343391747

The camera stage (bugs/0759) had travelled 87.154 mm toward the lens. It moves the imaging group
rigidly while keeping every downstream station fixed, and the only way the chain can say that is
a carry pair plus the SAME delta on the standoff -- so a move longer than the 8.82 mm standoff
drives that row negative **by design**. The scene says so itself:

    'camera_focus_stage': {'enabled': True, 'row': 23, 'min_mm': -171.65, 'max_mm': 30.42, ...}

On load, `_heal_negative_gaps_on_load` (bugs/0559) zeroed it and returned the amount through
every follower's `desp_z`. Its docstring says "nothing moves", and for the WORLD that is true --
every reference point came back identical. The FIRST ORDER sums thicknesses and never reads
`desp_z`:

                                          first-order image track      world image track
    live session (-78.334 written live)        156.92 mm                   156.92 mm
    saved -> reloaded (healed to 0.0)          235.26 mm                   156.92 mm

    first-order image_delta at the CURRENT |m|:   live +22.38 mm    reloaded -55.95 mm

So after any reload the solve believed the sensor was 78.33 mm from where it is. Every image-side
booking was wrong by that much; the traced-focus finisher then dragged the sensor back
("Focus: residual -78.2 -> +0.1474 mm") while the stage -- Filter included -- stayed 78 mm too
close to the lens. **Save, reload, solve: a different machine.**

A trap on `SurfaceRow.__setattr__` named the writer in one run:
`load_layout_by_name -> _heal_negative_gaps_on_load`, `-78.3343391747 -> 0.0`.

## The fix

`_declared_signed_gap_rows(info)` reads the scene's own declaration and returns
`{row: floor_mm}` -- today one source, an enabled `camera_focus_stage` whose `min_mm` is
negative. `_heal_negative_gaps_on_load(rows, signed_rows)` leaves such a row exactly as saved
**down to its declared floor**. Below the floor, and for every other negative gap, it is still
the corruption bugs/0559 repairs. Both loaders pass it (`open_layout` and
`load_layout_by_name` -- the bugs/0563 two-loader trap).

A gap is signed exactly where, and as far as, the scene states it. "A gap may never be negative"
stays the rule for every row nobody declared.

## Guard

`validate_open3d_0845_declared_stage_gap_survives_reload.py`, display-free, penta phase 624.

- **C** CONTROL: healed the old way the world is kept and the first-order track jumps +78.3343
- **K** with the declaration the row and every follower's `desp_z` are byte-identical
- **B** -200 mm is below the declared -171.65 floor: healed
- **O** an undeclared negative gap beside it is still healed
- **D** no stage / disabled / non-negative floor / malformed: nothing declared
- **R** the user's saved scene: standoff survives, first-order track 156.921 mm = the world's.
  Rebuilt from `om05a_folded.py` plus the five values the user's file saved, because that
  file (`om05a_folded_refusal.py`) is being deleted -- a guard that SKIPs on a missing file
  would have lost this check without anyone noticing
- **W** both loaders pass the declaration (executable lines only)

## A harness lesson, recorded because it cost the machine ten minutes

The first real-scene re-run sat at 1.7 % CPU in `futex_do_wait` while the load average went to
~60. The preview trace can use a `spawn`-context worker pool, spawn re-imports the launching
script in every worker, and my probe had no `if __name__ == "__main__":` -- so each worker
re-ran the whole probe, building an editor. Earlier probes never hit the pool path, which was
luck, not safety. `bugs/diag_0844_path_independence.py` is guarded.
