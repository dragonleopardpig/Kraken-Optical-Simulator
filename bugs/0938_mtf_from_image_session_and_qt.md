# 0938 -- "Measure MTF from Image" as one session, rendered in Tk and in Qt (phase 5g complete)

The dialog (bugs/0411, 0415) was a single 370-line Tk function, with its state in a closure dict.

## The split

| Module | What it owns |
|---|---|
| `mtf_from_image_session.py` (`MtfFromImageSession`) | the image and its display scale, the mode (slanted edge / USAF three-bar), the next-ROI fields, the calibration, the ROIs in ORIGINAL image pixels, the fits (`compute`), the plot (`draw`, with `style_mtf_axes`), the CSV, the enlarge-in-viewer, and the instruction / status lines |
| `panels/mtf_from_image_dialog.py` (`TkMtfFromImageView`) | the Tk layout; the canvas drag -> `add_roi_display` |
| `qt/dialogs/mtf_from_image_dialog.py` (`MtfFromImageDialog`) | the Qt layout: an image widget that draws the boxes and the rubber band, the ROI table, the calibration, and a Qt matplotlib canvas (click to enlarge) |

The Qt dialog is reached three ways:
- File -> Measure MTF from Image...;
- the ribbon's Analysis -> Measure group;
- the editor's own `open_mtf_from_image_dialog`, which now hands off through
  `show_mtf_from_image_dialog` when a shell installs it.

## Proof that nothing changed

A widget script drove the OLD dialog (HEAD) and the NEW one through the same steps on synthetic
captures (a 5° slanted edge, two three-bar elements):
- load;
- a too-small box;
- the edge box and Compute, without and with pixel pitch;
- Save CSV;
- USAF mode and two element boxes;
- Compute, Save, Delete, Clear.

Status lines, ROI tables, fitted values ("Edge MTF: angle 5.0°, MTF50 0.093 cyc/px (26.8 lp/mm)",
USAF 0.168 / 0.157) and both CSV files were **identical**; the CSVs were compared byte for byte.

One deliberate difference: after Clear All or a mode switch, the old dialog kept showing the
previous curve after discarding its result. Save CSV then said "Compute the MTF before saving."
while a curve was on screen. The plot now follows the result, so what is shown is what would be
saved.

## Guard

`validate_qt_mtf_from_image`, penta phase **716**:
- **O**: the File action opens the Qt dialog, and the ribbon carries it.
- **E**: a real drag on a 1320×1120 capture shown at 0.5× stores the box at twice the size in image
  pixels. Compute equals a direct `measure_slanted_edge_mtf` on that box; the edge angle is 5.00°.
  The capture is deliberately larger than the display: on an image shown 1:1, a view that skipped
  the scale would still pass.
- **U**: two USAF drags add G2E1 then G2E2, the element field advancing by itself; Compute fills
  each box's MTF and R².
- **T**: the Tk dialog's same drags store the same ROIs, and the two shells save byte-identical edge
  and USAF CSVs.

Phases 335 / 338 pinned the old function's source text; they are re-pointed to the view + session
and pass. Phase 714 (the ribbon) now covers 42 actions + Quit.
