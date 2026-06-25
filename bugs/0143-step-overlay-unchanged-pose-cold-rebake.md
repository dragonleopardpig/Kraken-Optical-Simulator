# 0143 — Unchanged STEP-overlay placement re-apply cold-rebakes the hover face metadata

## Symptom

> *"Open 3D … it is live now, still very lag."*

After bug 0142 killed the cold silhouette-edge re-walk, a second per-action stall
remained with the heavy camera STEP + LED plate + beam-splitter loaded: the first
**hover** after almost any editing action (a click that barely moved, a glued LED
following its partner, a scene refresh) froze the inspector for a beat while the
gold face-outline was rebuilt. The freeze tracked the display-only overlays —
worst on the camera, milder on the LED.

## Root cause

Hover/pick draws its outline from `_step_overlay_face_metadata(label)`, which
planar-clusters the imported-CAD triangle mesh into faces. For the **display-only**
labels (`_DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC = {camera, led, lens}`) that is the
**slow planar-clustering path** — ≈**1.9 s** on the camera, ≈**0.2 s** on the LED —
deliberately cached *pose-blind* (baked once per session, with an apply-on-read
axial correction for the image-plane track, bug 0113) precisely to dodge that cost.

But the cache only stays warm if nobody pops it. All four overlay **placement
setters** —

- `_set_step_axis_offset_xy`
- `_set_step_placement_offset_xyz`
- `_set_step_resize_for_label`
- `_set_step_rotation_deg_tuple`

— **unconditionally** popped the face-metadata cache (`_invalidate_step_overlay_face_metadata_cache`,
bug 0050), cleared `_live_step_overlay_trace_plan_cache`, and invalidated the
preview trace **even when re-applied with a value identical to the one already
stored**. That zero-delta re-apply happens constantly in normal use:

- a click that registers as a **zero-delta drag-release** (press → tiny jitter →
  release re-writes the same pose),
- a **glue carry** whose partner delta nets to zero (`_carry_glued_optical_led`
  re-applying the same offset),
- an **orient-onto-face** onto a face the body already sits on,
- a **scene refresh** re-applying the saved pose.

Each of those popped a perfectly valid cache entry, so the **next hover cold-rebaked**
the 1.9 s / 0.2 s clustering for no actual change — the residual lag the user felt.

The pop on a *genuine* move is necessary (bug 0050 / bug 0010: the pose-blind
metadata stores **world** coordinates, so a real translate/rotate must re-bake or
the gold outline floats at the body's former location). The defect was firing it
when nothing moved.

## Fix

`KrakenOS/UI/services/scene_placement_commands.py` — gate the three side-effects on
a before/after **mutation signature**:

- `_step_overlay_mutation_signature(label)` = `(_step_overlay_pose_cache_signature,
  _step_resize_signature, repr(axis-anchor))` — every input a placement setter can
  change that moves or reshapes the body in world space (rotation, axis offset,
  placement offset, resize, axis anchor). The pose component mirrors the overlay
  mesh builder's own transform signature, so it captures exactly what re-poses the
  baked world geometry. (The image-plane axial track is *not* included — it is
  driven by external state, not these setters, and self-corrects on read via the
  bug-0113 `alignment_target_z` delta.)
- `_invalidate_step_overlay_after_mutation(label, before_signature)` runs the
  bug-0050 cache pop + trace-plan clear + preview-trace invalidate **only when the
  signature actually moved**. An unchanged re-apply keeps the cached metadata and
  trace; a genuine change still invalidates, so the ghost-highlight fixes stay
  intact.

Each setter now captures `before_signature` right after its label check, applies
its `setattr` (and any anchor clear) as before, then calls the guarded helper —
the lone bug-0050 invalidation site now lives only inside that helper.

## Verification (`KrakenOS/UI/validate_open3d_step_overlay_unchanged_pose_no_rebake.py`)

A display-free harness (`_Harness(ScenePlacementMixin)`, real signature / pose-cache
/ resize / cache-pop methods, stubbed only for the preview-trace + anchor-clear
display calls) seeds a sentinel cache entry, a sentinel trace-plan entry and a
preview-invalidation counter, then for each of the four setters:

- **Unchanged re-apply** (the value `__init__` already stored): cache entry
  **survives**, trace-plan **kept**, preview-trace **not** invalidated → no re-bake.
- **Genuine change** (a different value): cache entry **popped**, trace-plan
  **reset**, preview-trace **invalidated** → bug 0050 / 0010 unregressed.

All 10 checks pass.

## Guard

- `KrakenOS/UI/validate_open3d_step_overlay_unchanged_pose_no_rebake.py`
  (`run_checks`, display-free): the eight per-setter pins above, plus source wiring
  — the bug-0050 face-metadata invalidation exists **exactly once**, inside the
  guarded `_invalidate_step_overlay_after_mutation`, and all four setters route
  through it (no unconditional invalidation survives).
- Penta phase **132** (`phase_132_step_overlay_unchanged_pose_no_rebake`);
  baseline → 132 = pass.

## In-app eyeball still owed

Headless cannot drive the embedded-VTK hover, so the *felt* responsiveness — a
hover staying instant after a zero-delta click / glue-follow / refresh, while the
outline still re-bakes correctly after a real drag/rotate/resize — is owed an
in-app check alongside the 0142 eyeball.
