# 0044 — Real (z-buffered) 3D wavefront surface, alongside the 2D Zemax waterfall

**Status:** Implemented (2026-06-09). *Enhancement, not a bug* — kept in the
register because it follows the same discipline (documented, tested, phase-guarded,
baseline-regenerated).
**Component:** Wavefront analysis. New `KrakenOS/UI/services/wavefront_3d_view.py`;
`open_wavefront_3d_view` on `LayoutAnalysisDisplayMixin`
(`KrakenOS/UI/services/layout_analysis_display.py`); a **WFront 3D** toolbar button
in `KrakenOS/UI/panels/main_analysis_controls.py`.

## Origin

While polishing the 2D Wavefront Function waterfall (bug 0036) the user asked:
*"can we just generate this wavefront directly in 3D? … Much better than this fake
3D from 2D, right?"* Correct instinct: the analysis panel's oblique waterfall is a
painter's-algorithm 2D projection, which is why hard saddle/twisted wavefronts kept
needing hand-tuned hidden-line tricks (the see-through wireframe, the grey block,
the broken wall line — all 0036 follow-ups).

A note on engines: the in-app "Open 3D" viewport is *not* Open3D-the-library
(those `open3d_*` modules are a naming convention; Open3D isn't installed and the
view renders through `scene_projector` — itself a software 2D projector). The real
3D libraries actually present are **VTK 9.5.2 + PyVista 0.48.1** (already KrakenOS
core dependencies). So PyVista/VTK is the right engine: a true GPU z-buffer (real
hidden-surface removal — the saddle artifacts cannot occur), interactive
rotate/zoom, headless off-screen capture, and **no new dependency**.

## Design

The 2D Zemax-style waterfall **stays** as the printout/export panel (users diff it
against Zemax). This adds an honest interactive counterpart, decoupled from the
large live inspector:

`services/wavefront_3d_view.py`
- `wavefront_xyz_from_samples(samples)` — pulls `x_pupil, y_pupil, phase_waves`
  out of `editor._last_wavefront_samples` (the dicts the analysis panel already
  fills), dropping non-finite rows. No new capture path was needed.
- `build_wavefront_surface(x, y, opd)` — `pv.PolyData(...).delaunay_2d()` then
  `warp_by_scalar`. **Pure** (mesh in/out, no display), so it is unit-testable.
  The warp factor auto-scales the relief to ~⅓ of the pupil footprint width
  (`auto_warp_factor`), so it reads as a shallow Zemax dome regardless of pupil
  units (mm) or OPD magnitude (waves).
- `render_wavefront_surface_to_png(...)` — off-screen render (export + tests).
  Works headless here via VTK software GL; no Xvfb required.
- `show_wavefront_surface(...)` / `main(npz)` — interactive window; `main` makes
  the module a subprocess entry point.
- `write_wavefront_payload_npz(samples)` — serialises the samples to a temp `.npz`
  for that subprocess; returns `None` (< 3 finite samples) so the caller can tell
  the user to run the Wavefront analysis first.

`open_wavefront_3d_view` (editor) reads the stashed samples, writes the payload,
and `subprocess.Popen([sys.executable, "-m", …wavefront_3d_view, payload])` so the
Tk event loop never blocks and VTK never fights it over the GIL. The **WFront 3D**
toolbar button calls it; an info dialog prompts to run the Wavefront plot first if
there are no samples yet.

Colormap is `RdBu_r` and the scalar bar reads "Wavefront [waves]", matching the 2D
panel; the pupil rim is outlined with `extract_feature_edges`.

## Tests

`KrakenOS/UI/validate_wavefront_3d_surface.py` (display-free; SKIPs if PyVista/VTK
is unavailable). On a synthetic spherical+coma+astigmatism pupil it asserts:
(A) the sample dicts round-trip (bad/non-finite rows dropped); (B) the built mesh
has real points/cells, finite bounds, and a non-flat z-extent matching the OPD
range × warp factor (relief actually warped, shallow-dome aspect); (C) an
off-screen render produces a non-blank PNG (≥ 2 % non-white); (D) the subprocess
payload round-trips (`None` for empty, arrays preserved otherwise). Folded into the
comprehensive harness as **Phase 50**.

## Verification note

Rendered headless via the real renderer on a dome and a coma+astigmatism saddle
(`/tmp/wavefront3d_preview.png`) and inspected: a genuine 3D surface with correct
hidden-surface removal on the saddle (no fake-3D self-occlusion), RdBu_r OPD
colormap, axes triad and "Wavefront [waves]" colorbar — the honest 3D the user
asked for. The 2D waterfall panel is unchanged.
