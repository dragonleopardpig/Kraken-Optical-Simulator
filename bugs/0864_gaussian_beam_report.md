# 0864 -- the Gaussian Beam Report, in both toolkits

The first report with **inputs**: wavelength, waist radius, waist offset and M2.

## What moved

`KrakenOS/UI/reports/gaussian_beam.py` now owns the propagation (`Kos.propagate_gaussian_beam`
over `system.ParaxMatrices`), the 20 columns, the infinity-aware formatter a beam trace needs
(`inf` / `-inf` / `-` for a collimated waist), the summary line, the defaults, and
`gaussian_cavity_eigenmode` -- the model side of the dialog's "Use Cavity Eigenmode" button.

The Tk dialog was **rewired onto it** (like 0859's paraxial matrix, whose data also lived inside
the dialog): its `recompute()` now calls the builder and inserts `report.cell(...)`, its export
calls `report.write_csv`, and its cavity button calls the shared helper. The Qt dialog renders the
same builder.

The four inputs are `ReportValue` controls -- the second control kind after 0863's `ReportChoice`.
A value control is a line edit that rebuilds **on commit**, not per keystroke, and the BUILDER
parses the text: a value that is not a number falls back to the default rather than raising, so a
half-typed field never breaks the dialog.

Defaults come from the model: the scene's own Gaussian source beam when it has one, else a 1 mm
unit beam at the current wavelength.

Not in the Qt dialog yet: the **Use Cavity Eigenmode** button. Its model side is shared and
tested; only the Qt control is missing.

## Guard

`validate_open3d_0864_gaussian_beam_report.py`, penta phase 643. D the defaults are the model's,
over 50 propagation steps. B a non-numeric input falls back instead of raising. E the cavity
helper answers from the model (this scene is not a resonator: stable=False, g=17.4246). T the
REAL Tk dialog's table equals the builder's cells. Q the Qt dialog's table equals them too --
**the same SHA-256 over all 50 x 20 cells in both toolkits**. V typing waist=2.5 rebuilds the
table to the builder's own report for that value, and the summary follows (final w 35.1 -> 87.8
mm).
