# 0389 — folded RA-mirror "broken rays" are correctly-vignetted rays wrongly DRAWN

**Flag:** `flag_20260721_153640_933` — "FOV changed, the ray still broken. Is the RA mirror
too small?" (scene `machine_vision_AZ85_RA_Mirror.py`, build ba13f4c2).

## The user's question, answered

**No — the RA mirror is not too small, and the trace is physically correct.** Measured on the
real traced scene (3249 rays):

| Quantity | Value |
|---|---|
| Aperture stop (F/4.5) clear semi-aperture | 9.44 mm |
| RA mirror semi-aperture | 12.50 mm — *bigger* than the stop |
| Rays that fold at the mirror and reach the sensor (`hit_detector`) | 2817 |
| Rays that fold then **vignette at the F/4.5 stop** (`stopped`) | 432 |
| Rays that *skip* the mirror / escape | **0** |

Every ray either images correctly or is correctly vignetted **at the aperture stop** (not the
mirror). The field-edge beam is wider than the F/4.5 stop, so the field edges clip — expected,
correct physics. There is no escaping/skip-through ray, and no mid-air break in the physics.

(My first-pass "49 escaping rays" was an artefact of a crude distance-to-mirror-centre metric:
an edge hit sits ~12.5 mm from centre and tripped the threshold, but those rays all fold ~90°
and image. A full ray census corrected it.)

## Root cause — a DISPLAY classifier bug, not the trace

`scene_geometry.ray_path_visible_without_clipping_from_events` decides which rays show with
**Show Clipped Rays OFF**:

```python
if status == "hit_detector":            return True
if ray_path_has_non_refractive_steering(path):  return True   # <-- fired for folded strays too
if status:                              return False
```

The 432 vignetted rays **fold at the mirror** (`non_refractive_steering=True`) *and then*
`stopped` at the aperture stop. The fold rule fired **before** the `stopped` check, so they
were drawn — as segments that fold at the prism and terminate mid-air at the stop. That is
exactly the "broken rays" the user saw. Correct physics, wrong display.

This also matched a latent contradiction with the North Star clipped-ray rule (BRANCH_README):
"every non-folded stray — vignetted/`stopped` rays … — is hidden." A *folded* stray slipped
through the "folds always survive" exception (bugs/0018/0062).

## Fix

In the classifier, a folded ray that a downstream aperture then **vignetted** (`status ==
"stopped"`) is a blocked stray, not an authored branch — it hides with clipping OFF like any
other vignetted ray:

```python
if ray_path_has_non_refractive_steering(path):
    if status != "stopped":
        return True      # BS 2nd path / mirror leg with no detector, absorbed, or escaped
    return False         # folded THEN vignetted at an aperture = blocked stray -> hide
```

Only `stopped` folds hide. `hit_detector` (rule 1), `absorbed`, `missed_detector`, and escaped
folds still survive, so a genuine beam-splitter 2nd path stays visible. **Proven safe on the
real MV-150 beam-splitter scene: 0 `(stopped, folded)` paths — its reflected branch is
`absorbed`, never `stopped`.** With clipping ON, the vignetted rays still show (for inspecting
where the beam clips).

## Verification

- `validate_open3d_clipped_vignetting_parity` (bugs/0062): the `stopped_folded` synthetic case
  flips `True → False`; the docstring + contract updated with the real-scene evidence. All
  other cases unchanged. Passes.
- `validate_open3d_clipped_rays_sync`: still passes.
- `validate_open3d_folded_vignette_hidden` (**new, penta phase 327**): traces the REAL AZ85
  folded scene and asserts it is non-vacuous (432 folded+stopped exist), every folded-stopped
  ray now hides with clipping OFF, and all 2817 image-forming folded rays stay visible.
- MV-150 BS scene: authored reflected branch (`absorbed`) stays visible; 0 folded-stopped.

## Files

- `KrakenOS/UI/scene_geometry.py` — the classifier fix.
- `KrakenOS/UI/validate_open3d_clipped_vignetting_parity.py` — contract + docstring update.
- `KrakenOS/UI/validate_open3d_folded_vignette_hidden.py` — new real-scene guard (phase 327).

## Note on the earlier flag (camera crash into the mirror)

The prior flag (`flag_20260721_153325_838`, "camera crash into the RA mirror" after swap) was
superseded — the user changed the FOV and solved thickness before this one. That collision is a
separate item (the 0388 auto-refocus min-gap clamps the *sensor plane*, but the camera *body*
extends forward of the sensor toward the mirror; a body-aware standoff is the follow-up).
