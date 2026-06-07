# 0025 — Quick Estimation: live object/image conjugate + FOV solve in 3D

**Status:** Implemented (2026-06-07). Enhancement, not a defect fix.
**Component:** Open 3D thickness handles + a new Quick Estimation service
(`KrakenOS/UI/services/quick_estimation.py`,
`KrakenOS/UI/services/open3d_thickness_dimensions.py`,
`KrakenOS/UI/services/open3d_face_assignment.py`,
`KrakenOS/UI/panels/open3d_live_controls.py`,
`KrakenOS/UI/open3d_inspector.py`).
**Reported via:** the user — a real machine-vision workflow: "the FOV (Object
Height) needs to change regularly by adjusting the object distance and image
distance, fixing the camera (sensor / Image Height is fixed). Do it directly in
3D."

## The interaction model

Four axial quantities, each with a **role**, each typeable:

| Quantity | Row | Roles |
|---|---|---|
| Object Plane | (object reference) | Constant / Independent (derived) |
| **Object Thickness** | `rows[0].thickness` (object distance) | Constant / Independent / Dependent |
| **Image Thickness** | `rows[-2].thickness` (image distance) | Constant / Independent / Dependent |
| Image Plane | (sensor reference) | Constant (pinned sensor) |

Two relations always bind them: the **axial identity** (image plane − object
plane = the gaps + lens body, just bookkeeping in the relative-thickness model)
and the **conjugate / focus** relation through the fixed lens. That is why a
well-posed study pins ~2 (the lens is the implicit permanent constant) and
leaves one Independent (driven) and one Dependent (solved).

The two *thickness* quantities form the conjugate pair. Setting one — **drag or
type a thickness handle in 3D** — promotes it to Independent and re-solves the
partner via the existing paraxial engine (`_compute_paraxial_solve_result`,
"image" or "object" direction) so the image stays focused on the pinned sensor.
**FOV = sensor_semi / |m|** then follows the magnification
(`_current_finite_paraxial_magnification`).

## Implementation

* **`QuickEstimationService`** — owns the role model (`set_role` with
  promote-on-interaction + the focus-absorber rule), `solve_dependent`
  (mutates the dependent row's thickness, no retrace), `preview_state`
  (uncommitted drag feedback, restores the rows), and `current_state` /
  `format_readout` (object dist, image dist, magnification, sensor, FOV, focus).
* **One choke point.** Every thickness change — drag release, click-to-type
  inline editor, numeric entry — flows through
  `Open3DThicknessDimensionService.apply_dimension_value`. Quick Estimation
  hooks there: after the driven gap is set, the dependent is solved and set in
  the same history capture, then a single retrace shows both. So Phase C
  (click-to-type) reuses the existing `edit_dimension` inline editor unchanged.
* **Right-click roles (Phase B).** A right-click on a conjugate thickness handle
  shows a role menu (Variable-Independent / Variable-Dependent / Constant),
  ahead of the CAD-face menu, via
  `_maybe_show_quick_estimation_role_menu`.
* **Live drag (Phase D).** `apply_drag_motion` computes `preview_state` for the
  pending value and pushes the live object/image/mag/FOV into the readout +
  status while dragging; the release commits + retraces.
* **Panel + checkbox (Phase A).** A "Quick Estimation" section in the live
  controls panel: the enable checkbox, the four-quantity + magnification /
  sensor / FOV / focus readout, and role selectors for the two gaps.

## Result

Validated across all five machine-vision layouts (150 mm 1×/0.5×, 120 mm, 85 mm,
150 mm measured): driving the object distance re-solves the image distance to
keep focus (the solved gap reproduces the paraxial conjugate to <0.05 mm), the
magnification matches sensor/FOV, and FOV grows monotonically as the object
moves away. The 1× layouts sit on m = −1 / FOV = sensor; the 0.5× layout on
m = −0.5 / FOV = 2× sensor. Both solve directions work (drive image → solve
object).

## Tests

`KrakenOS/UI/validate_open3d_quick_estimation_conjugate.py` — source contracts
(service API, the `apply_dimension_value` hook, the inspector role-menu methods,
the right-click hook, the `apply_drag_motion` live preview) plus the engine
behaviour across all five layouts (focus held, FOV = sensor/|m|, FOV monotonic,
`preview_state` does not mutate committed thicknesses, reverse solve). Wired into
the comprehensive harness as **Phase 34**.
