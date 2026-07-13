# 0291 — "the detector and object plane seem missing" after Add LED

Flag `flag_20260713_090936_572` (description: *"Add LED illumination pop up a yellow plane with a slider
arrow. What am I suppose to do? Also, the detector and object plane seems missing, is this suppose to be
the correct behaviour?"*), immediately following the 0290 module-seed work on the MV-150 coaxial scene.

Two questions in one flag:

1. **What is the yellow plane + arrow / what do I do with it?** — cosmetic/UX, answered below.
2. **Why do the detector and object plane look missing — is that correct?** — the real bug, fixed here.

## Symptom
On the real vendor scene (`attachment/machine_vision_150mm_test.py`), pressing **Add LED illumination**
makes the sequential **detector (Image) plane disappear** from the 3-D scene. The object plane also looks
gone.

## Root cause (confirmed end-to-end through the real API — `bugs/diag_0291_missing_detector_object.py`)
Adding a physical LED seeds an illumination flood (0290). That flood reflects off the promoted beam-splitter
cube into arms that never converge, so the branch-detector deriver (bugs/0088) parks **phantom** branch
detectors beside the cube. bugs/0285 correctly marks every non-imaging flood branch `draw_suppressed`
(kept only as a ray hard-stop, `focus_source != "reached_image"`) so none of them *draws*.

But `drop_superseded_image_display` (`scene_builder.py`, bugs/0093/0098) dropped **every** sequential
`is_detector` target (`-1 < row_index < 100000`) whenever *any* branch detector existed
(`has_branch_detector = bool(branch_detectors)`). So the real detector was dropped **for phantoms that
themselves never draw** → nothing replaced it → the scene lost its only visible detector.

```
[no-LED]  targets: row 0 (object)  row 5 (aperture)  row 8 (detector, DRAWN)          labels incl. 'Image'
[with-LED, pre-fix] the branch flood exists → row 8 dropped → NO detector target, no 'Image' label/curve
```

### The object plane was NEVER dropped
`row 0` (object_reference) is present in the targets, `surface_curves`, and labels in **both** cases. The
"object plane missing" is a **camera-framing artefact**: the object sits at z=0, far off the left edge of the
default view, and the added LED emitter glyph dominates that region. Nothing to fix on the object.

## Fix (SHIPPED — general, display-follows-physics)
The sequential Image is *superseded* (droppable) for **two** independent, principled reasons:

* **bugs/0093/0098/0090** — a branch detector that will actually **DRAW** replaces it (the correct per-arm
  display), **or**
* **bugs/0184** — the whole scene is a **diffuse double-pass**, so the sequential trace is itself noise
  (every branch detector is draw-suppressed *and* the Image is dropped).

An illumination flood (bugs/0285/0291) is **neither**: it parks branch detectors that are all
draw-suppressed **without any diffuse scatter**, and the sequential Image is the **one real imaging
detector**. So keep it.

`scene_builder.py` `build_scene_bundle` now computes:

```python
has_drawn_branch_detector = any(
    row_index >= 100000 and not metadata.get("draw_suppressed")
    for target in scene_targets
)
supersedes_sequential_image = has_drawn_branch_detector or scene_has_diffuse_scatter
drop_superseded_image_display(..., has_branch_detector=supersedes_sequential_image)
```

(`scene_has_diffuse_scatter` is hoisted to `False` before the branch-detector `try` so it is always defined.)
The `drop_superseded_image_display` helper itself is unchanged — only its call-site gate changed.

### End-to-end outcome (real vendor scene + synthetic OPT-CO90 — `bugs/diag_0291_missing_detector_object.py`)
| scene | detector row 8 | phantom row 100000 | object row 0 | 'Image' label |
|---|---|---|---|---|
| no-LED baseline | present, DRAWN | — | present | yes |
| + module-seeded LED (pre-fix) | **dropped** | suppressed | present | **gone** |
| + module-seeded LED (fixed) | **present, DRAWN** | suppressed | present | **yes** |

## Non-regression
* **bugs/0184** (`validate_open3d_branch_detector_leak_clutter`) — the diffuse double-pass still drops the
  sequential Image (0 footprints drawn at 15 and 60 rays): the `or scene_has_diffuse_scatter` term preserves
  it. Verified: the first attempt (drop gated on the drawn-branch count alone) regressed 0184; adding the
  scatter term restored it.
* **bugs/0093/0098/0090** (`detector_redundancy_drop`, `superseded`, `beam_splitter_branch_detectors`) — a
  DRAWN branch detector still supersedes the sequential detector.
* **bugs/0285** (`illumination_flood_phantom_branch_detector`) — the phantom flood branch stays
  `draw_suppressed`.

Guard: `KrakenOS/UI/validate_open3d_illumination_keeps_real_detector.py` (`run_checks()`), penta
**phase 255**, baseline updated.

## The yellow plane + arrow (question 1)
That is the **illumination LED emitter glyph** (bugs/0283): a translucent plate = the emitting aperture, with
an arrow = the emission direction. It is a scene object, not a control — there is **no functional slider**
yet (a drag/move gizmo is backlog, `project_open3d_scene_source_object`). The source is already emitting
(its rays are in the scene); to see its footprint on the sensor use the **Relative Illumination** overlay.
