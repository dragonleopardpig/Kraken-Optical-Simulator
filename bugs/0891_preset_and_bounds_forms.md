# 0891 -- two more tail dialogs, and where an error is allowed to go

The tolerance-solve preset (`main_tolerance_report_dialogs.py`) and an optimisation variable's
bounds (`main_optimization_panel.py`). Neither needed anything new from the framework.

What they **did** need was care about where an error goes:

- the bounds dialog has **never shown a message box**. A bad entry goes to the **debug log** and
  the dialog stays open;
- the preset dialog reports through `append_debug` *as well as* the status line.

Turning either into a modal error box would have been a behaviour change dressed up as a port.
So the builders raise `FormRefused` with the model's own wording and the **panels decide where it
lands** -- `append_debug` here, `status_var` in 0890's galvo dialog, a message box elsewhere.

The preset's compare-view list is one more **constructor kwarg** with a module fallback
(`tolerance_constants.TOLERANCE_COMPARE_VIEW_VALUES`), which is now the routine shape of
`model(owner)`.

## A guard that proved nothing, and its fix

The first version of the debug-log check set `current_menu_row_id = None` and asserted nothing
was logged. But `edit_current_bounds` returns on that check **before it ever reaches the
builder**, so the assertion held for the wrong reason -- a vacuous pass of exactly the kind
`feedback_guards_assert_claims_not_calls` warns about.

It now drives the **real panel method** with a builder that refuses, and asserts the message
reached the log and that no message box opened:

```
W: a bounds refusal reached the DEBUG LOG (["the guard's own refusal"]) and opened no message box
```

## Guard

`KrakenOS/UI/validate_open3d_0891_preset_and_bounds_forms.py` (penta phase 679):

- **P** -- seven fields; "Give the preset a name.", "Monte Carlo samples must be at least 1.";
  Save wrote a named preset
- **B** -- "Optimization bounds rejected: lower must be less than upper.", "Invalid optimization
  bounds entry."; Save wrote `(-5.0, 5.0)`
- **W** -- the refusal reached the debug log, no message box
- **T** -- the REAL Tk preset dialog drew 6 entries and a combo under Validate/Apply/Cancel, and
  it grabbed
- **Q** -- the Qt preset dialog refused a blank name and saved
