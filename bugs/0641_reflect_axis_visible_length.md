# 0641 — the BS reflect axis has a visible minimum length (user report)

flag_20260824_141739 ("No 2nd optical axis created") — the follow-up to bugs/0640, which
made the coating recognised (coatings 0→1, reflect axis emitted). The user still saw no
second axis. Two causes, confirmed by headless render:

1. **Length (fixed here).** `_bs_reflect_axis_guide_records` set the guide length to
   `reach = max((bounds corners − fold_point) · reflect_dir)` — the scene's extent in the
   reflect direction. A coaxial BS reflects the imaging axis toward the nearby LED, and
   nothing is placed on that arm, so it clamped to the bounding-box edge: a **78 mm** stub
   vs the **1654 mm** main axis (ratio 0.047). Fix: a MINIMUM length `0.6 × max(bounds
   dimension)` → the reflect axis is now **431 mm** (ratio 0.26) — a real second axis.

2. **Default view (NOT a code bug).** The inspector's default camera for this scene is a
   LEFT side view looking **straight along +X**, and the reflect axis runs +X — so it is
   edge-on and foreshortens to a point regardless of length. From a TOP (look along Y) or
   oblique view it is clearly visible (verified: bugs/_0641_axes_after_fix.png top-down
   shows it plainly; bugs/_0641_axes_fixed_default.png shows the edge-on default). The user
   just needs to rotate to TOP; whether to change the DEFAULT orientation for a two-axis
   BS-reflect scene is left as an open UX question.

Verified: guard phase 480 (the reflect guide takes a scene-sized minimum length). Screens:
bugs/_0641_axes_after_fix.png (top-down, visible), bugs/_0641_axes_fixed_default.png (default
LEFT view, edge-on).
