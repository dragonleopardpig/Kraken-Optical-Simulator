# 0551 — "still have unbounded rays"

**Flags:** `flag_20260805_081647_775` ("lens swapped, still have unbounded rays") and
`flag_20260805_081811_672` ("changed FOV 23x23, still have unbounded rays"), both build
`76399de9`.

Both flags confirmed bugs/0550 was fixed — `negative_gap_rows: []`, and the census recovered
(375 → 305 strays, 93 → 160 reaching). The long lines streaming off frame were a **second,
independent** defect, and a display one.

## Trace and display disagree

| flag | TRACED max x | DRAWN max x | overshoot |
|---|---:|---:|---:|
| pre-swap (healthy) | 239.7 | 264.9 | +25 |
| swapped | 296.2 | **495.4** | **+199** |
| FOV 23×23 | 237.1 | **392.0** | **+155** |

The physics stopped at ~237 mm; the renderer drew to ~375–495 mm. So what the user was
judging as stray light was display scaffolding.

## Mechanism

Named with a renderer-level `AddActor` tripwire (the same play that named bugs/0550's writer):
the offender is `_flush_merged_ray_actors` → `_add_ray_actor` ←
`open3d_scene_refresh.py:949` → `_bounded_3d_ray_points_for_display` →
`scene_projector.bounded_ray_points_for_scene_display`.

An **escaped** ray is drawn with a tail along its exit direction, and that tail is
*extended past the traced stub* when the stub is shorter:

```python
max_terminal_length = max(75.0, min(scene_radius * 1.25, 600.0))
```

`scene_radius` is the geometry envelope (`scene_display_center_radius` reads surface meshes,
curves and targets — **not** ray paths, so there is no feedback loop; an earlier hypothesis to
that effect was wrong). On this scene the envelope makes `1.25 ×` ≈ 375 mm.

What the swap changed is the *number and direction* of escapes — `no_next_intersection`
279 → 337 and `missed_image` 0 → 59 — so many more of those tails now point +x, straight past
the prism.

## Fix

`1.25` → `_ESCAPED_TAIL_SCENE_RADIUS_FACTOR = 0.40`, a named module constant.

Chosen by rendering the alternatives from the flag's own camera
(`bugs/render_0551_escape_tail_options.py`):

| factor | drawn max x | picture |
|---|---:|---|
| 1.25 (shipped) | 375.1 | strays run off the frame |
| **0.40** | **233.6** | beam / fold / camera bundle pixel-identical, strays bounded |
| 75 mm stub | 233.6 | indistinguishable from 0.40 |

Below ~0.40 the drawn extent falls back to the scene geometry, so **0.40 is the largest factor
that fixes it** — the direction cue survives, the starburst does not.

## Generality

The fix is one **scene-relative** number — no absolute millimetre bound — so a 10 mm
micro-objective and a 2 m telescope each get a tail proportionate to themselves, and the 75 mm
floor is untouched (0.40 only starts to bind above a ~188 mm radius, i.e. exactly the large
scenes where 1.25 ran off the frame; every smaller scene renders bit-identically).

`bugs/diag_0551_escape_tail_sweep.py` traces the real attachment scenes (AZ85+BS, Apo75,
AZ85 RA-mirror, Pyrite85, 150mm test, 120mm 65M, the dual-MV splitter and the 50/50 splitter
example) under both factors and asserts:

* no scene's drawn-minus-traced overshoot **grows**, and
* no scene is drawn **shorter than its own trace** (the tail may only bound the synthetic
  extension, never clip real traced geometry).

## Guard

`KrakenOS/UI/validate_open3d_0551_escape_tail_bounded.py` (penta phase 436) calls the pure
projector directly: the tail is `0.40 × radius` on a large scene, scales **linearly** with the
scene (proving there is no absolute constant), keeps the 75 mm floor at 10 / 50 / 150 mm radii,
never draws shorter than a traced segment, and leaves bugs/0506's suppressed-branch stub alone.
Non-vacuity: the guard FAILS at 1.25 and at 0.60, passes at 0.40.

## Note

The escaped rays themselves are real — the trace does produce them. This changes only how far
their diagnostic tails are drawn, never the physics or the census.
