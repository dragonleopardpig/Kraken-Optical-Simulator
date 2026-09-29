# 0930 -- design constraints and the System Selection calculator in Qt (phase 5f, part 3a)

The Tk Live Controls panel embeds two calculators that 0929 left behind.

## The design-constraint block

`panels/design_constraint_controls.py`: pin first-order knowns (magnification, object / image
distance, total track, object FOV), then solve for the lens (Design) or place a fixed lens
(Placement).
- All the optics was already in the Quick Estimation service (`design_constraint_view`,
  `placement_constraint_view`, `_apply_*_constraints`).
- But the rows, the header, the pin collection and the evaluate / apply calls were written into
  the Tk class.

Those are now **`KrakenOS/UI/design_constraints_model.py`**. The Tk class keeps only its layout
and calls the model. The Qt 3D Live dock's new **Solve: constraints** group calls the same
functions.

Measured in Qt: pins |m| 0.5 + object 100 mm show "Need EFL ~ 33.33 mm (object 100 mm, image 50 mm,
|m| 0.5, track 150 mm)", the service's own message. The three quantities they lock are filled and
disabled, and Apply moves the object and image gaps.

## The System Selection calculator had never been ported

The plan's phase-3 table listed "0864 | System Selection Calculator". That was wrong: bugs/0864 is
the **Gaussian Beam** report. The calculator (bugs/0631) existed only as a Tk builder,
`build_system_selection_form`, used by the main window's dialog and the live panel. Its input
parsing and answer lived inside that builder's `recompute`.

- **`system_selection_text(values, camera_pixels)`** is the one parser and composer. The Tk
  builder's `recompute` now calls it.
- `system_selection_prefill_values(editor)` gives the from-scene prefill.
- **`row_forms/system_selection.py`**: the calculator as a read-only `RowForm`.
  - Each input's `on_change` recomputes the static Result.
  - "From scene" re-reads the FOV / sensor / camera.
- **Qt**: *Analysis -> System Selection Calculator...*, and a button in the 3D Live dock that opens
  the same dialog: one copy, not a second embedded form.

The plan's table row is corrected.

## Guard

`validate_open3d_qt_5f_constraints_selection`, penta phase **709**:
- **S**: the Tk form's live result equals `system_selection_text` for the same seven typed inputs.
- **D**: the Tk live panel's constraint block, given two pins, shows exactly the model's message.
- **Q**: the Qt block shows the service's answer; the locked quantities are shown and disabled;
  Apply moves the gaps; the dock button opens the calculator, which recomputes on input.

## Left in 5f

- the Scene Components tree (1 639 lines).
