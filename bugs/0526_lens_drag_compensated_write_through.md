# 0526 — the compensated lens-drag write-through (drag = Solve for FOV, seats invariant)

## The arc

0524 first cut: raw two-gap writes → flag_20260803_162321 "haywire" (ghost BS diagonal,
prism off the beam) → reverted. This is the proper implementation.

## The key fact

EVERY row's pose — breadcrumbed world rows included — is `station + desp_z`: the 0433
freeze bakes `desp_z = world_z − station_at_freeze`. So a thickness write alone re-seats
every downstream row; the naive write corrupted exactly that way.

## The composite (atomic, inside the leg-slide branch)

For an along-leg lens slide `d`:
- gap BEFORE the lens block `+= d`, gap AFTER it `−= d` — the first order sees the
  conjugate change (s_o +d, s_i −d; the added/removed path is air, so reduced ==
  geometric; ppa rides the lens, ppp gains +d);
- `desp_z −= d` for every row strictly BETWEEN the two written rows — their stations grew
  by d, the compensation cancels it; rows past the downstream write get a net-zero station
  shift. Poses invariant BY CONSTRUCTION: the glued BS keeps its seat (it derives from row
  poses, so the glue needs no re-express), the mirror and sensor never learn anything
  happened, and the split's world legs change only through the members' own leg-direction
  desp motion (the intended lens move).
- Infeasible (either gap would go negative): the whole composite is skipped (body-only
  slide, debug note).

Verified on the frozen AZ85 scene: +8 mm drag → gaps ±8, |m| 1.152 → 1.039, FOV 28.28 →
31.35 (the readout follows), pose drift on BS/prism/sensor = 0.0 exactly, trace census
healthy; the 162321 haywire replay renders clean. With the 0520 commit refocus this
completes the user's loop: drag lens → FOV changes → image focuses at the sensor.

## Guard

`validate_open3d_0524_lens_drag_writes_sections.py` (penta phase 421): sections written,
FOV follows, seats hold to numerical zero, perpendicular drags stay body-only.
