# 0889 -- `RowForm.read_only`: a form that reports

bugs/0634's Camera + Lens Matcher: enter the field of view, the resolution you need on it, an
optional minimum working distance and a wavelength, and every registered camera x catalog lens
combination is listed -- passing ones first, with the reasons the others fail, and an explanation
for whichever you select.

`services/system_matcher.py` 455 -> 339 lines; the dialog is one call.

## Why this is a record list and not a report

The report family (`Report` + `ReportValue`) already does *inputs + a table*, and this dialog
looks exactly like that. But a report **rebuilds when a control changes**, and the first match
scrapes the lens datasheets -- 10-20 s. Re-running that on every committed field would be a
worse dialog than the one we have.

So it is a record-list form whose Match is a **`FormAction`**: the user says when. What it then
lacks is anything to write back, which is the new property:

```python
read_only: bool = False   # inputs and verbs, but nothing to Apply
```

A view with `read_only` shows neither Validate nor Apply and calls its Cancel button **Close**.
Measured on the real dialogs: Tk draws exactly `['Match', 'Close']`, Qt the same.

## Guard

`KrakenOS/UI/validate_open3d_0889_catalog_matcher_form.py` (penta phase 677):

- **B** -- five inputs (the FOV prefilled from the scene: 56.2476 mm) and an empty 7-column list
- **R** -- a missing height, a missing resolution and a negative width each refuse with the
  model's own message
- **M** -- Match listed **252** combinations, **88** passing (12 cameras x 21 lenses)
- **S** -- selecting one explains it: `MATCH <camera> + <lens>: |m|=..., WD~... mm, image
  circle ... mm`, or every reason it fails
- **T** -- the REAL Tk dialog shows `['Match', 'Close']` over its result list
- **Q** -- the Qt dialog the same, with `apply_button` and `validate_button` both `None`

bugs/0634's own guard still passes unchanged (its six checks include "dialog + editor + menu
wired"), which is the useful confirmation that the port kept the feature it was written for.
