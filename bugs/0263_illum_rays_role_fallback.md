# 0263 — "Illum rays" overlay draws nothing in the live app (strict `source_role` gate collapses to None)

User feedback (2026-07-08, eyeballing the just-shipped 0259–0262 illumination overlays), four in-app
flags recorded back-to-back:

* `flag_20260708_151620_147` — *"Illumination overlay on, seems working."* (Feature A heatmap)
* `flag_20260708_151638_238` — *"Illumination rays on, don't see any difference."*
* `flag_20260708_151854_588` — *"zoom in view, with illumination rays off."*
* `flag_20260708_151913_292` — *"zoom in view, with illumination rays on, seems no difference."*

So: the **heatmap (Feature A) renders**, but the **"Illum rays" overlay (Feature B) draws nothing**,
even zoomed in. The live scene in the flag `state.json` is the coaxial imaging stack **unfolded**
(optical axis along Z), which rules out a folded / short-`min_z_span` cause.

## Root cause — B is role-strict, A is role-agnostic

Both features start from the same `_collect_ray_analysis_records()`. But:

* **Feature A** (`services/source_illumination_analysis.py`) bins **all** detector hits — no
  `source_role` filter.
* **Feature B** (`build_source_illumination_rays_overlay`) **hard-gated** on
  `source_role == "illumination"` and returned `None` the moment no record carried that literal tag:

  ```python
  for record in records:
      if role is not None:
          if str(record.get("source_role", "")).strip().lower() != str(role).strip().lower():
              continue
      ...
  if not reaching and not clipped:
      return None
  ```

The coaxial *validator* layout tags its LED `role="illumination"`
(`common_optical_layouts/machine_vision_150mm_coaxial_led.py:76`), so the guard and headless harness
were green. But a **user-built** scene whose LED source role does not round-trip to that exact string
(blank, `None`, `"led"`, …) matches **zero** records → `None` → the inspector returns before drawing
(`open3d_inspector.py:_add_source_illumination_ray_overlays`, the `if not spec` early-out). The
overlay silently vanishes while the role-agnostic heatmap keeps working — exactly the flags.

Reproduced headlessly (`/tmp/diag_illum_rays.py`): the production coaxial records histogram to
`{'illumination': 8000}` and B yields `reaching 1714 / clipped 1469`; blanking the tag to `''`,
`None`, or `'led'` collapsed B to `None` in every case while A stayed OK.

## Fix — prefer the role, but fall back to every traced ray

`build_source_illumination_rays_overlay` now splits the **role-matched** records first, and **only if
that yields nothing drawable** falls back to **all** records rather than returning `None`:

```python
role_matched = [record for record in records if _role_matches(record)]
reaching, clipped = _split(role_matched)
if not reaching and not clipped and len(role_matched) < len(records):
    reaching, clipped = _split(records)
if not reaching and not clipped:
    return None
```

This mirrors Feature A (role-agnostic) and honours **"rays trace regardless of element placement"** /
**"display follows the physics engine"**: if rays were actually traced to the detector, the overlay
draws them; it does not gate the picture on a bookkeeping string. When the role *does* match (the
normal tagged scene), the fallback stays **dormant** — behaviour is unchanged, and any genuinely
foreign rays (e.g. an imaging ray in a mixed set) stay filtered.

## Verification (display-free)

* `/tmp/diag_illum_rays.py`: the three blanked-role variants (`''`, `None`, `'led'`) now each return
  `reaching 1714 / clipped 1469`, identical to the tagged case; Feature A unchanged.
* **Guard** `validate_open3d_source_illumination_rays` gains `_check_role_fallback`:
  * **Dormancy** — with the role present, the tagged split is exactly `n_reach / n_clip` (the foreign
    imaging ray stays out); the fallback must not leak it in.
  * **Fallback** — blank/`None`/foreign the role on every record: each variant must still draw BOTH
    classes, never `None`, and never fewer rays than the role-gated path.
  * Pure geometry, integration (real 8000-ray coaxial trace), cache, and render-only/toggle contracts
    all still PASS.

## Guard / baseline

* **Phase 232** (`validate_open3d_source_illumination_rays`) — same guard, one added check; **title
  unchanged**, so the penta baseline is **untouched** (no new phase, no rename).

## Notes

* The deeper ergonomic gap the flags expose — a user has no first-class way to *mark* a face/surface
  as the illumination source, so the role only ever gets the literal tag from a pre-built layout — is
  a **separate follow-up** (add an "Illumination" surface kind to the face editor + right-click
  assignment). This fix makes the overlay robust in the meantime; the follow-up makes the role
  *intentional* rather than incidental.
* In-app eyeball still owed: headless can't drive the embedded-VTK inspector, which is why the flags
  (the user's own eyeball) caught this. After this fix the user should re-toggle "Illum rays" on the
  live coaxial scene and confirm the green/red rays now appear.
