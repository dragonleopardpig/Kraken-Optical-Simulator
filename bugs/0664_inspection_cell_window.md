# 0664 — Embedded Inspection Cell view (phase 3)

**User (2026-08-30):** "proceed" on the phase-3 recommendation — the cell inside the
main application instead of a pyvista pop-up, double-click a station to edit it, the
cell re-composing on save.

## Shipped — `KrakenOS/UI/panels/inspection_cell_window.py`

`InspectionCellWindow(tk.Toplevel)`: a VTK render widget embedded the same way the
main 3D inspector embeds its own (`_prepare_vtk_tk_widget` + `vtkTkRenderWindowInteractor`
+ `vtkRenderer`, trackball camera). It never renders through pyvista: it runs the
phase-2 composition OFF-SCREEN and **transplants the actors** into its own renderer
(the vtkActors are plain VTK objects; the previous off-screen plotter is closed once
its actors have been replaced). `compose_cell_plotter` now records
`station_actor_keys` per face so the window maps every actor → station.

- **Double-click a station** (VTK `GetRepeatCount()` ≥ 1 on the left button, prop
  pick) → `open_station(face)` loads that station's layout into the main editor and
  raises it.
- **Re-compose on save**: the window polls the enabled station layouts' mtimes every
  2 s (`check_station_files`) and re-composes when one changed — no coupling into the
  editor's save paths, and it also catches edits made in another KrakenOS instance.
- Toolbar: Recompose, Fit view, Export Cell STEP, Close; the interference/summary
  line at the bottom. The dialog's *Open Cell View* now opens this window; the
  pyvista window remains the fallback when VTK/Tk is unavailable.
- Teardown finalizes the VTK render window before the Tk widget (VTK's
  "TkRenderWidget destroyed before its vtkRenderWindow" warning otherwise).

## Verified

Demo cell (six telecentric stations): window available, 1165 props transplanted, all
six faces in the double-click map, `open_station("front")` loads
`telecentric_front.py`, screenshot eyeballed. Guard
`validate_open3d_0664_inspection_cell_window` (penta phase 497): renderer holds the
composition, faces reachable, a prop pick at a projected face centre resolves,
open_station loads the layout, touching a station file re-composes. The window
section runs standalone (the harness owns the single embedded inspector).

## Open (phase 3, remaining)

Cell-level solve (calculator per face pre-filling stations); STEP part import for
non-box parts; shared illumination across faces; station labels in the view.
