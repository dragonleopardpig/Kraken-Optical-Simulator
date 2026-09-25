# 0888 -- `RowForm.labels`: when the choice changes what the next field *means*

Insert a component into a beam-splitter arm, or onto a traced `BRANCH_PATH`: pick what it is, say
how far along the path it sits and how wide it is, and give it a local decentre and tilt.

The component choice is not just a type. It **changes what the next field means**:

| component | the parameter is | glass |
|---|---|---|
| Thin lens | `Focal length [mm]` | locked -- "Glass (not used)" |
| Refractive surface | `Radius of curvature [mm]` | live |
| Mirror / Object Target | `Mirror radius [mm] (0 = flat)` | locked -- "Glass (MIRROR)" |
| Detector plane / Aperture stop | `Parameter (not used)` -- locked | locked -- "Glass (AIR)" |

## The tenth family property

`FormField.label` is frozen when the form is built, so `RowForm.labels` is the live half -- the
**fourth live property** after `values`, `choices` and `locked`. Both views ask
`form.label_for(key)` and re-read it on every refresh; neither knows what a thin lens is.

Two smaller things fell out:

- the Tk renderer had to start locking **choice and textarea** widgets, not just entries: a
  choice may now turn any kind off, and a `ttk.Combobox` takes `readonly`/`disabled` rather than
  `normal`/`disabled`;
- `_follow_component` writes `form.values["component"]` itself. A view sets the value before
  calling `on_change`, but a guard or a script driving the model directly should see the same
  form -- and the first version of the guard quietly validated against the *old* component
  because of it.

`panels/main_path_component_placement_dialog.py` 312 -> 62 lines.

## Guard

`KrakenOS/UI/validate_open3d_0888_path_component_form.py` (penta phase 676):

- **B** -- 10 fields for the transmit arm; a non-splitter row refuses with "Right-click a Beam
  Splitter row first.", an unknown path with "Unsupported path: Sideways"
- **L** -- each component relabels the parameter and locks what it does not use
- **V** -- "Thin lens focal length cannot be zero.", "Distance must be positive.", "Distance and
  diameter must be numbers.", "Local offset and tilt values must be numeric."; and choosing a
  thin lens seeds `f = 100`
- **A** -- apply inserts one row on the arm
- **T** -- the REAL Tk dialog **relabelled** "Parameter (not used)" -> "Focal length [mm]" when
  the combo changed
- **Q** -- the Qt dialog relabelled through all three, and the glass field followed (locked for a
  lens, live for a refracting surface)
