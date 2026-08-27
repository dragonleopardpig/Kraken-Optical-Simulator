# 0652 — Right-click a component → six-view DXF sheet

**User (2026-08-27):** "OK, is pretty good now. Can we add a right click to components
and export it as a DXF with view in all 6 faces?" (straight after the 0650 round-8
viewport export settled).

## What shipped

`Export Component DXF (6 Views)...` on BOTH element right-click branches (bugs/0619
pattern — the STEP-body menu and the element-row menu, canvas AND Scene Components
tree, via `append_element_context_actions`). One DXF R12 sheet, third-angle layout:

```
            TOP
LEFT  FRONT  RIGHT  BACK
           BOTTOM
```

- `SIX_VIEW_BASES` — six world-axis view frames, every one right-handed toward the
  viewer (`right × up == −direction`); side views share up=+Z, TOP/BOTTOM share
  FRONT's right=+X, so the RAW projected coordinates stay aligned and
  `place_six_views` only shifts columns (x) / rows (y) by one gap — projectional
  alignment like a drafted sheet, not a grid of thumbnails.
- `collect_component_six_view_layers(inspector, step_label=|row_indices=)` — actor
  selection via the 0650 registries (`_actor_step_map`, `_actor_row_map` +
  `_row_actor_map`), companions by the round-7 bounds-containment rule scoped to the
  exported body; rays/axes always excluded. Per view: `mesh_outline_strips` with the
  axis direction (the same silhouette+feature pipeline, incl. the round-6
  perturbation union) then the round-8 decompose/merge/stitch/RDP post-process.
- View captions as centre-aligned R12 TEXT (72=1 + second alignment point) on a new
  `KRAKEN_LABELS` layer; `write_dxf_r12` gained TEXT support.
- Editor dialog `export_component_six_view_dxf` (layout_import_export) — SCREENSHOT_DIR
  default, stem `<layout>_<component>_6views.dxf`; a lens row exports its whole
  `_lens_row_group_for_row` group.

## Verified

- Guard `validate_open3d_0652_component_six_view_dxf` (penta phase 488): frame math,
  third-angle offsets on asymmetric bounds, a REAL vtkCubeSource 10×20×30 through the
  actual collector (per-view extents 10×30 / 20×30 / 10×20, six captions), TEXT
  round-trip, both menu branches + editor method wired. All display-free (pure VTK
  filters, no render window).
- Real scene (Pyrite90 0.3X): camera STEP → 6 views, 17289 polylines; rendered sheet
  eyeballed — aligned rows/columns, closed outlines, captions under each view. Lens
  rows → the surrogate datum discs (circle + line pairs), as those rows really are.

## Scar

The first eyeball render was drawn at 100 dpi with 11 px captions and I misread the
layout as scrambled ("RIGHT above, TOP/BOTTOM overlapping"). The DXF's own caption
coordinates disproved it in one print. Cheap lesson: when a render contradicts the
data, print the data before touching the code.
