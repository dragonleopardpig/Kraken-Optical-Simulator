# 0593 — the field-aberration overlays draw nothing, and only numpy said so (OPEN)

Flag `flag_20260809_094851_598`: *"Normal to sensor works but none of the actual analysis overlay
works."* Then, separately, the user noticed these in the app's terminal:

```
numpy/_core/fromnumeric.py:3824: RuntimeWarning: Mean of empty slice
numpy/_core/_methods.py:142:    RuntimeWarning: invalid value encountered in scalar divide
```

They are the same defect. The warnings were the ONLY evidence the analysis suite was failing.

## Reproduced

On `machine_vision_Apo75.py` (0433-frozen, folded: BS +Z→+X, RA prism +X→−Z), exercising every
analysis overlay:

| overlay | result |
|---|---|
| `best_focus_surface_overlay_spec` | **None** |
| `distortion_grid_overlay_spec` | **None** |
| `astigmatism_surfaces_overlay_spec` | **None** |
| `illumination_marker_rays_overlay_spec` | None (no markers on this scene — expected) |
| `source_illumination_overlay_spec` | dict ✅ (fixed by bugs/0592) |
| `receiving_cone_overlay_spec` | dict ✅ |
| `source_illumination_rays_overlay_spec` | dict ✅ |

Warning provenance, 54 occurrences of each of 6 sites (54 field points × 3 means × 2 warnings):

```
KrakenOS/PupilTool.py:271/272/276   RMS_Pupil
  ← KrakenOS/PupilTool.py:572        __init__
  ← KrakenOS/UI/services/geometric_analysis.py:611  _build_geometric_image_samples_full
  ← KrakenOS/UI/services/analysis_plot.py:234       _sample
```

## Root cause

`RMS_Pupil` traces a small set of probe rays and then does `(X, Y, Z, L, M, N) = RP.pick(Surf)`.
On this scene **the pick comes back EMPTY** — the probe rays never reach the target surface — so
`np.mean(X)` warns and yields `NaN`, `R_RMS` is `NaN`, and every overlay built from those samples
silently becomes "no spec". The user sees an empty canvas with no message; numpy's warning is the
only trace.

Why the probe lands nothing here is the substantive part: `RMS_Pupil` drives a **sequential**
pupil probe (`SYSTEM.Trace` with explicit direction cosines) through a scene that is folded and
non-sequential. This is the documented non-seq behaviour — a ray outside the stop *skips* the
finite surfaces rather than vignetting (`bugs/diag_1x_cube.py`) — so a sequential probe has no
guarantee of arriving.

## Done here

`RMS_Pupil` now detects the empty pick and returns `NaN` **quietly and deliberately**, restoring
the system state (`SurfFlat`, `TargSurf`, `Vignetting`, `RP.clean()`) on the way out. Verified:
the 216 warnings drop to zero.

**This silences the noise. It does NOT fix the overlays** — all three still return `None`, because
the probe still lands nothing. Do not mistake the quiet for a fix.

## Open — what a real fix needs

1. The field-aberration suite must obtain its samples from a trace that actually reaches the
   sensor on a folded / non-sequential scene. The world-frame traced bundle already does
   (`_build_preview_system_rays_bundle` lands 141–160 rays on this very scene), so the suite is
   measuring with the wrong instrument, not measuring an impossible thing. This is the same
   station-frame-vs-world split as bugs/0576 / 0588 / 0591, one layer out.
2. Failure must be VISIBLE. A first attempt to log the reason from `analysis_plot._sample` was
   reverted because the check never fired (the tuple element tested was not the NaN-bearing one) —
   a guard that cannot fire is worse than none. The right home is probably where the emptiness is
   *known*, i.e. at the pick, with the reason surfaced to the status bar.
3. Guard it: no phase asserts that the field-aberration overlays produce a spec on a FOLDED
   scene. Phases 158–162 cover the suite, and this scene class slipped between them — the same
   gap shape as bugs/0589 (a guard that checked behaviour but never the thing the user looks at).
