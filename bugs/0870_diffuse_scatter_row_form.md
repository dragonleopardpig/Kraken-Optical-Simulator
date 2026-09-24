# 0870 -- the Diffuse / BRDF row form

The second row form, and the one that stretched the framework bugs/0869 built.

## Two field kinds the framework had not met

- a **multi-line** field: the pySCATMECH backend parameters, a JSON/dict blob. `FormField` gained
  `kind="textarea"` (with a `height`), which the Qt dialog renders as a `QPlainTextEdit` and the
  Tk dialog as its `tk.Text` -- and `values()` now reads whichever widget a field asked for.
- a **computed** choice list: the guided target surface offers every OTHER row, so the choices
  come from the layout rather than a constant. `target_options(owner, row_index)` builds them
  exactly as the Tk dialog did, and `target_label` maps the stored index back to its option.

The Tk dialog was rewired onto the builder; the Qt shell opens it from **Edit → Diffuse / BRDF
Settings...** on the selected row.

## What the guard measured, rather than assumed

Two assertions I wrote by analogy with the beam splitter were WRONG, and the measurements are
worth keeping:

**The model clamps; it does not refuse.** `_normalize_diffuse_scatter_settings` pulls every
numeric field into range before `_validate_diffuse_scatter_settings` ever sees it:

| input | becomes |
|---|---|
| reflectance 5 | 1.0 |
| sample_count 0 | 1 |
| max_branch_depth 0 | 1 |
| target_radius_scale 0 | 0.01 |
| roughness_deg 400 | 90.0 |
| max_scatter_angle_deg 200 | 90.0 |
| min_branch_power -1 | 0.0 |

So **validation cannot fire from either dialog.** The one case it still reports is an unknown
`model`, which neither toolkit can produce because that field is a read-only choice. The validator
still earns its place for settings loaded from a file -- but a user typing into the form will
never see it. That is the model's behaviour, not the port's, and both toolkits inherit it; the
beam splitter, by contrast, refuses an out-of-range reflectance outright.

**An empty backend model is not an error**: the form substitutes the default, exactly as the Tk
dialog did, so it never reaches validation.

## Guard

`validate_open3d_0870_diffuse_scatter_row_form.py`, penta phase 648. F the fields are the model's
settings less `polarization`, which it carries from the defaults. C the guided-target choices are
every other row (25 options, the edited row excluded). K the clamp, shown on reflectance. V the
clamp measured across six fields, with the unknown-model case as the only remaining refusal.
A apply writes the settings and makes the row a Diffuse Object with MIRROR glass. T the REAL Tk
dialog shows the builder's values, backend parameters included. Q1-Q3 the Qt form shows the same
values, gives each field the widget its kind asks for (`QPlainTextEdit` for the multi-line one),
and leaves the row in the same state.
