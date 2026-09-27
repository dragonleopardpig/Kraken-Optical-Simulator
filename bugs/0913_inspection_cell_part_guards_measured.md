# 0913 -- five inspection cell/part phases failed on moved code (497, 498, 499, 551, 607)

bugs/0882 and 0883 ported the Inspection Part and Inspection Cell dialogs to row forms
(`row_forms/inspection_part.py`, `row_forms/inspection_cell.py`). Their guards kept searching the
Tk shims' source. Every claim still held. The checks now build the REAL forms with a bare stand-in
owner and measure:

| Phase | Check | Now measured |
|---|---|---|
| 497 | B1 | The cell dialog opens the EMBEDDED view: the form's own "Open Cell View" action runs with the embedded opener recorded. It is called once and, with no window back, reports the pyvista fallback. |
| 498 | D1 | The cell dialog carries the solve section: the "Solve & Build Stations" action plus the defect / px / WD / output fields. The old check also depended on the lowercase label "build". |
| 499 | C2, C3 | Both dialogs offer the STEP: a "Part STEP (optional)" field AND a "Browse Part STEP..." action. |
| 551 | E5, E6 | Length, Width, Thickness in that field order. Values typed per label land in `width_mm`, `depth_mm`, `height_mm` (bugs/0766). |
| 607 | G1 | The form's FormPreview draws 6 face polygons, and its caption is the derivation chain. |
| 607 | G2, G2b, G3 | No face-choosing field; the FORM module records bugs/0768; the shared renderer wraps the caption. |

No product change.
