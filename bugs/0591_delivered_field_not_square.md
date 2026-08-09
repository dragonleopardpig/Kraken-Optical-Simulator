# 0591 — the delivered 55×55 field is not square, and the first order cannot judge it (RESOLVED: it IS square — the real defect is the delivered magnification)

Flag `flag_20260809_082246_212`: **"FOV 55x55, everything correct?"** — a question, not a defect
report. Scene `machine_vision_Apo75.py`, as-loaded lens 0703-005-000-40-EXC, build `5bcb72de`
(i.e. after bugs/0588 made this solve reachable at all).

## First: the tools that should answer it cannot

Three independent estimates of the delivered magnification disagreed:

| source | |m| | implied object field for a 23.04 mm sensor |
|---|---|---|
| the solve's own message | 0.4189 | 55.0 mm (the request) |
| a review lens, from world geometry | 0.38278 | 60.19 mm |
| `_shared_first_order_reference` after the solve | 0.59384 | 38.80 mm |

The third is mine and it is **not admissible**: `image_z = sum(row.thickness for row in
solve_rows[:-1])` (`paraxial_tools.py`, `_shared_first_order_reference`) is a STATION-frame
row-sum, and `image_principal = image_z - h2_z` inherits it. On a 0433-frozen folded scene that
frame is not the scene — the whole of bugs/0576. So the readout that looks most authoritative is
the least trustworthy here, and any answer derived from it (including the "system is 44 mm out of
focus" it implies) is an artefact of the frame, not a measurement.

**Only a world measurement can answer this question.** That is the 0576 methodology: judge an
estimator against an observation.

## The measurement

Solve 55×55 on the as-loaded scene, trace, and take the extents of rays that actually terminate
on the detector — their launch points at the object plane, and their landing points on the sensor
plane (world X and Y are the sensor's in-plane axes on this fold):

```
landed rays: 141 (of 558)
LAUNCH  extent at object : x -27.500 .. 27.500  (55.000 mm)   y -27.500 .. 27.500  (55.000 mm)
LANDING extent on sensor : x 238.899 .. 259.952 (21.053 mm)   y -14.785 .. 10.527  (25.312 mm)
```

Sensor: 23.04 mm square, active centre world (249.57, 0). Detector ROW diameter is 32.58 mm, so a
ray may terminate outside the 23.04 active area and still count as `target_termination` — which is
why the Y landings reach beyond ±11.52.

**The launcher is honest**: it launches exactly the requested 55.000 × 55.000 mm object field.

**The image is not square.** A square object maps to **21.053 mm (X) × 25.312 mm (Y)** — a 20%
axis asymmetry — and the Y footprint is **decentred by −2.13 mm** (centre −2.129, not 0), while X
is centred to 0.14 mm. Against the 23.04 mm active sensor that is 91.4% fill in X and 110% overfill
in Y.

X is the FOLD axis on this scene (BS reflects +Z→+X, the RA prism turns +X→−Z); Y is perpendicular.

## What is NOT yet established

**The X figure is confounded by vignetting.** Only 141 of 558 rays land, with 119
`aperture_stop_vignette`. The 21.053 mm X extent is the extent of the SURVIVORS, which is a lower
bound on the image, not the image. The Y overfill and the −2.13 mm Y decentre are the harder
findings, because vignetting cannot manufacture rays *outside* where the image is.

So the honest answer to "everything correct?" is **no, not exactly** — the delivered field is not
the square the message promises — but the size discrepancy and the decentre need separating before
anything is fixed.

## Next steps

1. Re-measure with vignetting disabled (or with the stop opened) so the X extent is the image
   rather than the survivors' silhouette.
2. Decide the Y decentre by termination reason: −2.13 mm on a nominally symmetric fold suggests a
   real decentre, not sampling.
3. If the asymmetry is real, suspect the two prisms' glass paths on the fold axis (the reduced
   path t(1−1/n) that bugs/0297 documents) being applied on one axis only.
4. Whatever the cause, the fix must NOT be judged by `_shared_first_order_reference` — see above.
   A frozen-aware first order is the standing debt (noted in bugs/0576's Open section).


## 2026-08-09 — measured with the world-order instrument (bugs/0593's fix)

The aimed-fan instrument (entrance-pupil-aimed launches, real-stop clipping, dominant-cluster
landings) re-measured the solved 55×55 state, free of the survivor-silhouette confound:

```
  fx      fy  |  u(land)  v(land)  nrays
  0.00   0.00 |  -0.165   -0.000     80
  0.00  27.50 |  -0.164   14.680     57
  0.00 -27.50 |  -0.164  -14.680     57
 27.50   0.00 |  14.466   -0.000     64
-27.50   0.00 | -14.862   -0.000     56
```

1. **The field IS square**: X edge-to-edge 29.329 mm vs Y 29.359 mm — 0.1% apart. The
   "21.053 mm X" of the original measurement was the survivors' silhouette, exactly as this
   doc's own caveat suspected.
2. **The Y decentre is NOT real**: ±14.680 exactly symmetric, centre −0.000. The −2.13 mm was
   preview-sampling asymmetry. The X asymmetry (14.466 vs −14.862) is also pure offset — both
   edges sit 14.664 from the shifted centre.
3. **Real, small**: the whole pattern lands ~0.17 mm off-centre on the FOLD axis (u ≈ −0.165
   at every field) — plausibly the BS plate's lateral walk-off. Cosmetic at sensor scale;
   unverified attribution.
4. **Real, large — the actual defect**: delivered |m| = 29.34/55 = **0.534** (0.542 at half
   field — ~1.6% distortion), against the solve's promised **0.4189**. At the delivered
   magnification the 55 mm object maps to 29.4 mm across a 23.04 mm sensor: **the sensor sees
   ~43×43 mm of the requested 55×55.** The solve message "Object 55 x 55 mm fills the sensor"
   promises a conjugate the machine does not deliver.

So the question this flag asked ("FOV 55x55, everything correct?") now has a precise answer:
the geometry is fine (square, centred); the CONJUGATE is not — the folded solve's first order
books gaps for |m| = 0.419 and the world delivers 0.534. That is the frozen-aware first-order
debt already standing in bugs/0576's Open section (and the §5b per-branch-pupil deep target),
now with a measured error bar: **27%**. Per `feedback_drag_is_thickness_constraint`'s durable
lesson (measured shifts are under-measured — iterate, never single-shot), the fix is a
measured-|m| feedback step in the solve or the frozen-aware first order itself — NOT a
compensation factor baked on top of the wrong frame.
