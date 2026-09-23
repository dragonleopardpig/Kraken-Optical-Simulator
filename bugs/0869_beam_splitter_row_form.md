# 0869 -- the Beam Splitter row form: the sixth family

The shape most of the remaining dialogs take: **pick a surface row, show its settings, validate
them, write them back.** Coating/Material, Advanced Surface, Diffuse/BRDF, Error Map and the
1 902-line CAD face-roles editor are all this.

## The framework

`KrakenOS/UI/row_forms/` -- `FormField` (key, label, kind, choices, hint) and `RowForm` (title,
row index, fields, current values, summary, and the three callables the MODEL owns: `validate`,
`apply`, `describe`). A refusal is `FormRefused` carrying the message to show, so "select a row
first" and "this is not a beam splitter" read the same in both toolkits.

`qt/dialogs/row_form_dialog.py` renders any form: fields in order, hints as tooltips, and
Validate / Apply / Cancel. Porting a row dialog is a builder plus a menu entry.

The Qt shell's **Edit menu** opens the form on the row selected in its surface table; the Tk
dialog was rewired onto the same builder, so its fields, hints, validation and apply are now that
one function.

## Where the model actually lives

The beam splitter's methods (`normalize` / `validate` / `summary` / `coating_for_settings`) are on
the editor, but its three CONSTANTS are module-level -- `BEAM_SPLITTER_SURFACE` in
`trace_intent.py`, the attribute name and the split modes in `services/beam_scatter_metadata.py`
-- and were only ever injected into the Tk dialog shell. The editor itself does not carry them, so
`row_forms.beam_splitter.model(owner)` prefers what the owner holds and falls back to the defining
module. One builder then serves the Tk shell and the editor alike.

## Guard

`validate_open3d_0869_beam_splitter_row_form.py`, penta phase 647. F the form's 11 fields are
exactly the settings the model normalises. R a row out of range and a non-beam-splitter row each
refuse with their own message. V validation is the model's own ("BeamSplitter reflectance must be
in [0, 1]."). A apply writes the settings, regenerates the Coating, keeps the surface and sets the
status line. T the REAL Tk dialog shows the builder's values. Q1-Q3 the Qt form opens on the
selected row with those same values, its Validate returns the same errors, and its Apply leaves
the row in the same state.

Noted, not fixed: after an apply the status line can be overwritten by a later model write (the
row selection). That happens in both toolkits, because it is the model talking.
