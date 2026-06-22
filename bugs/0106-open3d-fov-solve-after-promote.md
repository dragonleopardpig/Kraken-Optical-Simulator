# 0106 — Clicking the FOV plane to change the FOV does nothing on a beam-splitter scene

**Flagged:** 2026-06-22 (`flag_20260622_141959_865` — *"After changing the FOV by
clicking the FOV plane, it does not take effect."*).

## The scene

MV 150mm 1X (finite-conjugate, machine-vision) with a **50 mm beam-splitter cube
BEFORE the single lens**; the transmit arm images through the 150 lens to the
camera, the reflect arm is a **bare pickoff** (no lens). One imaging arm.

## What the user did

Double-clicked the Object FOV plane → the FOV box opened → typed a new field
width → **"Solve for Thickness"**. Nothing in the scene moved.

## Root cause — a sibling of bugs/0104

"Solve for Thickness" runs a paraxial conjugate solve:

```
fov_solve("object","thickness") → _apply_conjugate_pair → _conjugate_pair
        → _paraxial_solution() → editor._exact_paraxial_solution_for_rows(editor.rows)
```

`_paraxial_solution()` solved the **raw rows**. On a beam splitter that raises:

```
RuntimeError: Paraxial solve supports centered refractive systems only
```

→ `_paraxial_solution()` returns `None` → `_conjugate_pair` returns `None` →
`fov_solve` returns `(False, "No real-image conjugate for that size…")`. The
status bar flashes that message and **no thickness is written** — exactly "does
not take effect".

This is the same family as **bugs/0104** (the object-plane magnification also
returned None because the conjugate solve threw on the splitter), but in a code
path 0104 never touched: 0104 fixed `_current_finite_paraxial_magnification`
(used by `_finite_mag` / the "Solve for Sensor Size" mode), while
`_paraxial_solution` — feeding focal length, the conjugate/thickness solve and
`is_forbidden` — still ran on the raw rows.

## Fix

Mirror 0104 in `KrakenOS/UI/services/quick_estimation.py`,
`_paraxial_solution`: straighten to the transmissive (straight-through)
reference whenever `_layout_needs_paraxial_reference()` is True (mirror OR beam
splitter OR promoted mesh solid) before `_exact_paraxial_solution_for_rows`:

```python
rows = self.editor.rows
solve_rows = rows
if self.editor._layout_needs_paraxial_reference(rows):
    solve_rows, _ = self.editor._paraxial_reference_rows_for_layout(rows)
return self.editor._exact_paraxial_solution_for_rows(solve_rows)
```

`_paraxial_reference_rows_for_layout` already replaces the splitter / mesh solid
with its transmissive flat-plate equivalent (the path every other first-order
consumer uses), so the single imaging arm's solve succeeds (effl ≈ 150 mm here)
and the FOV thickness solve writes the object/image gaps. Net positive: focal
length, working-distance/forbidden checks and the quick-estimation readout now
work on any splitter / promoted-solid scene instead of returning "--".

## "Shouldn't there be 2 FOVs due to the split?"

For this scene, no: the reflect arm is a bare pickoff (no lens → no real image →
no defined object FOV), so there is one imaging conjugate and one FOV rectangle.
If **both** arms imaged, each branch detector would define its own object FOV
(`sensor_semi / |arm magnification|`). The FOV feature today is single-conjugate
(`quick_estimation.py` has no per-branch awareness), so a true two-arm imaging
scene would only ever show/solve one. That per-branch FOV is a separate,
larger design item — deliberately out of scope for this fix.

## Repro / test

`.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_fov_solve_after_promote`
— display-free guard. Checks: (A) the splitter scene now yields a finite
`_paraxial_solution()`/`focal_length()` and `_layout_needs_paraxial_reference()`
is True; (B) `fov_solve("object","thickness",…)` returns ok=True and moves the
object gap; (C) a plain refractive MV 150 1X scene is unchanged and the
straightening is gated on `_layout_needs_paraxial_reference` (source check).
Confirmed the raw-rows solve raises `RuntimeError: Paraxial solve supports
centered refractive systems only` while the straightened path returns
effl ≈ 149.99 mm. Penta phase 92.

## Owed

In-app eyeball: the actual click-on-plane → FOV change taking visible effect
still wants a user confirm (headless can't drive the VTK double-click / render
the machine-vision scene).
