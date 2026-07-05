# 0234 — Object-distance fold split desyncs the trailing mirror on a two-fold periscope

## Symptom
flag_20260706_070942_311: on the two-fold AZ85 periscope the user double-clicked the FOV plane,
typed 55×55 mm, then clicked **Apply split (move mirror)**. They reported:

- "FOV not changing" — the FOV was unchanged.
- "first RA mirror seems shifted, but 2nd RA mirror wrong location."
- "The rays even bend without touching the 2nd RA mirror."

## Root cause
Two independent things:

1. **FOV unchanged** is expected-but-confusing: the FOV Width/Height boxes are read only by
   *Solve for Thickness* / *Solve for Image Size* (`run(mode)` → `_apply_quick_estimation_fov_solve`).
   The separate *Apply split (move mirror)* button (`_add_folded_conjugate_split_section._apply`)
   ignores the FOV boxes entirely — it only slides the mirror. Typing a FOV then clicking split
   applies nothing to the FOV.

2. **Broken geometry** is the real defect. `_apply_folded_object_split` slides the object-side
   fold mirror by trading the object gap (row 0) against the trailing air spacer. On a **single**
   fold every downstream element is a plain row that re-derives from the folded-axis walk, so the
   slide is a clean mechanical repackaging. On a **two-fold** periscope the trailing (2nd) mirror is
   pinned to an absolute incoming-axis placement (bugs/0218) and does **not** follow the object-gap
   walk. Measured headless on the promoted two-mirror AZ85, sliding the object leg +20 mm:

   | element                | before            | after             | follows beam? |
   |------------------------|-------------------|-------------------|---------------|
   | mirror 1 (object fold) | (0, 0, 71.9)      | (0, 0, 91.9)      | yes (+20 Z)   |
   | lens                   | (97.5, 0, 71.9)   | (77.5, 0, 91.9)   | yes           |
   | detector               | (181.4, 0, −13.6) | (161.4, 0, 6.4)   | yes           |
   | beam 2nd-fold vertex   | (181.4, 0, 71.9)  | (161.4, 0, 91.9)  | yes           |
   | **mirror 2 (trailing)**| **frozen**        | **frozen**        | **no**        |

   Everything moves with the beam except the drawn 2nd mirror, so the beam folds ~28 mm away in
   empty space beside it — exactly "rays bend without touching the 2nd RA mirror."

## Fix
`_folded_object_conjugate_split` now returns `None` when a fold mirror exists **downstream** of the
object mirror (`any(f > mirror_row for f in folds)`), so the split section is not offered and
`_apply_folded_object_split` refuses. On the object-plane popup a two-fold scene shows a short note
explaining why fold-mirror repositioning is unavailable. Single-fold scenes are byte-for-byte
unchanged (the object mirror is the only fold; the split still reports its legs, slides, and keeps
the total conjugate fixed).

The proper feature — carrying the whole image arm (trailing mirror + camera + detector) with an
upstream gap change so it stays on the beam — is a display-entangled increment (deferred; the same
blocker as the image-side split). **Related risk:** the folded FOV *Solve for Thickness* applies the
same object-gap change (`_folded_conjugate_gaps_for_magnification`, object_gap_row=0) and would
desync the trailing mirror the same way on a two-fold scene; it is only validated on single-fold so
far (penta phase 209). Tracked for the same image-arm-follows increment.

## Verification
`KrakenOS/UI/validate_open3d_folded_split_two_fold_gated.py` (penta phase 211):
- **TWO-FOLD GATED** — split is `None`, Apply refuses on the promoted two-mirror AZ85.
- **ROOT CAUSE** — forcing the slide moves mirror 1 (+20 mm) and the beam 2nd-fold vertex
  (+28 mm) while the trailing mirror stays frozen (0.0 mm), i.e. the drawn 2nd mirror leaves the
  beam.
- **SINGLE-FOLD UNAFFECTED** — the one-mirror AZ85 split still applies and keeps the total conjugate.
- **WIRED** — the gate is in the split source and the note is in the dialog.

The existing single-fold guard `validate_open3d_folded_conjugate_split.py` (phase 207) still passes.
Overlays/3D are a VTK render and can't be pixel-validated headless (llvmpipe SIGSEGV); this guard
checks the geometry the renderer consumes. In-app visual confirm owed.
