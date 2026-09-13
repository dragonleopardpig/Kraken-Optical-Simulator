# 0784 -- the lens gap's floor is the METAL, not the row

Flags `20260913_083551_916` and `20260913_085839_545`:

> "Device size 22x22x1mm, FOV auto-solved to 23.1x8.3mm. I noticed the A5 gap is 32.96mm, so if the
> device size shrink to 0.5mm and the motor move everything that carries lens+filter+40mm RA
> mirror+camera closer to the big inverted RA mirror, meaning shortening the gap 32.96mm to around
> 11mm, it should match 0.5mm with FOV 23 just fine."

> "For device size 20mm, A5 gap is 28.1mm. So plenty of A5 room for 0.5mm device."

The user was right, and they were measuring the thing the app does not book.

## Two different A5s

The screenshot's banner reads `delivering 23.1 x 23.1 mm (|m| 0.9974); the lens moved -124.9 mm`,
so the ROW gap is 130.889 - 124.9 = **6.01 mm**. The measure tool in the same screenshot reads
**32.96 mm**. Both are right: they are different quantities, and they differ by the 26.90 mm offset
bugs/0782's verification workflow established (row 8's station origin sits 30.187 mm past the
prism's exit face, less row 9's `desp_z` of 0.389). The second flag is the same story at another
point: 28.1 mm of metal at device 20 is a 1.2 mm row, i.e. FOV ~22.

The lens block's position is booked as `rows[front-1].thickness`, which may not go negative (a
negative gap runs the station chain backwards and slides every downstream row off the leg;
bugs/0563/0564 heal them at load). That floor is **26.90 mm short of metal contact**, because the
50 mm prism's folded glass path is booked entirely on the OUTGOING leg while only ~25.29 mm of it
runs along that leg in world.

## Reproduced

`remeasure_routes_scene.py` on `attachment/om05a_folded_80mm.py`, one app per process:

| case | result |
|---|---|
| 22 mm, auto | solves, 2.22/2.22 um, capture 1.0, room 30.9/64.4 -- the flag's own banner |
| 0.5 mm, auto | refused, and rightly: auto targets 0.525 mm, needs the lens -214.5 mm, has 155.8 |
| **0.5 mm, FOV 23** | **refused: "the leg gap (row 8, 130.9 mm) cannot absorb it ... short by 5.099 mm; 155.8 mm of PHYSICAL room remains, so this is the row partition and not the hardware"** |

bugs/0771 wrote that message and deferred the cure: *"The real fix is to give the frozen family a
way to re-partition the object leg ... That is scene-structure work and is NOT done."*

## Fix -- buy the gap the room the metal already has

`ScenePlacementMixin._recover_lens_leg_headroom(front, needed, signed_delta)`, called from
`translate_lens_block_along_leg` at the point it used to refuse (after the PHYSICAL gate has
passed), shifts the shortfall out of the nearest upstream AIR gap into the lens gap and compensates
every body in between so that nothing moves:

* the donor must be AIR, carry no `Solid_3d_stl`, not be station-neutral (bugs/0581) and hold the
  shortfall -- glass is never shortened;
* each body between donor and gap is put back on its OWN measured `desp` frame -- probe the row's
  response to a unit desp on each axis and solve, never assume `desp_x` (the bugs/0782 rule);
* the move is audited afterwards: every body and the lens datum must be where they were, or every
  row is restored bit-for-bit and the old refusal stands;
* object side only -- the camera-side cap is the Filter, which is real hardware.

Measured on the scene by hand first (shifting 26.902 mm from row 6 into row 8 with the prism's desp
following): **0 bodies moved and `object_delta`/`image_delta` were bit-identical** (-135.9878 /
+47.4148). The code then reproduces that at run time.

## Result -- the shipped scene, through the real solve

| case | before | after |
|---|---|---|
| 0.5 mm @ FOV 23 | refused (row short 5.099 mm) | **solves, 2.28/2.28 um, capture 1.0, 19.8 mm of metal clearance, stage 42.3** |
| 20 mm @ FOV 21 | refused (row short 2.501 mm) | **solves, 2.48/2.48 um, capture 1.0, 22.4 mm clearance, stage 52.8** |
| 22 mm @ auto | 2.22/2.22 um, room 30.9/64.4, stage 53.066 | **identical to every digit** |
| 0.5 mm @ FOV 17 | refused (physical) | refused (physical): needs -157.4 mm, has 155.8, short 1.651 mm |

The limit is now the metal. For a 0.5 mm device the reachable floor moves from **FOV 24.43** (the
row) to **~17.5** (the bodies).

## Consequences to carry

* `docs/source/knowledge_base/om05a_bench_geometry.rst` states the row-model floor -- its
  `FOV_min(L) = 21.70 - 0.14 (L - 20)` line, the FOV 26/34/54 "no-crash" set and the travel chart's
  single 130.89 mm rail line are row limits, not hardware limits, and need restating against
  155.79 mm.
* The recovery writes the re-partition into the live rows, so it persists if the layout is saved.
  That is inert by construction (same world geometry, same conjugate, audited) but it means a saved
  scene may carry a smaller upstream gap and a larger lens gap than the file shipped with.
* Whether the bench drawing's "A5" is this metal dimension or the station is still the user's to
  confirm; if it is the metal, the model and the drawing now agree at the zero.

## Guard

`KrakenOS/UI/validate_open3d_0784_lens_leg_headroom_is_the_metal.py`, penta phase **567**, 16 checks
on a stub bench whose desp frame is PERMUTED (so a compensation that assumed `desp_x` fails B2): the
recovery shifts donor -> gap and leaves every body and the lens datum exactly where they were (A, B);
glass, short, station-neutral and body rows are not donors (C); the camera side and non-positive
requests are declined (D); an un-provable audit reverts bit-for-bit (E); and the mover tries the
recovery before its row refusal, re-reads the cap, and still runs the PHYSICAL gate first (F).
Related guards pass: 0719, 0726, 0727, 0731, 0740, 0759, 0770, 0771, 0772, 0782, 0783.
