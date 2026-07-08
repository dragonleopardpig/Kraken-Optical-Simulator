# 0265 — analysis-overlay legend overlaps the detector figure ("can space out?")

User flag `flag_20260708_161012_624` (eyeballing the coaxial-LED illumination overlays):

> *"the text label overlap the underlying figure, can space out?"*

The `screenshot.png` shows the grouped illumination legend
("Relative illumination on detector …" + "Coaxial-LED illumination rays …") drawn as a white box
**draped over the top of the detector heatmap**, its lower lines sitting on the figure.

## Root cause — anchored just below the figure edge, grows DOWNWARD

Every analysis overlay (illumination heatmap + rays, and the field-aberration overlays: best-focus,
distortion, astigmatism, spot map, pixel grid) queues its caption into ONE shared billboard drawn by
`Kraken3DInspector._add_grouped_analysis_overlay_label` (`open3d_inspector.py`). That billboard was:

* anchored at `sup * (reach * 0.95)` above the image-plane centre — i.e. **just *inside* the figure's
  top edge** (the figure radius ≈ `reach` = the image-circle radius); and
* drawn **top-justified**, so the multi-line block **grew downward**.

With one short caption that was tolerable, but the illumination legend stacks **six** lines, so the block
grew straight back down over the detector — exactly the flag. (The real scene hit the no-screen-axes
fallback `center + worldY*reach`, which put the anchor barely above the top edge, then the tall block
draped down.)

## Fix — anchor above the figure edge, grow UPWARD

`_add_grouped_analysis_overlay_label` now:

* anchors via a new **pure static helper** `_analysis_overlay_label_anchor(center, normal, sright, sup,
  reach)` at `sup * (reach * 1.15)` — **above** the figure's top edge with margin (a modest `0.6*reach`
  rightward bias; the fallback lifts straight up `worldY*1.15*reach`); and
* draws the block **bottom-justified**, so it **grows upward**, away from the figure.

Because the block bottom now sits above the figure's top edge and expands away from it, the legend cannot
drape over the figure no matter how many overlays are stacked. This applies uniformly to every overlay
that shares the legend, not just illumination.

## Verification

* **Visual (off-screen render, `/tmp/render_label_check.py`)** — reproduced the flag on the fallback path:
  OLD (0.95·reach, top-justified) overlaps the detector quad; NEW (helper, bottom-justified) sits entirely
  above it with a clear gap. Confirms the user's exact symptom and its removal.
* **Display-free guard** `validate_open3d_analysis_overlay_label_placement`:
  * GEOMETRY on the pure helper — canonical basis, a tilted 3/4-camera basis, and the no-screen-axes
    fallback all clear the figure's top edge along screen-up (≥ reach, with ≥10% margin), keep a rightward
    bias, and lift only slightly along the plane normal; a degenerate `reach` still yields a finite anchor
    above centre.
  * WIRING (source) — the drawing method delegates to the helper AND flips the block to
    `SetVerticalJustificationToBottom` (grows up, not down).

## Guard / baseline

* **Phase 234** (`phase_234_analysis_overlay_label_placement`) wraps the guard's `run_checks()`. Registered
  in the `phases` list; `tools/penta_validator_baseline.json` updated (234 → pass). The change is
  render-only and figure-agnostic, so no prior phase is affected.

## Notes

* The legend is a screen-space billboard: the fix guarantees vertical clearance from the *figure*. When the
  figure is zoomed to fill the viewport the upward block can approach the top edge of the window — the user
  can zoom/pan; that is strictly better than draping over the data.
* In-app eyeball owed: headless can't drive the embedded-VTK inspector's live camera, so the user should
  re-toggle the illumination overlays on the coaxial scene and confirm the legend now floats above the
  detector.
