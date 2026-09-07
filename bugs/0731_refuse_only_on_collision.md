# 0731 — only a real collision refuses the FOV solve

User, after bugs/0728/0729 put the focused image on screen: *"Refusal of solve is unnecessary for
the case of image location shift since we already have image detached from sensor shows up. Only
apply to real collision will do."*

## What changed

An image plane that lands off the sensor used to bail `_folded_conjugate_gaps_for_magnification`
to `None`, so the whole solve refused ("No real-image conjugate for that size") even though the
OBJECT side — the lens move that actually sets |m| — was perfectly reachable. That refusal existed
because the shift was otherwise invisible. It is not invisible any more: the scene draws the
focused image where it forms, with the distance on the banner.

* the solver now flags the result (`image_side_unreachable`) and returns the numbers instead of
  bailing;
* `_apply_conjugate_pair` turns that flag into an image-write LOCK — the image gap is never
  written (that would put the sensor inside the optics) — and reports a focus residual, pointing
  at the focused-image plane;
* every real refusal is untouched: no conjugate at all, no lens block, a parked CAD solid inside
  the block, and the object-side physical-room gate — the collision.

## Measured (om05a, in order, on one scene)

| request | before | after |
|---|---|---|
| FOV 20 × 20 | solves, lens −138.6 mm | unchanged, residual −98.0 mm |
| FOV 20 again | no-op (bugs/0727) | unchanged |
| **FOV 30 × 30** | **refused**, "No real-image conjugate" | **solves**: lens +35.76 mm, \|m\| 0.768, residual −93.9 mm |
| **FOV 55 × 55** | refused | **solves**: lens +89.41 mm, \|m\| 0.419, residual −33.2 mm |
| **FOV 5 × 5** | refused | **still refuses**: "needs the lens −178.8 mm … only 145.5 mm of physical room … short by 33.32 mm" |

This also removes the path-dependence noted in bugs/0727: fields that only solved from the
as-loaded geometry now solve from a moved lens too.

## Guard

`validate_open3d_0731_refuse_only_on_collision` = penta phase 530: A the image-side gate no longer
returns None; B the flag rides the dict both ways and the OBJECT-side bail still refuses; C the
caller locks the image write and reports a residual, before the write is assembled, naming the
focused-image plane; D the collision gate and its Force hint still refuse and banner the
shortfall.
