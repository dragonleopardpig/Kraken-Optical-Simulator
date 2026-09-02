# 0696 — faceB's 19.2 mm defocus: phantom glass in the sequential medium bookkeeping

## The hunt (in order, each measured)
1. Suspected the mirrored-launch stash (bugs/0695 doc): gated non-launch stash
   writers (`stash_launch`), threaded the 0319 mixin wrapper -- no change.
2. Rebuilt the launch explicitly (grid builder, world-mode builders, keeper
   SOURCE_XYZ/LMN, captured-record) -- no change or arm vanished; reverted to an
   INLINE mirrored twin in `_trace_preview_bundles` (kept: architecturally the
   right place -- every non-append imaging call now carries its own mirrored
   twin, desync-proof) -- still no change.
3. Launch-order probes: the ONE real imaging call is the 3x3 grid aimed at the
   ~293 mm unfolded object distance (the PupilCalc-fallback aim,
   `_pupil_launch_fallback_count`=1) -- for BOTH arms. The earlier "aimed 2.9
   deg chain vs unaimed 1.16 deg B" readings were POOLING ARTIFACTS (mixed
   field cones share launch columns). Both arms launch mirror-identical cones;
   geometric paths equal to 4 um. So the asymmetry had to be in the TRACE.
4. Per-event media dump (RayEvent3D media_in/out): ray B's event at virtual
   surface 6 ("to lens (unfolded RA mirror 1)", glass AIR, drawing 0) applied
   `medium_change AIR->BK7` at (0, 28.3, -33.3); BK7 held until the Front
   Optical Vertex Datum -- the climb + ~189 mm of the lens leg in PHANTOM BK7.
   Ray A's same crossing: `transmit AIR->AIR`. The sequential medium
   bookkeeping consumed the FIRST-SURFACE mirror rows' glass fields for
   additive-SOURCE rays; chain rays suppress virtual glass on folded scenes.

## Root cause + fix
The 0695 stamp set `glass=BK7` on every swapped row -- including the
first-surface mirrors whose beams never travel inside glass (window RA
mirrors, centre halves) -- and mirror1/mirror2 rows carried BK7 from their
era. Fix (bugs/0696_air_mirror_rows.py): all six first-surface mirror rows
carry glass AIR. The BS cubes and far halves keep BK7 (real through-glass).
A one-iteration refocus + a BALANCED-focus stamp (bugs/0696_balance_focus.py:
sensor midway between the arms' waists) complete it.

## Measured result (bugs/0694_focus_census.py)
| arm | cones | waist RMS | vs plane | RMS @plane |
|-----|-------|-----------|----------|------------|
| A | 3/3 | 0.5-1.6 um | -0.40 mm | 20-23 um |
| B | 3/3 | 0.6-1.2 um | +0.40 mm | 17-18 um |
All six field cones sub-2 um, symmetric +-0.40 mm about the shared sensor,
~4 px at-plane both faces -- the vendor split-field design as intended.
(Old state: B 522-582 um at plane, waists 19.2 mm behind.)

## Also banked
- `_inline_mirrored_additive_bundles` (source_modeling) + the inline twin in
  `_trace_preview_bundles`: the faceB launch now reflects the exact bundles of
  its own trace call in every topology (sync/capture/replay).
- `mirror_profile()` in the 0695 builder: mirrored profiles get REVERSED
  winding (the 0684 inside-out lesson, pre-emptively correct even though STEP
  writers normalize orientation).
- Chain reach changed with the glass truth (edge cones thinner): the guard is
  re-pinned to the measured new state; the pre-AIR counts were partly
  phantom-glass artifacts.

## Follow-ups
- Engine question (not blocking): why virtual-row glass applies to additive
  SOURCE rays but not chain rays on folded scenes -- unify someday.
- The 0.8 mm A/B focal split is real modeled physics (balanced by the stamp);
  vendor drawing may specify the intended compromise.
