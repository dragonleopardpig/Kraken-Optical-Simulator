# 0636 — calculator text reflows on resize + shorter Target-Spot label (user request)

attachment/text.png: the System Selection result text stayed wrapped at a fixed width, so
widening the window/panel did not reflow it. Also the Target-Spot explanation was too long.

## What shipped

- **Reflow**: a wrapped label keeps a FIXED `wraplength` in Tk, so it never re-wraps. The
  shared calculator form (`build_system_selection_form`) now builds its intro, hint and
  result labels via `_reflowing_label`, which binds `<Configure>` to set `wraplength` to
  the live widget width (sticky "ew"). Applies to BOTH the Actions dialog and the 3D
  left-panel section. The matcher dialog's status line reflows the same way.
- **Shorter Target-Spot label** (bugs/0633): now just
  "Target spot ≈ X µm (2× axis pixel pitch, per H/V)" — the axis-pitch reference stays
  explicit without the long diagonal-mismatch aside.

Verified: reflow follows width (wraplength 264 at 300 px → 564 at 600 px); screenshots
bugs/_0636_reflow_narrow.png (wraps) and _wide.png (one line each). Guards unchanged
(phase 473 checks fields/wiring, not label strings).
