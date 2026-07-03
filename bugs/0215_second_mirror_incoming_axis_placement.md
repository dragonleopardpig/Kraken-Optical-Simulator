# 0215 — the incoming optical axis is drawn far BELOW the two-mirror components

**Status: FIXED (incoming-guide placement). On the two-mirror AZ85 (ELS-85 surrogate) folded scene the
incoming +Z optical-axis guide was clamped ~134 mm BELOW the optical components (at the twice-folded
detector's Z=−62 instead of the first mirror's Z=+71.9). The guide now clamps at the FIRST fold, so it
runs up through the components. Fixes flag_20260703_150248_512 "the optical axis is away from the optical
components". The 2nd/3rd axis SEGMENTS (middle + outgoing) remain deferred — see "What's still open".**

## What the user flagged

After 0214 landed (and the user confirmed in-app via flag_20260703_145514 "reflected rays, image plane,
detectors are all same direction now"), the user flagged two optical-axis facets on the same two-mirror
scene:

1. **flag_20260703_150248_512** — *"even with one optical axis shown, it is away from the optical
   components."* The single drawn axis guide ran far below the mirrors/lenses.
2. An earlier observation: *"there should be 3 optical axis now, but there is only one shown"* — with two
   mirrors the chief-ray path has three straight runs (object→mirror-1, mirror-1→mirror-2,
   mirror-2→detector), so three axis segments are expected.

This bug fixes (1). Facet (2) is deferred (see below).

## Root cause — `min(fold_branch_zs)` picked the twice-folded detector

The incoming +Z guide's far end is clamped to `_folded_axis_incoming_fold_point_z()`
(`KrakenOS/UI/open3d_inspector.py`). That helper applies each folded row's rigid fold transform to the
row's straight +Z anchor and collects the resulting world Z per row (`fold_branch_zs`), then returns a
single representative Z.

A promoted full-mirror cube folds the downstream chain onto the reflected +X branch (bugs/0185). With
**one** mirror every folded row lands at the SAME constant Z — the AZ85 RA-mirror vertex, **Z=+71.9** — so
the choice of representative Z was irrelevant and `min` was fine.

A **second** promoted mirror re-folds the tail, so the rows no longer share one Z:

```
two-mirror fold_branch_zs (row → Z):
  rows 2..7 (fold-1 branch)   → +71.897
  row 8 (mirror-2 vertex)     → +70.598
  row 9 (twice-folded Image)  → -62.05   ← 0214's DOWN detector seat
```

`min(fold_branch_zs)` = **−62.05** — BELOW the object plane at Z=0 — so the incoming +Z guide was clamped
to `z1 = min(z1, -62+5) = -57`, drawing the whole axis ~134 mm below the components that sit at Z≈+72.
That is exactly the "axis away from the components" the user saw.

The incoming axis can physically only reach the **first** fold (the near mirror at +71.9); everything
downstream of that is on the reflected branch, not the incoming one. So the representative Z must key off
**optical/row order**, not the extremum.

## The fix — return the first fold, not the deepest

`KrakenOS/UI/open3d_inspector.py`, `_folded_axis_incoming_fold_point_z`:

```python
        if not fold_branch_zs:
            return None
        # First fold in optical order -- the one the incoming +Z axis meets before any
        # downstream re-fold (bugs/0215). Single-fold scenes have one constant Z, so this
        # equals the old ``min`` and their guides stay byte-identical.
        return fold_branch_zs[0]
```

`fold_branch_zs` is built by walking `range(len(rows))` in order, so `[0]` is the first folded row's Z
(+71.9). The incoming guide's far end now reaches +76.9 (first fold + the standard 5 mm margin), running
up through the components.

**Single-fold safety:** with one mirror all entries in `fold_branch_zs` are equal, so `fold_branch_zs[0]
== min(fold_branch_zs)` — the return value is unchanged and every single-mirror guide is byte-identical.

## Verification

Display-free guard `validate_open3d_second_mirror_incoming_axis_placement` (5/5):

1. two-mirror `_folded_axis_incoming_fold_point_z()` = **+71.9** (the first fold, above the object), and
   the fn returns `fold_branch_zs[0]`;
2. **CAUSAL:** `min(fold_branch_zs)` = **−62.05** (the twice-folded detector, below the object) — the old
   value would have dragged the guide ~134 mm below the components;
3. the drawn incoming `axis:global` record's far end reaches **+76.9** (up at mirror-1), not the bug's
   ~−57;
4. a single-mirror AZ85 scene is **byte-identical** — all fold Zs equal (+71.9) so `first == min`;
5. the fix is **wired** — the method returns `fold_branch_zs[0]`, not `min(...)`.

Causal check confirmed by stashing the fix: checks 1, 3, 5 FAIL against the old `min` code (fold point
−62.05, `axis:global` far end −57.1, source returns `min`), all 5 PASS with the fix. Checks 2 and 4 pass
either way by construction (the `min` value and the single-mirror equality are independent of the fix).

Registered as penta **phase 191** (`phase_191_second_mirror_incoming_axis_placement`), baseline `pass`.
The full validator marathon still SIGSEGVs on llvmpipe, so phases 0–190 are carried forward.

Scratch probe (untracked): `bugs/probe_0215_axis.py` (reproduces the mis-placed guide + the chief-ray
termination finding below).

## What's still open (deferred, honest scope)

The **2nd and 3rd axis segments** (middle mirror-1→mirror-2, outgoing mirror-2→detector — facet (2)
above) are NOT delivered here. The clean source for all three segments is the chief ray's own folded
polyline, but the headless dead-centre chief ray (ray 124, launch radius 0.00) **terminates at x=87.6 and
never reaches mirror-2** (x≈199.5) — only divergent marginal rays fold at mirror-2 (defocus). So there is
no central-ray data to derive a clutter-free middle/outgoing axis from. This is entangled with the
**two-mirror "unfocused" bug** (flag_20260703_145514, next in the queue): once the image focuses through
the two folds the chief ray should reach the detector and the traced-segment axes should populate
naturally. A deterministic alternative — anchoring the middle/outgoing guides on the known mirror-vertex
positions — is a larger new mechanism, deferred with the focus work.

**In-app eyeball owed:** the headless guard proves the incoming guide's far end moves from −57 up to +76.9
(through the components); confirm the rendered axis in-app on the user's two-mirror AZ85 scene.
