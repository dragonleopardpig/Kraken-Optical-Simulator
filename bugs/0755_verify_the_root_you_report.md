# 0755 -- verify the root you report, and measure it before the solve moves anything

Flag `20260908_154430_151`: "change device size to 55x55mm, image plane still not landed on
sensor." The scene's own banner carried the bugs/0754 line, and it was **wrong**:

```
This track DOES focus a 96.89 x 96.89 mm object field (|m| 0.2378)
  -- ask for that and the image lands on the sensor
```

The traced in-focus field is **54.09 mm**. `image_delta(0.2378)` is **-15.53 mm**, not 0.

## Two causes

Dumping `_folded_conjugate_gaps_for_magnification(m)["image_delta"]` shows it is monotonic with
exactly ONE root, at |m| 0.4260 -> 54.085 mm -- which matches the trace to 0.04 mm. Everything
below that root is flagged `image_side_unreachable=True`.

1. **The scan never honoured that flag and never checked its own answer.** It bracketed a sign
   change and returned the midpoint. A focus claim that is not evaluated against the model it
   came from is a guess.
2. **It ran after the solve had already moved the lens** (`+13.03 mm along its leg`). The
   "current track" it measured was a transient state nobody is looking at. Reproduced: the
   post-move state genuinely roots at |m| 0.2681 -> 85.93 mm.

## Fix

* The scan skips magnitudes the model marks unreachable.
* Every bracketed root is re-evaluated: accepted only when `|image_delta| <=
  _ROOT_RESIDUAL_TOL_MM` (0.1 mm, inside the 0.153 mm one-pixel depth of focus) **and** the
  state is reachable.
* `_apply_conjugate_pair` snapshots the field on ENTRY, before any geometry is written, and
  stashes that snapshot.

## Result

```
before:  This track DOES focus a 85.93 x 85.93 mm object field (|m| 0.2681)
after:   This track DOES focus a 54.05 x 54.05 mm object field (|m| 0.4262)
traced:  54.090 mm
```

## Guard

`validate_open3d_0756_camera_focus_stage.py` section A/B (penta phase 545), including a model
that never crosses zero and one whose only sign change sits in an unreachable region -- both
must yield no field rather than a bracket artefact.
