# 0929 -- the 3D Live Controls in the Qt shell (phase 5f, part 2)

`panels/open3d_live_controls.py` (559 lines) is a Tk side panel inside the inspector's own
window. Under the Qt shell that window is withdrawn, so none of it could be reached.

## Measured first: most of it already had a Qt home

The panel edits **28** editor variables. **26** of them are the very variables the Qt main window's
System / Source / Trace docks already edit (bugs/0900-0902):
- field type/value/samples, aperture, object mode, wavelength;
- the ray count and the pupil pattern;
- the 12 source inputs;
- the non-sequential trace inputs.

So its Field / Trace / Source sections need no second Qt form. There is one place to edit each.

What the panel adds is named in `KrakenOS/UI/open3d_live_panel.py`:
- the **header**: Live Mode, Trace now, Update 2D;
- the two display variables the docks lack: the **image-diameter mode** and the **camera**;
- **Quick Estimation**: the toggle, the thirteen readouts, three actions (Set Target FOV...,
  Snap to FOV, Config Table...) and the Obj/Img Thk role choices;
- the **Variable-thickness** solve: the gap list comes from the solve service, plus Solve Best
  Focus / Collimation.

`qt/live_controls_dock.LiveControlsForm` lays these out as a **3D Live** dock, tabbed with the
System / Source / Trace / Optimization docks. It binds the same model:
- a widget writes and commits;
- a model write repaints it through `trace_add`.

## Two model/view leaks, both found under Qt

1. **The readouts were the view's.** The inspector started with an empty
   `_quick_estimation_readout_vars`. The Tk panel made thirteen `tk.StringVar`s and handed them
   over, and the Quick Estimation service writes whatever is there. Under Qt nothing was there.
   - The inspector now makes one host variable per key (`self.ui.string_var("--")`).
   - The Tk labels bind to those, and so does Qt.
   - Measured in Qt: turning Quick Estimation on fills 11 readouts (focal length 85.13 mm,
     magnification +0.4096x, FOV 28.12 mm semi, ...).
2. **The thickness toggle read a hidden checkbox.** `_open3d_toggle_variable_thickness` reads the
   Tk checkbox that Tk has already flipped. Under the shell that checkbox still exists, hidden in
   the withdrawn window, and Qt never flips it. So the toggle wrote back the OLD value, and a Qt
   click did nothing.
   - `_open3d_set_variable_thickness(row, enabled)` takes the explicit value and keeps the hidden
     Tk variable in step.
   - Qt calls it; Tk keeps its path.

## Guard

`validate_open3d_qt_5f_live_controls`, penta phase **708**:
- **V**: coverage. Every editor variable the Tk panel edits (28) has a Qt home: 26 in the docks,
  2 in the 3D Live dock. A variable added to the Tk panel without one fails here.
- **R**: the inspector owns the 13 readout variables, and the Tk panel's labels are bound to
  those very variables.
- **Q**: in a real Qt shell on om05a_folded:
  - the dock is there;
  - Quick Estimation fills the readouts;
  - Live Mode, the camera and an Obj Thk role reach the model;
  - a gap checkbox sets the solve service's flag to the value shown, and back (24 gaps).

## Left in 5f

- the design-constraint block (`panels/design_constraint_controls.py`, 269 lines) and the
  embedded compact System Selection form (Qt already has System Selection as a report, 0864);
- the Scene Components tree (1 639 lines).
