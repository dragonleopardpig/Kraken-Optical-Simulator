# 0147 — Re-anchoring one dimension endpoint reverts the other end

## Symptom

> *"I tried reachor the right arrow, is working, but left arrow reanchor will
> cause the right arrow to position wrong, should be our next bug fix."*

A thickness/distance dimension arrow can be Ctrl-click re-anchored (bugs/0053):
the endpoint nearer the cursor follows the mouse onto a picked surface/edge and a
plain click commits a **measurement-only** override (the optical model is
untouched). Re-anchoring the **right** (downstream / larger-z) end worked. But
re-anchoring the **left** (upstream) end afterwards yanked the right end back to
its model position — the right arrow jumped to the wrong place.

## Root cause

The per-row override is a **single spec** that stores only the *moved* endpoint:

```python
spec = {"endpoint": endpoint, "ref_z": ref_z, "ref_label": ..., "fixed_z": fixed_z}
```

`ref_z` is the moved end's new axial z; `fixed_z` is the *other* end's axial z
captured at pick time (`_commit_dimension_anchor_pick` →
`apply_dimension_anchor_override`, `scene_placement_commands.py`).

The **drawing** path `reanchored_endpoints`
(`KrakenOS/UI/services/open3d_thickness_dimensions.py`) applied `ref_z` to the
moved end but took the **fixed end from the live model surface** `p0`/`p1`
(`_surface_reference_world_point(row)`), *ignoring the stored `fixed_z`*:

```python
if endpoint == "start": q0[2] = ref_z   # q1 left at live p1
else:                   q1[2] = ref_z   # q0 left at live p0
```

For a *fresh* single re-anchor this is invisible: the fixed end's `fixed_z`
equals the live model surface, so "re-anchor the right" looks correct. The bug is
a **sequence**:

1. Re-anchor the **right** → `spec = {endpoint:"end", ref_z:R, fixed_z:Lₘₒdₑₗ}`.
   Drawn: left at model `p0`, right at `R`. Correct.
2. Re-anchor the **left** → the spec is *replaced* with
   `{endpoint:"start", ref_z:L, fixed_z:R}` (its `fixed_z` correctly captured the
   right's re-anchored `R`, read from the live drag record). But the draw now hits
   the `endpoint=="start"` branch, so **the right end falls back to the live model
   surface `p1`** instead of `R` — the earlier right re-anchor is discarded and
   the right arrow snaps back to the model station.

So the position the user wanted was *already stored* in `fixed_z`; the drawing
just never consulted it. (The value-edit path `apply_reanchored_dimension_value`
*does* use `fixed_z` — the two were inconsistent.)

## Fix

`reanchored_endpoints` now pins the fixed endpoint's axial z to the stored
`fixed_z` when present and finite (keeping its x/y on the optical axis from
`p0`/`p1`, exactly as the moved end keeps its x/y and overrides only z):

```python
fixed_z = float(override["fixed_z"])  # when present & finite, else None
if endpoint == "start":
    q0[2] = ref_z
    if fixed_z is not None: q1[2] = fixed_z
else:
    q1[2] = ref_z
    if fixed_z is not None: q0[2] = fixed_z
```

A re-anchored dimension is therefore a true absolute-z measurement: **both** ends
stay where the user placed them. Re-anchoring the two ends in sequence now
composes — the second pick's `fixed_z` captures the first pick's moved position
(via the live drag record), so left-then-right and right-then-left both persist.

When `fixed_z` is absent (legacy spec written before it was stored, or the LED
object-edge sentinel row -7), the fixed end falls back to the live `p0`/`p1` —
unchanged behaviour, so no regression.

## Verification

- `reanchored_endpoints` with **no** `fixed_z` is byte-identical to the old
  behaviour (live fixed end), so the existing
  `validate_open3d_dimension_reanchor._test_reanchored_endpoints` still passes.
- With `fixed_z`, the fixed end is pinned: re-anchoring **start** keeps the end at
  `fixed_z` even when the live `p1` differs; re-anchoring **end** keeps the start
  at `fixed_z` even when the live `p0` differs.
- The right-then-left **sequence** (the reported failure) leaves the right end at
  the re-anchored R, not the model surface.

## Guard

- `KrakenOS/UI/validate_open3d_dimension_reanchor_fixed_end.py` (`run_checks`,
  display-free): pins (1) a stored `fixed_z` overrides a *drifted* live fixed end
  for both `endpoint` values; (2) the reported right→left sequence keeps the
  right end at its first re-anchor (simulating the live drag record feeding the
  second pick's `fixed_z`); (3) no-`fixed_z` falls back to the live end
  (back-compat); (4) `measured` equals `|ref_z − fixed_z|` when pinned; and a
  source marker that `fixed_z` is consulted (so a revert is caught).
- Penta phase **136** (`phase_136_dimension_reanchor_fixed_end`); baseline → 136 =
  pass.

## In-app eyeball still owed

Headless cannot drive the embedded-VTK Ctrl-click pick, so the *felt* behaviour —
re-anchor the right, then the left, and confirm the right arrow stays put — is
owed an in-app check.
