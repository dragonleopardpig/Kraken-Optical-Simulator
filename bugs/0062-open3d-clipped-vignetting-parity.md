# 0062 — Open 3D: "Show clipped rays" OFF must hide vignetting like 2D does

## Reported (recorder bundle `flag_20260611_154110_547`)

> disable clipped rays still show up.

Direct follow-on to bugs/0061. That fix gave the 3D inspector a **Clipped**
toggle synced to the 2D "Show clipped rays" checkbox (one shared
`show_clipped_rays_var`). But turning it OFF still left a wide fan of stray rays
on screen in 3D — the same machine-vision LED → lens → camera layout
(`machine_vision_150mm_test.py`) where rays fan out from the LED and a large
fraction vignette at the aperture stop / lens rims. In 2D those strays vanish
when clipping is OFF; in 3D they stayed.

## Root cause

bugs/0061 synced the toggle **state**; the two views still ran **different
filters** under that one var:

- **2D** — `scene_renderer_2d._draw_rays` (scene_renderer_2d.py:195) skips any
  ray where `not projected_ray_hits_detector(ray)`. That predicate is just
  `projected_ray_terminal_status(ray) == "hit_detector"` (scene_geometry.py:698),
  so 2D clipped-OFF shows **only detector hits**.
- **3D** — `ThreeDSceneToolsMixin._iter_3d_scene_ray_records`
  (three_d_scene_tools.py:1877) filters on
  `ray_path_visible_without_clipping_from_events` (scene_geometry.py:540), whose
  bugs/0016+0018 form kept *every* traced ray and hid **only escaped,
  non-folded** rays. Rays that vignetted and `stopped` on the aperture/lens rim
  — or that `missed_detector` — are not "escaped", so 3D kept drawing them.

For the flagged layout the trace is 39 `hit_detector` + 24 non-folded `stopped`
(0 escaped). 2D clipped-OFF → 39 lines; 3D clipped-OFF → all 63. Hence "disable
clipped rays still show up": the 24 stopped strays were never gated in 3D.

## Fix (3D filter only)

Tighten the 3D-only predicate `ray_path_visible_without_clipping_from_events`
(scene_geometry.py:540) to the 2D rule — visible-when-OFF iff the ray **hit the
detector** *or* underwent a **deliberate fold**:

```python
status = ray_path_terminal_status_from_events(path)
if status == "hit_detector":
    return True
if ray_path_has_non_refractive_steering(path):
    return True
if status:
    return False
return bool(getattr(path, "reaches_image", False))
```

The fold clause keeps the prior invariants intact: bugs/0016 (a TIR/mirror-folded
scene whose rays all `missed_detector` stays visible) and bugs/0018 (the
beam-splitter reflected "2nd path", which is an `escaped` fold the user asked to
see). Every *non-folded* stop / miss / absorb / escape — pure vignetting — is now
gated behind Show Clipped Rays, exactly as in 2D. The bug-0022 don't-blank
fallback in the 3D filter still shows all rays if the filter would otherwise hide
every one. **The 2D filter is untouched** (it already hid these); only the 3D
predicate moved, so 3D now follows 2D.

## Tests

- **`KrakenOS/UI/validate_open3d_clipped_vignetting_parity.py`** (new,
  display-free) — Phase 64:
  - synthetic `RayPath3D` per case: detector-hit and *folded* branches (folded
    stop / folded escape) survive clipped-OFF; non-folded stop / miss / escape
    are hidden;
  - real fold-free `machine_vision_150mm_datasheet_1x.py` trace (45 paths = 27
    `hit_detector` + 18 vignetted `stopped`): the wired 3D filter renders all 45
    with clipping ON and exactly 27 with it OFF, and that 27 equals the number of
    rays the **2D** filter keeps (`projected_ray_hits_detector`) — the two views
    now agree.
- **`KrakenOS/UI/validate_open3d_traced_rays_always_visible.py`** (retargeted —
  the bugs/0016 guard, Phase 25): Section 1 now expects `absorbed` / `stopped` /
  `missed_detector` **hidden** when clipped-OFF (non-folded), keeps `hit_detector`
  visible / `escaped` hidden, and adds a folded-stop / folded-miss / folded-escape
  block asserting a deliberate fold stays visible regardless of terminus. The
  mirror-fold and beam-splitter sections still pass because those rays are folds.
- **`KrakenOS/UI/validate_open3d_clipped_rays_sync.py`** (updated — the bugs/0061
  guard, Phase 63): check F's clipped-OFF expectation tightened from
  `{1,2,3,4}` to `{1,3}` (only the detector hit + folded escape survive).

## Penta phase

**Phase 64** — `phase_64_open3d_clipped_vignetting_parity` wraps the new guard's
`run_checks` (display-free, runs everywhere). Baseline regenerated with phase
64 = pass (65 phases, 0–64).
