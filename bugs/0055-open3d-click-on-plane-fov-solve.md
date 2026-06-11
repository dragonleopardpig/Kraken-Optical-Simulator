# 0055 — Open 3D: graphical click-on-plane FOV solve (object + image planes)

## Motivating request (user's words)

> need to improve the "Set Target FOV":
> 1) Can we do that graphically for Object? Click on the object in 3D canvas →
>    pop up input box → input the FOV in horizontal dimension (not diameter) →
>    There are two buttons to click beneath the input box: Solve for Thickness
>    and Solve for Image/Sensor Size.
> 2) The same reasoning go for Image plane.

The old "Set Target FOV" was a menu-buried, screen-centred text dialog that asked
for the *full Object Height* and only ever stored a target (you then dragged a gap
or used a separate "Snap" menu pick). The user wanted it **graphical and direct**:
click the plane you care about, type the **horizontal** field width, and pick what
the solver should change.

## Feature

**Double-left-click** the Object plane *or* the Image plane disk in Open 3D opens a
small modal box, pre-filled with that plane's current **horizontal** field width
(not the image-circle diameter / diagonal). Two buttons beneath the entry:

- **Solve for Thickness** — move the object↔image **conjugate pair** so the typed
  field fills / maps to the sensor, in focus. The sensor is left untouched.
- **Solve for Image/Sensor Size** — keep the conjugates (current magnification) and
  **resize the terminal sensor** so the typed field maps onto it. No thickness
  changes.

A plain single click still just selects the plane row (non-intrusive); the gesture
is the well-understood double-click "edit" idiom. The existing right-click Quick-
Estimation role menu (Set Variable / Snap / Configuration table…) is unchanged.

### Horizontal vs. diameter

The optical model's FOV/sensor is a **circle** (semi-height = radius, `diameter` =
the image circle), so a *horizontal width* only differs from the diameter once an
aspect is assumed. We use the working machine-vision aspect
(`SENSOR_ASPECT = 4:3`), giving `horizontal / diagonal = 4/5 = 0.8`. The box reads
and writes the horizontal width; the solver converts width↔diagonal internally.

### Object plane vs. image plane

| typed value | Solve for Thickness | Solve for Image/Sensor Size |
| --- | --- | --- |
| **Object** field width | conjugates so an object of that width fills the current sensor (`set_target_fov` too) | resize sensor `= |m| × object width` at current magnification |
| **Image**/sensor width | conjugates so the *current object field* images to that width on the unchanged sensor | resize sensor directly to that width |

## Implementation

- **Solver (`KrakenOS/UI/services/quick_estimation.py`)** — new on
  `QuickEstimationService`:
  - `_aspect_horizontal_fraction` / `horizontal_to_diagonal` /
    `diagonal_to_horizontal` (4:3) and the `object_fov_horizontal` /
    `sensor_horizontal` readouts (popup prefills).
  - `_conjugate_pair(object_semi, image_semi)` → `(object_distance,
    image_distance, |m|)` for `|m| = image/object` in focus (the lens-equation
    math, generalised from `snap_to_fov`'s sensor-only case);
    `_apply_conjugate_pair` writes both gaps.
  - `apply_sensor_diagonal(diagonal, horizontal)` writes `rows[-1].diameter`.
  - `fov_solve(plane, mode, horizontal)` orchestrates the four cases above; never
    retraces (the caller owns it). `snap_to_fov` is left intact (Phase 34).
- **Gesture + popup (`KrakenOS/UI/open3d_inspector.py`)** —
  `_maybe_open_fov_popup_from_double_click(event)` re-uses
  `_surface_row_under_cursor` + `rows[srow].surface == "Object"/"Image"` (the same
  pick the right-click role menu uses) and schedules the box via `after(1, …)` so
  the popup never opens inside the Tk event handler.
  `_open_quick_estimation_fov_popup(plane)` builds the entry + two solve buttons +
  Cancel (centred via `_show_centered_dialog`, Esc cancels).
  `_apply_quick_estimation_fov_solve(plane, mode, value)` wraps the solve in a
  history capture, syncs the table/object controls, and retraces — mirroring
  `_quick_estimation_snap_to_fov`.
- **Binding (`KrakenOS/UI/services/open3d_mouse_bindings.py`)** — a new
  `<Double-Button-1>` → `double_left_press` handler routes to
  `_maybe_open_fov_popup_from_double_click`. Tk fires `<Button-1>` on the first
  press (so the row still selects) and the more-specific `<Double-Button-1>` on the
  second, so the gesture doesn't disturb single-click selection.

## Tests

- `KrakenOS/UI/validate_open3d_fov_plane_solve.py` — display-free, deterministic
  via a stubbed paraxial engine (f=50, |m|=0.5): the 4:3 horizontal↔diagonal
  mapping + readouts; all four solve cases (object/image × thickness/sensor) hit
  the expected conjugate distances / sensor Ø and leave the *other* quantity
  untouched; bad/under-specified input is refused with the model untouched; and the
  gesture/popup wiring (`<Double-Button-1>` → router → two buttons → `fov_solve`)
  is asserted against the source.
- Phase 60 in the comprehensive validator (`phase_60_fov_plane_solve`) — boots the
  inspector, stubs the same deterministic engine, drives the real
  `QuickEstimationService.fov_solve` for all four cases, runs the real
  `_apply_quick_estimation_fov_solve` retrace path once (must not raise), and
  asserts the gesture wiring. Added to the baseline (61 phases, 0–60).

## Notes / follow-up

- The 4:3 aspect is the working assumption; if a rectangular vendor sensor
  (`active_width_mm` / `active_height_mm`) is ever made the optical aperture (today
  it's overlay-only, phases 37–38), the horizontal mapping should read that aspect
  instead of the constant.
- "Solve for Image/Sensor Size" resizes the **circular optical aperture**
  (`rows[-1].diameter`); the detector-overlay rectangle follows via the existing
  diameter fallback in `scene_target_active_dimensions`.
