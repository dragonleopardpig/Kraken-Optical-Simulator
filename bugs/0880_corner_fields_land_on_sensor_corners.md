# 0880 -- pin the requirement: corner fields land on the sensor corners

User's requirement, in their words: *"the 9 launched sampled rays, 4 launch from the corners, 4
launch from the edges, 1 from center, the user can visually see the corners rays land on the
corresponding sensor corners."*

**It is correct physics and KrakenOS already delivers it.** Measured on MV150 with the Open 3D
`world_envelope` sampling, keeping only the rays that reach the detector:

```
sensor half 11.52 mm, paraxial |m| 1.14671
fld        launch x,y  | hits   centre of HITS x,y   |c|/half
  0  (-10.046,-10.046) |   25   (-11.5200,-11.5200)    1.000   corner
  1  ( +0.000,-10.046) |   25   ( +0.0000,-11.5200)    0.707   edge
  2  (+10.046,-10.046) |   25   (+11.5200,-11.5200)    1.000   corner
  3  (-10.046, +0.000) |   25   (-11.5200, +0.0000)    0.707   edge
  4  ( +0.000, +0.000) |   25   ( +0.0000, -0.0000)    0.000   centre
  5  (+10.046, +0.000) |   25   (+11.5200, +0.0000)    0.707   edge
  6  (-10.046,+10.046) |   25   (-11.5200,+11.5200)    1.000   corner
  7  ( +0.000,+10.046) |   25   ( +0.0000,+11.5200)    0.707   edge
  8  (+10.046,+10.046) |   25   (+11.5200,+11.5200)    1.000   corner
```

Nine field points, all `hit_detector`, landing on exactly the sensor's 3x3 grid. Nothing was
broken; what was missing is that **no guard checked it**, so 0879's launch-side contract could
have gone on passing while the corners quietly stopped reaching the corners.

## The check

`_check_field_grid_lands_on_sensor` in
`KrakenOS/UI/validate_launch_origin_within_object_aperture.py` (penta phase 668). Everything else
in that file checks where the rays START; this checks where they LAND.

- only rays whose terminal status is `hit_detector` count;
- each field's landing centroid must match `|field| / half * sensor_half` within 2% of the sensor
  half-extent;
- the sign mapping must be **consistent** across the grid (one sign per axis) rather than
  hard-coded, because orientation is a convention -- an odd number of folds flips it.

## Two traps this cost, both worth keeping

1. **Averaging vignetted rays moves the spot.** Each field launches 31 pupil samples and 6 are
   `stopped` at the aperture, terminating elsewhere. Averaging all 31 put the corner centroid at
   9.11 mm instead of 11.52 -- 79% of format -- and I reported that as a possible defect before
   filtering by terminal status. **A spot centroid must be built only from rays that reached the
   plane you are measuring on.**
2. **`field_index` is not guaranteed to start at 0.** The first version indexed `pairs` by it and
   raised `IndexError` the moment a trace numbered its fields 9..17. The check now pairs the
   sorted field indices with the launch pairs **in order**.

## Proven able to fail

A guard that cannot fail is not a guard. Told the FOV was 20% smaller than it is, the check
reports exactly the 8 off-axis fields and passes the on-axis one:

```
WRONG-HALF failures: 8 (expect 8 off-axis fields)
   field 0 launched from (-10.05, -10.05) landed at (-11.52, -11.52); expected |x|=14.4, |y|=14.4 (+/-0.2304)
```

## Still open, unchanged

`rows[0].diameter` is 25 mm while the field diagonal is 28.41 mm, so the four corners launch from
1.71 mm outside the object row's circular aperture. The measurement above shows this does not
affect the trace -- the rays launch, propagate and land correctly. It remains a bookkeeping
inconsistency (and affects how the object plane is drawn); letting the object diameter follow the
FOV diagonal would settle it. That is a prescription decision, not a bug fix.
