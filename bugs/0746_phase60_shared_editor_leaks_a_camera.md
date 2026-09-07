# 0746 -- phase 60 failed in-suite because the shared editor kept someone else's camera

The last failure this session actually owed. Phase 60 ("click-on-plane FOV solve") PASSED standalone
and FAILED in the suite, which is a state leak, not a regression -- the same shape as bugs/0743.

## Root cause

The penta suite passes ONE `app` editor to every phase. Phase 60 builds its own synthetic 4-row
system (object / L1 front / L1 back / image) and stubs the paraxial engine, but its "sensor" is an
IMAGE ROW of diameter 24 -- there is no camera, and every expectation is computed with the DIAGONAL
rule (`mag1 = sensor_semi / object_semi = 12 / 25`).

Phase 39 runs earlier and leaves a real camera registered on that shared editor. bugs/0735 then
sizes the rectangular FOV target from THAT camera instead of these rows, and on this fixture the
result lands within bugs/0727's idempotence tolerance of the stubbed |m| = 0.5. So the solve took
the "already delivering" path: **returned ok=True and moved nothing**.

The numbers make it obvious once they are visible:

    ok=True  obj 275.0000 (want 154.1667)  img 24.4050 (want 74.0000)  sensor 24.0000 (want 24.0000)

275.0 and 24.405 are the fixture's own defaults -- untouched.

## Fix

The fixture now declares that it has no camera:

    app._current_camera_sensor_active_mm = lambda: (0.0, 0.0)

bugs/0735 reads a zero sensor dimension as "no rectangle" and falls back to the diagonal rule,
which is what the expectations assume. (Raising instead escapes the phase -- tried, reverted.)

Verified: phase 60 passes ALONE, after 39, and across 35-60.

## The note that cost the most

The failure said only

    object plane 'Solve for Thickness' did not fill the sensor with the typed width

with no numbers, so the first instinct was to bisect the product. It now prints actual vs expected
for all four quantities, which is what turned this from a bisect into a two-run diagnosis.

**Lesson:** a guard sharing a mutable fixture must pin every input its expectations depend on --
not just the ones it happens to set. And a failure note without numbers costs more than it saves.

## Status of the gate after this

Of the ten phases the gate blocked on mid-session: 518 and 536 were bugs/0743 (encoding), 25 and 31
were bugs/0737 fallout, 60 is this. The remaining five -- 39, 282, 477, 492, 505 -- were confirmed
to predate the session by fixture-complete runs at `ee521fae` (0721).
