# 0663 — Inspection Cell: six station layouts composed around one 3D part (phase 2)

**User (2026-08-27 → 08-30):** six cameras inspecting a rectangular part's six faces;
"blow out 6 optical axis for user to place lens and cameras"; "after done, start
Phase 2".

## Design (docs/inspection_cell_multi_station.md)

The row chain stays ONE imaging chain. A cell = the 0661 part (box centred at the
cell origin) + up to six STATION LAYOUTS (one per face), each designed as an ordinary
layout with the part enabled on that face. The cell loads every station HEADLESS
(a KrakenLayoutEditor with no embedded inspector — the one thing that can exist N
times), traces it independently, and places its actors under the rigid transform
carrying its object plane onto its face: object point → face centre, object axis →
outward normal, field-width direction → face width (`station_frame_transform`). The
two-arm precedent (per-arm sequential traces + display transforms), generalised.

## Shipped (v1) — `KrakenOS/UI/services/inspection_cell.py`

- **Cell file** `*.cell.json`: part spec + `stations: {face: {layout, enabled}}`.
- **Cell View**: one pyvista scene — part box + six blow-out axes + every station's
  bodies/rays via the legacy scene populator with a per-station `SetUserMatrix`.
  (Opens a pyvista window from the dialog; headless off-screen for guards.)
- **Cell STEP**: each station's NATIVE STEP export (analytic optics + CAD bodies +
  ray tubes) written to a temp file, read back, transformed with `_shape_with_affine`,
  merged into one compound with the part box.
- **Interference report**: pairwise overlap of station body boxes (mm).
- **Dialog**: Actions → *Inspection Cell (6 stations)…* — part W×H×D, six face slots
  (Browse), Open Cell View / Interference Report / Export Cell STEP / Save / Load.

Headless-station scar: the legacy populator reads inspector-owned Tk vars
(`show_terminal_diagnostics_var`) through the editor; `load_station` seeds them
(checked through `__dict__`, the 0594 Tk `__getattr__` recursion trap).

## Verified

Two real stations (Basler_Telecentric on Front, Pyrite90 on Top): 98 + 197 actors,
both object planes on their face centres to 0.00e+00 mm, screenshot eyeballed (part
at the origin, front station along +z, top station along +y), interference report
flags the expected front×top body overlap on a 60×40×20 part, cell STEP 29 MB with
sensible bounds. Guard `validate_open3d_0663_inspection_cell` (penta phase 496).

## Phase 3 (open)

Cell-level solve (calculator per face pre-filling stations); STEP part import
(non-box parts, picked planar regions); shared illumination across faces; an
embedded (Tk) cell view instead of the pyvista window; double-click a station to
open its editor.
