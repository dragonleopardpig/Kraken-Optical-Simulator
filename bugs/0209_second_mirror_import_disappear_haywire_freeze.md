# 0209 — importing a 2nd RA mirror: overlay "disappears", rays go haywire, UI freezes

**Status: DIAGNOSED. The haywire rays are ALREADY FIXED by bugs/0208 (commit b18d571). The
remaining two — the ~5 s UI freeze and the unplaced mirror perturbing the beam / sitting off-axis —
are (a) a pre-existing trace-performance issue and (b) a placement-workflow gap; both need in-app
work (task #77) and are documented here, not blind-fixed.**

## Flag

`attachment/recorded_bug_repros/flag_20260702_210526_994` (+ `recording_20260702_210514.json`):

> *"The imported 2nd RA mirror, not placed yet, disappear, and the ray go [haywire]."*

Plus, from chat: on retry the UI froze (the recording shows a **39 s** gap between the mouse press
and release on the mirror).

## Root cause

Importing the 2nd RA-mirror STEP promoted it to a sequential row (row 2) at a **default, off-beam
pose** — `desp = (55.857, 126.376, 66.16)`, i.e. up at Y≈126, nowhere near the +X beam, with a
78.66 mm thickness. That is the "not placed yet" state, and it breaks the scene three ways:

1. **Rays go haywire.** Because the mirror is off the beam, `_solve_mirror_tilt` FAILS for it, so
   `fold_promoted_mirror_specs_to_sequential` yields only 1 record and the mesh mirror isn't folded.
   On the code the user's app was running, that dropped the scene to a **non-seq mesh trace** that
   sprayed the beam (`NsTraceLoop`, 2958 rays — the rainbow fan in the screenshot).
   - **FIXED by bugs/0208**: verified on the exact flag pose, the current code folds the beam
     cleanly at mirror 1 and ignores the unplaced floating mirror (on-axis endpoint stays at
     Y∈[−2,2], Z≈72 — a tight cone, no spray). The app just needs a **relaunch** to pick it up.

2. **The 2nd mirror "disappears".** It didn't vanish — it was promoted and parked at Y≈126, off to
   the side of the view (`step_actor_counts` has no `optical` because it's now a promoted *solid*
   row, drawn at its off-beam pose). There is no workflow yet to place it between lens and camera.

3. **The unplaced mirror perturbs the beam.** `_folded_optical_solid_straight_equivalent_rows`
   flattens every promoted mirror to a plate with its **desp zeroed** — so the floating mirror is
   flattened *onto the beam axis* as a 78.66 mm BK7 plate. Measured: the on-axis focus shifts from
   X 275.32 (single AZ85) to **X 353.98 (+78.66 mm — exactly the mirror's thickness)** and the RMS
   blows from 239 µm to 1386 µm. An unplaced mirror should not be in the optical path at all.

## The freeze

The AZ85 dense-cone preview trace is **~5 s per pass** — 3471 rays through KrakenOS's pure-Python
tracer (the dense `world_cone` from bugs/0203). This is inherent and not specific to the 2nd mirror:
even the single AZ85 is ~5 s per retrace, cold or warm (no effective caching). Importing / promoting
/ selecting the mirror retriggers that trace on the UI thread → the multi-second-to-39 s freeze.

## Why the rest is not blind-fixed

- **Freeze**: the real fix is architectural — run the preview trace off the UI thread, cache it by a
  geometry signature so non-geometry interactions don't retrace, or drop the ray count during
  interaction. Each risks the display or is a threading change that can't be verified headless (the
  full validator SIGSEGVs on llvmpipe). It also helps the single-mirror scene, so it deserves its own
  focused, in-app-profiled pass.
- **Unplaced-mirror handling / perturbation**: the clean fix is the import/placement workflow — an
  unplaced mirror should stay a floating DECORATION (like an unpromoted STEP overlay), not be
  inserted into the sequential optical path with a thickness that displaces the focus. Making it
  merely inert in the flat-plate equivalent doesn't help, because its axial *thickness* still
  displaces everything downstream; the row must not be in the optical path until placed. That is the
  in-app promote/placement workflow (task #77 / the bugs/0208 CAD-side follow-up).

## What to do

- **Relaunch the app** (the frozen instance won't recover) to get the bugs/0208 haywire fix.
- Adding a 2nd mirror is still an unfinished workflow: it lands off-beam, perturbs the focus, and
  can't fold until it is positioned on the +X leg between lens and camera. That placement (and the
  freeze) are the remaining pieces, both needing in-app iteration.
