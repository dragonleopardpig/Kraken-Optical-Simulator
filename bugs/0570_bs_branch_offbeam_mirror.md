# 0570 — the splitter's reflect branch was invisible to the beam walk

**Two flags plus a follow-up, all on `attachment/machine_vision_Pyrite85_BS.py` (build c3062096):**

* `flag_20260806_102150_488` — "solve FOV partialy works, rays still defocus at sensor."
* `flag_20260806_102258_275` — "right click defocus not working."
* "the BS plate is shifted down. It happened after FOV solve."

The first two are the same defect seen from two buttons; the third is a separate one on the
object side. Both are the *positional/straight-axis assumption* family that 0546/0569 belong to.

## Defect 1 — the in-path fold mirror read as "parked clear"

`offbeam_free_placed_mirror_row_indices` walks ONE leg from the straight global **+Z** and bends
it only at **Mirror** faces. On a coaxial LED+BS scene the imaging axis IS the splitter's
**reflect** branch (`axis:global:split`, +X at z = 82.7), so the RA mirror at x = 193 sat 193 mm
off the walked leg and was recorded off-beam:

```
offbeam rows: {7}                 <- the mirror the rays visibly fold off
equivalent thicknesses [147.432, 1.823, 18.302, 18.302, 1.093, 93.865, 0.0, 0.0, 0.0]
                                                                          ^^^ row 7 zeroed
```

bugs/0224 treats an off-beam mirror as optically inert and zeroes its row in the straight
equivalent — and **that row is the mirror→sensor gap**. With the image leg gone,

```
_real_ray_best_focus_shift_for_rows() = 54.593  with the sensor 40 mm nearer
                                      = 54.593  unmoved
                                      = 54.593  40 mm further      (bit-identical)
```

A number that does not move with the sensor **cannot be a residual**, and everything downstream
consumes it as one:

* `snap_detector_to_image_plane`'s frozen adaptive loop (bugs/0515) re-measures to decide when to
  stop. With a constant residual it just walked the sensor around — the debug trace added here
  shows five iterations of ±54.593 that ended wherever the count ran out, once landing the sensor
  **on the far side of the fold mirror**. Its first attempt aimed at a far leg of
  44.076 − 54.593 = **−10.5 mm**, i.e. straight through the mirror, so the camera-body resolver
  refused ("the fold mirror needs to slide 39.5 mm further than the lens-to-mirror leg can
  give") — the "right click defocus not working" the user saw.
* the FOV solve's traced-focus finisher (bugs/0490, wired into the folded branch by 0569) calls
  that same snap — "solve FOV partialy works, rays still defocus at sensor".

**Fix:** the walk now carries a small SET of legs and bends at splitter faces too
(`splitter_fold_face_normal`): a splitter's reflect branch becomes a leg of its own, and a mirror
is off-beam only when it misses **every** leg. bugs/0224's parked prism still reads off-beam
(it misses all of them), which its guard checks.

After the fix, on the user's scene: off-beam = ∅, the equivalent keeps the 58.924 mm image leg,
and the measure follows the sensor 1 mm per mm (−4.331 at the current gap, −44.331 40 mm along
it). The real defocus was **4.33 mm**, not 54.59 — the big number was the truncated chain. The
snap now lands it in ONE iteration, residual 4.8e-14 mm.

## Defect 2 — the object write dragged the glued beam splitter

`_object_locked_redirect_row` holds the LED+BS fixed and moves the lens instead — but it finds
the unit **positionally** (the row right after the object gap), and bugs/0546 established that a
promoted solid's row index is not its geometry: here the BS is glued to the LED, physically
upstream of everything, with its row at index **6**, after the whole lens block. The redirect
never fired, the delta went into row 0, and every WORLD-placed row slid with it while the LED
body (an overlay at an absolute offset) stayed:

```
object gap 118.970 -> 147.432   (+28.462)
BS plate   z 54.459 -> 82.921   (+28.462)      LED housing centre z 74.405 -> 74.405
```

— "the BS plate is shifted down", measured to the millimetre.

**Fix:** `_glued_illumination_unit_rows` finds the unit by **marker** (a promoted solid that is
station-neutral (bugs/0435) or flagged a beam splitter, in a scene with an LED body/glue), at any
row index. When the row order makes a redirect impossible — no single gap write can move the lens
while holding a splitter that sits *after* it — `_hold_glued_illumination_unit` takes the slide
back out of the unit's own `desp_z` (a promoted solid is absolutely placed: pose = station +
desp_z, bugs/0546/0526), so its world pose is unchanged by construction.

After the fix, a 30×30 solve moves the **lens** 25.864 mm and leaves the splitter at
`(−0.122, 0, 82.921)` — 0.0000 mm — with its offset from the LED housing centre unchanged at
+8.516 mm.

## Guard — phase 445 `validate_open3d_0570_bs_branch_reaches_the_mirror`

* **A pure**: the splitter-normal reader; the walk follows the reflect branch, with a
  **fail-before** (strip the splitter marker and that same mirror reads as parked) and bugs/0224
  intact (a mirror parked 400 mm off every branch is still off-beam); the unit is found by marker
  at row 3 of a 6-row scene; the hold cancels a +25.864 mm slide exactly.
* **B real scene** (skip-if-absent): on the saved layout the mirror is not off-beam; the measure
  follows the sensor (the property that makes it a residual); the snap moves the sensor and lands
  it at best focus; and a 30×30 solve holds the splitter while the lens moves.

Also added: a permanent `append_debug` line per snap iteration (base leg, residual, direction,
target, refusal). Without it this was invisible — the numbers only exist inside that loop.

## Note on the older reds

Phases 380 / 414 / 418 (0468 / 0515 / 0519) were failing at HEAD before this work — verified with
the work stashed out — and all three still fail, on the same assertions, after it. They drive the
user's LIVE `machine_vision_AZ85_RA_Mirror_BS.py`, which has drifted a long way from the baseline
cut on 2026-08-05. What changed with this fix is their numbers, and one of them is worth a look:

* **418 (0519)** now REFUSES 55×55 with the honest bugs/0466 message ("the image distance would
  go negative … about 80% of the size you entered") where it used to accept. That refusal is
  computed on the *corrected* chain (the image leg is no longer zeroed), so it may well be right
  — but it needs its own turn to confirm against the optics rather than be assumed.
* **414 (0515) B2** still reports "residual traced defocus (got None)": that is
  `_traced_bundle_best_focus_shift`, whose preview bundle on this scene contains **no
  `target_termination` rays at all** and dozens of duplicate `focus_source='default_distance'`
  detector targets at a bogus pose `(−107.441, −10.452, 13.737)`. A separate hole, measured here
  but not fixed.
