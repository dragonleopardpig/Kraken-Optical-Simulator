# 0122 — an in-line LED decoration carves the object→lens dimension, so "275" reads as object→LED

## Symptom

Two flagged snapshots from one recording (`flag_20260623_202414_122` "before
change the distance" and `flag_20260623_202506_093` "after change LED distance,
all wrong"):

> "When imported LED, I entered 200 in the pop up box for LED distance, why
> become 275?" … "Thickness should not stick to one surface forever after
> rotation. it should remeasure. … the gap between the flipped LED to object is
> shown to be 275mm."

The user imported an LED illuminator, set its object-side edge distance to
**200 mm** (correctly placed: LED front face at z=200), and was looking at the
`S0` object-gap dimension. The S0 arrow visibly runs from the object plane to the
**LED's object-side face** (z=200) — ~200 mm long — yet it is **labeled
"S0 Thickness = 275 mm"**. So the object→LED gap appears to read 275 mm, and the
275 (the real object→lens working distance) looks like an LED measurement.

## Root cause

The LED is an **independent decoration** (a visual prop), placed in front of the
lens for in-line illumination. The `S0` prescription gap is object plane
(z=0) → lens front (z=275). The LED body (z[200, 276.4]) straddles the optical
axis and its centroid (≈238) sits inside the S0 span.

`Open3DThicknessDimensionService._overlay_axial_spans_within` iterated **every**
STEP overlay (`_step_actor_map`) — including decorations — and the bugs/0009
overlay-carve therefore carved S0 at the LED. The carve clamps the LED span to
`[200, 275]` and `split_span_at_overlays(0, 275, [(200, 275)])` returns a
**single** remaining gap `[(0, 200)]`. The label branch keys off
`split = len(gaps) > 1`:

```python
elif split:                       # 2+ gaps -> per-gap "gap = X mm"
    label = f"gap = {gap_mm:.4g} mm"
else:                             # 1 gap -> falls through to the FULL row thickness
    label = f"S{row_index} Thickness = {thickness:.6g} mm"
```

With one remaining gap, `split` is False, so the arrow geometry is shortened to
object→LED (0→200) but the label falls through to the full row thickness
(275 mm). Net: a **200 mm arrow wearing a 275 mm label** — the object→LED gap
"shown as 275".

The placement itself is correct and rotation-invariant: the LED aligns its
`front_face="min"` to `target_front_z` (the entered edge distance), and a 180°
flip pivots about the body centre, so the LED stays at z[200, 276.4] before and
after the user's un-reverse rotation. The 275 has no link to the LED — it is the
object→lens working distance — which is why typing an LED distance never changed
it and why the rotation didn't "remeasure" it.

## Fix

A decoration overlay must not carve an optical thickness dimension; only real
optical bodies (lens / beam splitter) may. `_overlay_axial_spans_within` now
skips overlays whose label is a decoration:

```python
for step_label, actor_keys in list(step_map.items()):
    if is_step_overlay_decoration(step_label):   # bugs/0122: led / camera are props
        continue
    ...
```

(`is_step_overlay_decoration` / `STEP_OVERLAY_DECORATION_LABEL_SET = {"led",
"camera"}` already exist — the same decoration notion used by the
not-promotable-as-optics guard, phase 87.)

After the fix S0 has no carve span, so it draws a single full-length object→lens
arrow whose 275 mm label matches its length; the LED prop simply sits in the
path. The beam-splitter / lens carve (bugs/0009, bugs/0093) is unchanged — those
are optical, not decorations.

## Not in scope (separate later stages, per the user)

- **LED↔lens coupling** (the in-line illuminator riding in front of the lens so
  setting the working distance moves both) — next stage; the LED stays an
  independent decoration for now.
- **BS↔LED glue** (the cube beam splitter glued to the LED for actual optical
  function) — the existing pending Item 3.
- **LED imports facing backwards** (needing a manual 180° flip) — model-specific
  nuisance; the flip works correctly and is left as-is.

## Test

`KrakenOS/UI/validate_open3d_decoration_does_not_carve_thickness.py::run_checks`
— display-free, drives the real `_overlay_axial_spans_within` /
`split_span_at_overlays` off a fake inspector with canned axial extents:

- a decoration **LED** alone does not carve S0 → one full uncarved span, and the
  single gap equals the full row span (label length == arrow length, pinning the
  bugs/0122 mislabel away);
- the **camera** decoration does not carve either;
- a real **optical beam-splitter** body still carves S0 into two gaps (bugs/0009
  preserved);
- **LED + BS** together → only the BS carves (no span reaches the LED region);
- source contract — `_overlay_axial_spans_within` consults
  `is_step_overlay_decoration`.

Penta **phase 114** runs the guard.

## Note — in-app eyeball owed

Headless Xvfb can't drive the embedded-VTK dimension render, so the on-screen
"S0 = clean full-length 275 mm arrow across the LED prop" is verified in-app. The
guard pins the carve-exclusion logic and the single-gap label trap.
