# 0241 — "Sensor" and "Image circle" coverage labels overlap on the folded arm

## Symptom
flag_20260706_130527_037, on the promoted two-fold AZ85 periscope: after a 55×55 mm FOV
solve-for-thickness the user reported **"Sensor and Image texts overlap"**. In the screenshot the two
detector-coverage labels at the top of the folded sensor arm — **"Sensor 26.3×26.3"** (orange) and
**"Image circle Ø32.6"** (cyan) — print on top of each other, rendering as the garbled
`Sensor 2Ima6g.3e×2c6ir.3cle Ø32.6`.

## Root cause
`detector_coverage_label_specs` (`detector_coverage_overlay.py`) places each coverage label at a
distinct **clock angle** in the image **plane** — Sensor at 90°, Image circle at 150°, "Needs" at
275° — spanned by the in-plane basis `iu, iv = _basis(detector_normal)`. That spreads the labels when
the image plane is seen **face-on**.

But the user works **edge-on**: the folded reflect arm runs in the −YZ view (camera looking along X).
Seen edge-on, one in-plane basis direction projects to nothing, so the clock spread **collapses onto a
line** and the fixed-screen-size billboards (`vtkBillboardTextActor3D`, font 13, center-justified)
land on nearly the same spot. Worse, several clock angles have a near-zero in-plane component along the
one axis that *stays* visible: Sensor's 90° offset is pure `iv` (= world X, the view axis → invisible),
so it collapses right onto the detector centre; "Needs" at 275° likewise. The center-justified text is
~110 px wide, so even the ~7 mm residual offset of the Image-circle label leaves the two strings
overlapping.

All image labels also shared **one** normal lift (`img_label_center`), so nothing separated them along
the detector normal either.

## Fix
**Stack** the co-planar image labels along the detector **normal** — the one axis still visible when
the image plane is seen edge-on — by a per-label step, *on top of* the existing clock placement:

- `place(...)` gains a `stack` index; the anchor is offset by `stack * _stack_step * _lift_dir`
  (`_lift_dir` = the unit detector normal, the same direction as the base lift).
- Sensor = `stack 0`, Image circle = `stack 1`, "Needs" = `stack 2`, so they read as distinct rows
  from the detector outward.
- `_stack_step = max(sensor_half_diagonal * 0.55, 5.0 mm)` — scales with the element, floored so a
  tiny sensor still clears the fixed-size text.

Face-on the normal offset is **depth-only** (a billboard ignores depth for its screen size/position),
so the tuned clock layout is unchanged. **Sensor stays at stack 0**, so its anchor is byte-identical to
before — the tuned right-edge placement pinned by `validate_open3d_fov_label_edge_on_clearance`
(bugs/0164) is preserved. The object FOV label lives on the other plane and passes `stack 0`, so it is
untouched.

This is a **display-follows-physics** fix in spirit: the labels separate along a real scene axis (the
detector normal the geometry already computed) so they stay readable in the view the user actually
uses, instead of relying on a face-on-only clock spread that silently collapses when folded.

## Verification
`KrakenOS/UI/validate_open3d_folded_coverage_label_decollide.py` (penta **phase 218**):

- **STACKED ALONG NORMAL** — the image labels occupy distinct rows: pairwise separation along the
  detector normal ≥ the stack step (≈10.2 mm for the 26.3 mm sensor); the un-stacked placement shares
  one normal offset (0 mm).
- **EDGE-ON SEPARATED** — under the user's −YZ projection (drop world X) the min pairwise screen
  separation is ≈19 mm (fix), whereas the un-stacked placement collapses a pair to ≈1.8 mm (the
  Sensor/Needs pile-up) — the fail-before/pass-after property.
- **SENSOR PINNED** — the Sensor anchor is byte-identical to its un-stacked (stack-0) placement.
- **FACE-ON PRESERVED** — dropping the normal component, the labels keep distinct clock positions
  (≈17 mm apart), so the face-on layout is unchanged.
- **TEXT + ORDER** — the label texts and order are unchanged; the covering case still drops "Needs".

`validate_open3d_fov_label_edge_on_clearance`, `validate_detector_coverage`, and
`validate_open3d_inscribed_sensor_recommendation` all still pass (they pin label text/order and the
Sensor anchor, none of which changed). The labels are VTK billboards and can't be pixel-validated
headless (llvmpipe SIGSEGV); this guard checks the label-anchor geometry the renderer consumes. In-app
visual confirm owed (restart the app onto this build, redo the folded solve, confirm the Sensor and
Image-circle labels read as separate rows).
