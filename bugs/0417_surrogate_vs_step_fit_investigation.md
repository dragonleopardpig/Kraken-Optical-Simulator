# 0417 — "Surrogate does not fit the Lens STEP" (Excellitas Apo 75 / 0703): why the importer can't fix it

**Flag `flag_20260723_074819_534`** (AZ85 scene, 0703 lens swapped in):
> "This Excellitas Apo 75 1X lens, seems like the surrogate does not fit the Lens STEP. you can see the
> last element is out."

## What's actually happening (datum-coordinate reconciliation)

The 0703 surrogate (`machine_vision_0703_005_000_40_exc.py`) is a blackbox **two-thin-group** model.
Reconciling its rows against the STEP glass (glass span 47.0, body span 52.9, the bugs/0374 pin centres
the glass on the datum-span centre):

| surrogate feature | datum-D | vs STEP glass | result |
|---|---|---|---|
| Blackbox Group 1 (front element) | 1.484 | glass front 1.502 | **−0.018 mm — fits** |
| Blackbox Group 2 (rear element) | 48.520 | glass rear 48.502 | **+0.018 mm — fits** |
| Rear **Optical Vertex Datum plane** | 50.004 | glass rear 48.502 | **+1.5 mm past glass, +0.5 mm past body** |

**The optical elements fit to 0.018 mm.** Only the rear *reference* datum plane overhangs, because the
importer sizes the surrogate datum span to the STEP **body** extent (50 mm, `_step_optical_axis_extent`)
while the pin aligns by the **glass** extent (47 mm) — the `margin = (span − d)/2 ≈ 1.5 mm` pads the datum
planes past the glass.

## Why "datum span = glass extent" was tried and REVERTED

The obvious fix — size the span to the glass extent so the datums land on the glass vertices (which
`solve_two_thin_groups`'s docstring even states as the intent) — **backfires for this lens.** I added a
shared `step_optical_glass_axial_metrics` helper + switched `_surrogate_span_from_assets` to the glass
extent, **regenerated** the 0703 surrogate, and got:

```
Front Optical Vertex Datum thickness = -2.141437   (was +1.483859)
Blackbox group thickness             = 25.641437    (was 23.517991)
```

**Negative** datum margins → the optical **GROUPS** now overhang by 2.14 mm — worse than the 1.5 mm datum
overhang it removed. `solve_two_thin_groups` confirms it: it *tries* to keep both groups inside the span
(`g1 >= 0 and g2 >= 0`) and falls back to a negative-margin symmetric solution when it can't. For the
0703's cardinals (EFL 74.9, PP ±30.7), the ideal two thin groups are **geometrically wider than the
47 mm physical glass** — and `HH = span − ppa + ppp` couples span into the solve, so shrinking span
doesn't free them.

**Conclusion: there is NO span that fits both the datums and the groups inside the glass.** The body
extent is the sensible tradeoff — optical groups inside (correct optics), only the reference datum planes
stick out ~1.5 mm. So the importer change was reverted; a code comment records why, to stop a re-try.

## What would actually help (not done — user's call)

The residual 1.5 mm is a **reference-plane** artifact of a surrogate that is inherently wider than its
glass, not an optics error. Options:
1. **Accept it** — the optics and the drawn optical groups are correct to 0.018 mm.
2. **Display-side** — clip / stop drawing the front/rear Optical Vertex Datum *planes* where they exceed
   the STEP glass, so the reference planes don't read as a protruding element (a render change, not the
   importer).
3. **Confirm stale app** — the surrogate was edited 07:35 and flagged 07:48 on a `dirty` build; a
   dramatic "last element out" is larger than 1.5 mm, so the running app may have had an earlier
   surrogate. Restart + reload + re-check first ([[reference_bug_repro_recorder]], stale-app pattern).

## Files

- `KrakenOS/UI/services/machine_vision_folder_import.py` — NB comment on `_surrogate_span_from_assets`
  documenting why glass-extent span is wrong (no behaviour change; span stays the body extent).
