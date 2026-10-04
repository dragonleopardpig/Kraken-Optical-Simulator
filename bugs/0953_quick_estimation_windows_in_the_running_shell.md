# 0953 -- Quick Estimation's windows open in the running shell

Step 3 of "what is left" in `docs/design_qt_migration.md`, second part. With it, no inspector
window that a Qt user can reach is a Tk window.

## The gap

**Measured before**, in a real Qt shell on om05a_folded:

| Window | Reached from | In Qt before | In Qt now |
|---|---|---|---|
| Target FOV | Set Target FOV, Snap to FOV | Tk window + freeze | a modal row form |
| FOV solve, object plane | double-click the object plane; after a lens swap or an import | Tk window + freeze | a modal row form |
| FOV solve, image plane | double-click the image plane | Tk window + freeze | a modal row form |
| Detector design box | double-click a branch detector | Tk window (unseen) | a row form, not modal |
| Configuration table | Config Table | Tk window (unseen) | the report dialog |

## Change

The Tk windows stay as they are for the Tk app (four ungated validators pin the FOV popup's
source, and each window is placed by hand for Wayland). Each asks `shell_host_of` first.

- **Three row forms** (`row_forms/quick_estimation.py`). Every verb ends in the inspector's own
  solve, with the arguments the Tk buttons pass.
  - *Target FOV*: Width, Height; "Set Target", "Clear (fill sensor)". It waits, as the Tk window
    does: Snap to FOV reads the target straight after it closes.
  - *FOV solve*: Width, Height and where the prefill came from; on a folded scene the fold-leg
    boxes (locked until ticked; a ticked leg greys its sibling); the inspected part drawn at true
    proportions when a device is enabled; "Solve for Thickness", "Solve for Image/Sensor Size".
  - *Detector design*: no fields, only the design block.
- **`FormPanel`** (`row_forms/base.py`): a named block of live controls drawn under a form's
  fields. The FOV form ends in "Design a lens for this field", which is not a field: it has rows of
  its own, a result line and its own Apply. A form names the block and says what it pins.
- **The design block is one Qt widget** (`qt/design_constraints_block.py`), extracted from the 3D
  Live dock, which now uses it too. With a context it leaves out the rows the form pins and names
  them ("From this view: Object FOV (semi) = 28.28"), as the Tk popups do.
- **The configuration table is a report** (`reports/quick_estimation_config.py`). The sweep and
  the cell formats moved there; the Tk window and the shell's report dialog both read them. In Qt
  it gains Export CSV.

## Two things the Qt row-form dialog could not do

1. **A ticked box could not rewrite the form.** Only choices and text fields called `on_change`.
   A box does now, and it keeps what is typed in the other fields first: the refresh that follows
   re-reads every widget from the form, and a width typed just before ticking a leg was put back
   to its old value. The guard's parity claim caught that as Qt sending a different solve than Tk
   for the same input.
2. **A plain form's action read the values the form opened with.** The typed values were copied
   in only for record lists; the Tk view always copies them. Qt does the same now.

Also: an unlabelled line of text now spans the form's width. In the field column the fold-leg
explanation was cut off after two lines.

## Guards

**`validate_qt_quick_estimation_windows` (phase 725)**, on om05a_folded:
- **Q1:** Target FOV is modal and prefilled; two blank boxes are refused; a width of 30 sets the
  target semi-diagonal to 21.21 (sensor aspect); Clear removes it; Snap to FOV runs after the form
  closes, with that target.
- **Q2:** the object form: legs prefilled 9 and 6.85, locked until ticked, a ticked leg greying its
  sibling; the design block's pin follows the typed width; a bad width and an empty ticked leg are
  refused with no solve call; then the solve is called with
  `("object", "thickness", 40, None, (52.5, 1.05), segment=("far", 7.5))`.
- **Q3:** the image form: sensor size prefilled, no design block, the solve called in sensor mode.
- **Q4:** the detector box is not modal, opens in Placement mode, pinned by the image distance.
- **Q5:** the report dialog shows 16 conjugates; the two thicknesses are unchanged by the sweep.
- **N:** no Tk popup, no wait on one.
- **T:** in the Tk app the four still open their own windows and take the typed values.
- **P:** parity. Both shells show the same titles, prefills, leg labels and values, design rows and
  table cells, and send the same arguments to the solve.

**`validate_qt_inspector_popups` (phase 723):** its Tk-only list shrank from 6 to 2 (the 2D bug
flag, and the Tk System Selection window).

**Mutation-checked:**
- Target FOV not waiting: the Qt half fails.
- a leg label reworded in the form only, and the design block pinning nothing: Q2 and P fail.
- actions reading the opening values: Q1, Q2 and P fail.

**Unchanged numbers:** the configuration table's cells equal the old inline computation on three
scenes (om05a_folded, Pyrite 90 0.3X, ELS-85): 16 rows each, identical.

**Other guards run:** 32 Quick Estimation / FOV validators and the 3D Live dock's constraint guard
all pass.

**Seen by eye:** the five windows rendered to PNG.

## Gates

- **Full Tk gate with 0953: 724 of 724 phases pass.** Seven sequential `--phases` chunks on M90aPro
  under the 2.5 GB free-memory watchdog: 1 h 54 min. It also covers 0950, 0951 and 0952, which had
  targeted gates only. Lowest free memory 2.9 GB, in the Qt chunk.

## Left

- A box's `on_change` is honoured by the Qt view only. The Tk row-form view never shows these
  forms (the Tk app has its own windows).
- The 2D bug flag still has no Qt route.
