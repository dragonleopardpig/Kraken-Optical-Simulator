# 0201 — BUG: the 2D view shows no ray tracing at all on the folded RA-mirror scene

**Status: RESOLVED. The 2D preview (`refresh_plot`) now routes the folded RA-mirror scene
through the same folded-aware trace the 3D view uses, so the 2D pane shows the converged
folded rays. Fix factors the folded trace + display-bend out of
`_build_preview_system_rays_bundle` into shared `Kraken3DInspector`/editor helpers
`_trace_preview_rays_folded_aware` + `_apply_folded_display_bend`, called from BOTH the 3D
builder and `refresh_plot`. Guard `validate_open3d_2d_folded_shows_rays.py`.**

## Flag

Reported in the 2026-07-01 review pass of the folded AZ85 RA-mirror scene (flagged as
critical):

> "2D does not show any ray tracing at all!"

## Root cause — the 2D path traced the mesh non-seq system directly

The 3D view builds its preview through `_build_preview_system_rays_bundle`, which on a
folded scene (bugs/0187) does NOT trace the mesh non-seq system — that retroreflects the
ideal Thin-Lens surrogates. Instead it traces the UNFOLDED straight equivalent
(bugs/0197) and BENDS the display rays at the mirror, so the folded cone converges on the
drawn +X detector.

`refresh_plot` (the 2D pane) never got that treatment. It traced the mesh system directly:

```python
system = self.build_system(require_solids=True)
rays = Kos.raykeeper(system)
self._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=True, ...)
```

On the folded AZ85 this retroreflects into a scattered mess — the on-axis endpoints strew
from X≈100 to X≈296 with a transverse RMS ≈ 45 mm (measured), instead of converging at the
X≈295.6 sensor. Those world-space rays then hit the 2D **meridional slice filter**
(`_should_filter_projection_slice` is on for `world_cone`/`world_sections`), which keeps
only rays lying in the display slice. The scattered retroreflected rays do not, so **every
ray is dropped and the 2D pane projects ZERO rays** — an empty layout. (Measured: the old
mesh trace projects 0 rays; the routed trace projects 279.)

## Fix — share the folded-aware trace between the 3D and 2D paths

The folded trace + post-bundle bend, previously inline in
`_build_preview_system_rays_bundle`, are factored into two shared helpers on the editor
(`ThreeDSceneToolsMixin`):

- `_trace_preview_rays_folded_aware(system, wavelength, max_radius, *, sampling_mode, folded_trace_rows)`
  returns `(rays, fold_transform)`. Unfolded → the plain mesh trace (byte-identical to
  before). A **single** promoted-mirror fold → the straight-equivalent trace (bugs/0197)
  and `fold_transform` for the display bend. A CHAIN / missing equivalent → the sequential-
  Mirror fallback (bugs/0187), `fold_transform = None`.
- `_apply_folded_display_bend(scene_bundle, fold_transform)` runs the straight-equivalent
  bend (when `fold_transform` is set) then the mirror-reflection correction — the same two
  post-bundle steps the 3D builder already did.

`_build_preview_system_rays_bundle` now calls both helpers (behaviour unchanged — the 3D
guards `validate_open3d_ra_mirror_folded_{sequential_trace,cone_converges}` and
`_ra_mirror_hypotenuse_reflection` stay green). `refresh_plot` calls the same two helpers
in place of its direct mesh trace, so the 2D pane now shows the converged folded cone
landing on the drawn detector — 279 projected rays where before there were 0.

## Verification (done)

`KrakenOS/UI/validate_open3d_2d_folded_shows_rays.py` (standalone, display-free — drives
the exact `refresh_plot` call sequence + the real 2D projection pipeline):

1. the OLD direct mesh trace projects to **0** rays in the 2D view (the empty pane);
2. the NEW routed 2D trace projects **279** rays and its world cone converges ON the drawn
   +X detector (endpoint RMS 0.0008 mm at X = 295.577);
3. an unfolded layout (`flat_mirror_45_deg.py`) still projects rays (helper returns `None`
   → the plain mesh trace, unchanged).

STANDALONE (NOT a penta phase) — no penta phase drives the 2D refresh. In-app eyeball
still owed (headless cannot render the matplotlib 2D canvas).
