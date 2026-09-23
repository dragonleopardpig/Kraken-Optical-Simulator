# 0865 -- the Paraxial Calculator, in both toolkits

The first **form** dialog ported: fields, a solve, and an apply that writes back into the layout.
The three families of phase 3 are now all represented -- a report (0859), a report with controls
(0863/0864), and a form that changes the model.

## What moved

About 200 lines of paraxial arithmetic lived inside a Tk closure. It is physics, not layout, and
it is now `KrakenOS/UI/paraxial_calculator.py`:

- `initial_inputs(owner)` -- what the form opens with: the EFL estimate and the layout's own
  object/image gaps, so both toolkits start on identical values;
- `load_from_layout(owner)` -- EFL/H1/H2 from the layout's cardinal points, EP/XP from the
  aperture settings, and the note that says which of those succeeded;
- `solve(owner, inputs, loaded)` -- the four targets (image distance, object distance,
  magnification, distances from magnification), including the matrix-solution path used when the
  form still shows the cardinal points that were loaded;
- `field_states(solve_for, object_mode)` -- which distance fields may be edited, so the two forms
  enable the same ones;
- `apply_solution(owner, payload, result)` -- writes row 0 or the second-to-last row, normalises,
  syncs and returns the status line;
- `CalculatorFailed` for a refusal, and `NothingToApply` for a magnification solve, which has no
  layout cell -- a status line, never an error box, which is what the Tk dialog did.

The Tk dialog was rewired onto all of it (its `_solve`, `_apply_to_layout`,
`_try_load_from_layout` and `_refresh_mode_state` are now thin), and
`qt/dialogs/calculator_dialog.py` is the Qt form: the same fields, Solve, Use Current Layout,
Apply and Apply-and-Close, with the shell's table and 3D view refreshing after an apply.

## Two things worth noting

**The form must not fire its own signals while it is being built.** Setting a combo's text in the
constructor emitted `currentTextChanged` into the field-state refresh before the distance fields
existed -- a `KeyError` at construction. The combos are connected at the end of the constructor.

**The dialog's `tk.StringVar`s had no master.** An unmastered variable attaches to the DEFAULT
root, which is a different interpreter as soon as a second one exists -- so inside the penta
harness (which has its own editor) the calculator's variables lived where its widgets did not, and
the guard read them back empty. They are mastered on the dialog now; the app never noticed because
it has one root, but it was a latent bug either way.

**The opening magnification is 0**, and "Distances from magnification" rightly refuses that
("object distance goes to infinity"). The guard gives that target a usable value on both sides
rather than asserting the refusal away.

## Guard

`validate_open3d_0865_paraxial_calculator.py`, penta phase 644. M both forms open on the model's
values (EFL 100, object gap 5.35 from row 0). S1 the module solves all four targets from one set
of inputs (f=100, m=0.5 -> object 300 mm, image 150 mm). S2 the REAL Tk dialog displays the
module's own result and detail. F the Tk entries follow the module's field-state rule. A1 apply
writes the solved value into row 23 (8.82 -> -5.6524). A2 a magnification solve refuses with
NothingToApply. E a refusal carries the model's message. Q1-Q4 the Qt form opens on the same
values, solves every target to the same results, honours the same field states, and applies to
the same row.
