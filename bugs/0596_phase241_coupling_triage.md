# 0596 — phase 241 (source→object coupling) triage: the BASE image is no longer uniform (OPEN)

Phase 241 ("source → object irradiance couples the illumination rolloff onto the detector image")
is one of the 17 pass→FAIL flips recorded in the 2026-08-09 honest baseline re-cut. Measured
triage, so the next session starts from facts instead of hypotheses.

## The failure

```
COUPLED detector image fold(X) edge/centre=0.375 perp(Y)=0.441; BASE fold=0.375 perp=0.441
coupled detector perp edge not uniform: 0.441 (<0.80)
coupling did not deepen the fold dip: base 0.375 -> coupled 0.375 (<0.15)
```

Coupled equals base **to three decimals in both axes** while the guard's own elementwise check
confirms `weights == base_weights × irradiance` with irradiance spanning 0..1. The coupling
multiplies, and the image does not move.

## Measured facts (fixture: `_build_coupling_fixture(800)`, seeded)

1. **The record pairing is perfect**: corr(object_x, det_x) = **+1.000**, corr(object_y, det_y)
   = +1.000 over 230 paired records (a 1:1 coaxial double-pass — the origin extraction and the
   local frames are fine).
2. **The sampled multiplier is noise w.r.t. the fold axis**: corr(irr, |det_x|) = **−0.002**
   (fold), corr(irr, |y|) = −0.211 (perp). A working coupling demands strongly negative on the
   fold axis.
3. **The map is shot noise by construction**: 294 object hits over a 16×16 grid spanning the
   **±50 mm** auto-fitted extent (~6.3 mm bins, ~1.1 hits/bin). Sampling along X at y=0 gives
   `[0, 0, 0, 0, .33, .33, .33, .33, .67, .33, .33]` — half the FOV samples zero.
4. **The extent is BY DESIGN, not a regression**: the fixture LED footprint is ±27.5 (fold) ×
   ±39 (perp) — hits span ±33/±37 — plus the 20% pad gives the observed ±48..52. This has been
   the map's window since the fixture was calibrated. Two candidate "fixes" tested and
   discarded: bin-count scaling by full/robust span, and [p2, p98] pre-clipping — **both left
   every metric byte-identical** (the footprint has no thin stray tail to clip).
5. **The anomaly is the BASE image**: base fold = 0.375, base perp = 0.441. The guard's design
   reads as if the un-coupled base (weights = `branch_power × source_weight × source_power`)
   was ~uniform when calibrated, with the coupling then imprinting the dip (thresholds:
   coupled fold ≤ 0.45, coupled perp ≥ 0.80, deepening ≥ 0.15). Today the base ALREADY carries
   a dip in BOTH axes — so even a perfect multiplier cannot make the perp edge read ≥ 0.80.

## Next-session direction

Find when the BASE detector image on this fixture stopped being uniform: bisect
`_branch_detector_spot_samples`' weight inputs (`branch_power` semantics changed in the
0530–0533 stray-visibility / split-power rework; `source_weight` paths changed around
0540/0590/0592's ray-count caps). The guard may ALSO need its thresholds re-derived from the
physics rather than the calibration-day snapshot — but only after the base-weight change is
attributed. Do the archaeology in the MAIN tree (phase 317's lesson: worktree A/B is not
trustworthy for every phase).

Related: `project_validator_known_failures` (the 2026-08-09 re-cut), bugs/0530–0533 (split
power), bugs/0592 (full-count switch).
