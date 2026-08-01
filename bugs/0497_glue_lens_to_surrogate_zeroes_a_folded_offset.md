# 0497 — "glue surrogate to LED" zeroes the lens offset, which is only right on an unfolded scene

`flag_20260801_195042` — *"glue surrogate to LED misplaced the Lens STEP."* (build `865d3afc`).
This is the recurrence of the earlier backlog item `flag_20260726_192720` ("clicking glue-surrogate
misplaces the lens"), now with an exact signature.

## Measured

```
lens placement_offset_xyz   [97.41, 0, -105.10]  ->  [0.0, 0.0, 0.0]
STEP lens bounds            x[67.81, 127.00] z[27.63, 82.63]
                        ->  x[-29.60,  29.60] z[132.73, 187.73]
```

The offset is zeroed and the body lands on the nominal +Z axis near the origin.

## Root cause

`glue_step_overlay_to_surrogate` clears the offsets outright:

```python
self._set_step_axis_offset_xy(label, (0.0, 0.0))
self._set_step_placement_offset_xyz(label, (0.0, 0.0, 0.0))
```

on the stated assumption that *"for a lens or an LED the zero-offset default IS the auto-aligned
station"*. That holds on an **unfolded** scene, where the surrogate sits on the nominal +Z axis. On
this folded scene the lens sits on the splitter's SPLIT axis (along +X at z ≈ 55), so its correct
offset is `[97.41, 0, -105.10]` and zero is nowhere near it.

bugs/0475 already met exactly this failure — for the **camera** — and its comment says so: *"with a
zero offset the body seats on the NOMINAL axis, which on a folded scene is nowhere near the sensor
... Clearing the offset here therefore did the opposite of the menu's promise"*. The fix there was
to delegate to `seat_camera_on_sensor`, *"a RELATIVE correction computed from the body's current
bounds, so it lands from ANY starting offset and never needs the destructive zeroing step."*

That carve-out was written for one label. The lens (and the LED) still take the destructive path,
and on a folded scene they hit the identical bug.

Note the second-order trap 0475 also documented: once the offset is all-zero, the `already_glued`
short-circuit refuses every retry, so the body is **stranded** — a second click cannot recover it.
Ctrl-Z is the only way back.

## Fix — PARTIAL, shipped with a measured residual

`_seat_step_body_world_center(label, target)` is already the relative seater this needs: it reads
where the body actually sits and corrects by the **residual**, so it lands from any starting offset
(bugs/0456). The camera's fix used the same property. What is missing is the **target**.

"Front datum on the surrogate" is not literally the body's front face. Measured on this scene while
correctly glued:

```
lens STEP body      x[67.81, 127.00]   centre 97.405
front datum (row 1) x 71.66            rear datum (row 6) x 126.66   midpoint 99.16
```

so the body's centre sits **1.755 mm before** the datum midpoint, and its front face 3.85 mm before
the front datum. That asymmetry is a property of the CAD, not of the scene, so it is the same in any
orientation — which is what makes a general target computable:

1. Read the body's world centre at **zero offset** → `C_zero`.
2. `k = (C_zero − datum midpoint on the nominal axis) · ẑ`.
3. Take the surrogate's datum midpoint and leg direction **as they actually sit** → `M_now`, `d̂`.
4. `target = M_now + d̂ · k`, then `_seat_step_body_world_center("lens", target)`.

**Steps 1–2 do not survive contact with a frozen scene, and the shipped code inherits that.**
Measured:

```
c_zero (offset 0)              [0, 0, 160.230]     -- the nominal +Z line, not a designed pose
datum stations                 130.635 / 185.635   -> nominal midpoint z 158.135
datum rows' desp_z             -76.831 / -131.832  -> station + desp = 53.803 = their WORLD z
k from the nominal frame       +2.096
k measured from the glued pose -1.753
```

The datum rows' `desp_z` **already encodes the fold**, so "where this row would be on the nominal
axis" is not a separate quantity to recover `k` from — station + desp is simply the world position.
`c_zero` therefore lands on a meaningless point and `k` comes out wrong by 3.849 mm, which is
exactly the body's front overhang (front face 67.81 vs front datum 71.66).

## What is shipped, and what is still wrong

Shipped, because it removes a catastrophic failure and a dead end:

* the body lands **on the surrogate's leg** (z 53.803, the split-axis height) instead of at the
  origin ~100 mm away;
* the seating is relative, so it works from any starting offset;
* the `already_glued` short-circuit is expressed against the computed target rather than "is the
  offset zero", so a second invocation still acts — **the stranding is gone**, verified by dragging
  and re-gluing twice, and a third call correctly reports "already glued".

Still wrong, and it must not be mistaken for noise: the seat lands **+3.849 mm along the leg** from
the CAD-exact pose (target x 101.255 against the correct 97.406). A "glue" that is 3.85 mm out is a
real error in a precision workflow — better than 100 mm at the origin, not good enough to call done.

## What the exact fix needs

`k` is the body's axial asymmetry about its surrogate's datum span — measured on the correctly
glued scene, front overhang 3.85 mm and rear overhang 0.34 mm, so `k = (0.34 − 3.85) / 2 = −1.755`.
Those overhangs are a property of the CAD relative to its **optical** datums, and nothing in the row
data marks where the barrel's front face sits relative to the first optical surface. It is known at
IMPORT time, when the auto-alignment establishes it on an unfolded axis, and then discarded.

So the exact fix is to seat against the datum the alignment actually pins.

**Lead worth following first, before adding any persisted state.** The codebase already states the
invariant. `improve_lens_surrogate_rear_datum` (`scene_placement_commands.py`) computes

```python
# the STEP rear face = the axial extreme farther from the (front-pinned) front datum
step_rear_z = zmax if abs(zmax - front_datum_z) >= abs(zmin - front_datum_z) else zmin
```

— "the **front-pinned** front datum", read from `self._lens_front_datum_z()`. If the body's front
face is pinned to that datum, the target needs no `k` at all: it is
`P_front_datum + d̂ · (centre-to-front-face distance along the leg)`, all of which is measurable at
runtime from the transformed mesh.

The catch, measured: that is NOT the `Front Optical Vertex Datum` row. Pinning the front face to
row 1 (x 71.66) gives centre 101.256 — exactly the wrong answer this partial fix produces. The
correctly glued body's front face sits at 67.81, i.e. **3.85 mm ahead of** the optical vertex,
because this scene came from the machine-vision folder importer, which "placed g1 behind the front
datum / g2 ahead of the rear datum" (`machine_vision_folder_import.py`).

**Resolved — the lead is a dead end, and it rules out the whole runtime-derivation family.**

`_lens_datum_row_index(side)` matches `side` + (`datum` | `vertex` | `edge`), so on this scene it
resolves to row 1 `Front Optical Vertex Datum` and row 6 `Rear Optical Vertex Datum` — exactly the
rows already in use. No fallback is in play. So `_lens_front_datum_z()` = station 130.635, and
pinning the front face to it reproduces the wrong answer (101.256) that was already measured.

Putting the numbers together settles it:

```
datum stations            130.635 / 185.635   -> station midpoint 158.135
c_zero (auto-aligned)     z 160.230           = station midpoint + 2.095
world datums              x 71.66 / 126.66    -> world midpoint 99.160   (span 55.0 both, so a
                                                 pure translation relates the two frames)
correct glued centre      x 97.406            = world midpoint - 1.754
```

Both frames have the same 55.0 mm span, so the auto-aligned pose maps to world midpoint + 2.095 =
**101.255**, while the correct pose is **97.406**. They differ by 3.849 mm *after* accounting for
the fold. So the correct pose is **not what the auto-alignment produces at all** — no amount of
frame-mapping recovers it.

That is because this scene's lens was placed by the **machine-vision folder importer**, which
"placed g1 behind the front datum / g2 ahead of the rear datum", not by the zero-offset
auto-alignment. The 3.849 mm is genuine information that exists *only* in the stored placement
offset — which is precisely what the menu destroys.

## What this means for the fix

"Glue to surrogate" cannot reconstruct the correct pose from the surrogate geometry, because for an
importer-placed lens the correct pose was never derived from it. The menu's promise — "return to the
auto-aligned station" — is simply wrong for such a lens; the auto-aligned station is 3.849 mm off.

So the fix is to record the REFERENCE placement when it is established (by the importer, or by the
auto-alignment, whichever placed the body) and have the menu restore *that*, rather than recompute
anything. Concretely: persist a per-overlay `glue_reference_offset_xyz` alongside the existing
`*_step_placement_offset_xyz` in the layout settings, written at import/auto-align time, and have
`_reset_lens_to_surrogate` seat to it. That is the "persist at import" plan, now with the runtime
alternatives eliminated by measurement rather than by assumption.

## Shipped — exact

`step_glue_reference_offset_xyz`, a per-overlay record of the placement a body was PLACED at, kept
beside the live placement offset and persisted in the layout settings. `glue_step_overlay_to_surrogate`
restores it for the lens instead of deriving anything; the surrogate-derived seat remains as the
fallback for a body that has no reference, where landing on the leg still beats the origin.

A saved layout's stored placement **seeds** the reference on load, so layouts written before the key
existed work immediately — which includes the scene that reported this.

Measured: drag the body 30.8 mm away, glue, and it returns to x 97.406 with residual **0.000000 mm**.
A second drag-then-glue lands identically (the stranding is gone), a third reports no move, and the
reference round-trips through save/reload.

Guard: `validate_open3d_0497_glue_restores_the_recorded_placement.py`, penta phase 402. Section C
covers the round trip on purpose — bugs/0492 is this exact settings block, and the facade shadowing
it fixed is what silently ate a key here before.

Still open: the LED takes the same destructive zeroing path and wants the same treatment.

The LED takes the identical destructive path and still wants the same pass.

The `already_glued` short-circuit must go too, or be re-expressed against the computed target
(`is the body already AT the target`) rather than against "is the offset zero" — otherwise the
stranding survives the fix.

The LED takes the identical destructive path and wants the same treatment on the same pass.

## Guard it still needs

Not written yet — the behaviour is not final while the 3.849 mm residual stands. When `k` is
persisted at import, the guard should assert: the folded scene lands on the surrogate **at the
CAD-exact pose**, a second invocation can still move it, and the unfolded case is unchanged.
