# 0896 -- the paraxial matrix and Gaussian beam reports render their builders

The last report-family panel that still drew its own tables. Both builders already existed --
`reports/paraxial_matrix.py` (0859) and `reports/gaussian_beam.py` (0864), which Qt has rendered
ever since -- but the Tk dialogs kept **211 lines of layout** over them, and the Gaussian one
held a verb the report could not say.

## "Use Cavity Eigenmode" as data

That button solves the resonator's own mode and **writes it back** into the waist and offset
boxes, then recomputes. A `ReportAction` could not express it: its `run` returned a status line
and nothing else. `ReportUpdate` is the verb's result as data --

```python
ReportUpdate(status="Cavity eigenmode applied: q=-50+i86.60254 mm, w0=0.12313222 mm, ...",
             controls={"waist": "0.12313222", "offset": "-50"})
```

-- so the arithmetic stays in the model and each toolkit has one job: put these values in those
widgets, then rebuild. **Qt now has the button it never had** (it was on the backlog).
`ReportAction.needs_controls` hands the verb the current control values, which is all the
eigenmode needs (wavelength and M²).

## Measured, and worth knowing

**The box ends up holding what the *builder* echoes back, not the string the verb returned.**
Adopting the values rebuilds the report, and the rebuild re-renders every control from the fresh
report, which formats to 6 significant figures: `0.123132` where the eigenmode said
`0.12313222`. The first guard compared strings and failed on exactly that. The right assertion
is numeric -- the same number, said by the model.

**No layout in the tree is a resonator.** `om05a_folded` gives g = 17.4246, so the verb
correctly writes nothing back and names g. The stable case therefore runs through a stand-in
owner whose `ParaxMatrices` are a two-mirror round trip with d = f = 100 mm (g = −0.5,
w₀ = 0.12313222 mm, q = −50 + i86.6 mm), the same trick 0892 used for the splitter forms. The
rest of that owner -- the wavelength, the default beam, `short_error_message` -- is the real
editor's.

## What stayed

The **Paraxial Calculator** is a form the user solves and applies, and the three solve prompts
(paraxial, folded mirror, best focus) are modal confirmations. Those keep their own pages; only
the two reports moved. `main_paraxial_analysis_dialogs.py`: **672 -> 471 lines**.

One deliberate simplification: the Tk dialog showed the cavity message twice, in an inline label
*and* in the status bar. Only the status line remains, and both toolkits use it.

## Guard

`KrakenOS/UI/validate_open3d_0896_paraxial_reports_on_report_view.py` (penta phase 684):

- **L** -- two `ReportWindow`s, no `Treeview`, and the calculator and solve prompts still there
- **M** -- the matrix window draws the builder's 25x17 grid and exports it under its own keys
- **G** -- the four Gaussian inputs are the builder's own, and typing one rebuilds through it
- **C** -- the verb writes nothing back on a non-resonator and names g; on the stable cavity it
  returns the model's own w₀ and q and the view adopts them and rebuilds
- **Q** -- the Qt dialog offers the same verb and adopts an update the same way
