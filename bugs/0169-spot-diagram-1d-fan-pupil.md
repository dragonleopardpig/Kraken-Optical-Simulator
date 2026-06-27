# 0169 — Spot Diagram (2D) drew thin LINE spots: it sampled a 1D meridional fan, not a 2D pupil

## Symptom (user, comparing the 3D spot map to the 2D export)

`attachment/Spot_Diagram.png` (exported "Spot Diagram (Grid View)", Zemax double gauss):

> Is the plot correct? I also output Spot_Diagram.png, seems not matching. **I think the
> 2D is wrong.**

Each field's spot is a **thin vertical line** (~34 µm tall, ~0 µm wide), e.g. the on-axis
(0°) spot too. A spot must be a 2D blob (round on-axis from spherical aberration; an
ellipse off-axis from coma/astigmatism), never a line.

## Root cause — the editor's display pupil pattern collapses the spot to a Y-fan

The spot trace (`analysis_plot._plot_*`, the `spot`/`rms` branch) calls
`_build_geometric_image_samples_full(..., pattern="hexapolar", ...)`. But that sampler
**overrides** `"hexapolar"` with the editor's display pupil pattern:

```python
pupil.Ptype = self._current_analysis_pupil_pattern(pattern) if pattern == "hexapolar" else str(pattern)
```

`_current_analysis_pupil_pattern` returns `_current_kraken_pupil_pattern()`, i.e. the
editor's `pupil_pattern_var`, whose **default is `"Meridional fan"` -> Ptype `"fany"`** (a
1-D fan along Y, `source_trace_helpers.py`). So the "hexapolar" request becomes a
meridional Y-fan: every spot is sampled only in Y -> a vertical line (verified: on-axis
X-spread = **0.00 µm**, Y-spread = 33.74 µm).

The pupil pattern (Meridional fan / Cross fan / Hexapolar) is a *ray-fan DISPLAY* choice;
a spot diagram / PSF / spot-RMS must fill the pupil in **2D** regardless. (The same flaw
fed the new 3D "Spot map" overlay, so its RMS was a 1-D fan RMS.)

## Fix

`_build_geometric_image_samples_full` gains `require_2d_pupil=False`. When True and the
resolved Ptype is a 1-D pattern (`fanx`/`fany`/`fan`/`chief`/`rtheta`), it forces
`"hexapolar"` (a true 2-D pupil). The 2D Spot Diagram trace and the 3D Spot-map trace both
pass `require_2d_pupil=True`. A 2-D pupil keeps a user's explicit Hexapolar/Square choice
but never collapses a spot to a fan.

After the fix (double gauss): on-axis spot **X = Y = 33.74 µm (round)**; +14° spot **21 ×
31 µm (an ellipse — the off-axis aberration)**; RMS rises slightly (it now includes both
pupil axes, not just Y). The 3D Spot-map RMS is now the true 2-D RMS (6.5-9.9 µm). The 3D
map also right-sizes its hexapolar ring count (Samp 8 ≈ 217 rays/field) and skips a bad
field instead of dropping the whole map.

## Guard

`validate_open3d_spot_diagram_2d_pupil` (display-free): on the double gauss the editor's
default pupil pattern is a 1-D fan (so the fix is needed); with `require_2d_pupil=True` the
on-axis spot is round (X ≈ Y) and gains the X-spread the fan lacked; the 2D Spot-Diagram
trace and the 3D Spot-map trace both pass `require_2d_pupil=True`. Penta phase 163.
