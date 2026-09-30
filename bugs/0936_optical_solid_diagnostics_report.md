# 0936 -- "Inspect Optical CAD/STL Solids" as one report; the dead numeric placement assistant removed (phase 5g)

`panels/main_optical_solid_dialogs.py` (273 lines) held two Tk dialogs.

## The diagnostics: a `Report`

The Tk dialog was a text box filled inside its method. The text is now built by
`reports/optical_solid_diagnostics.py`:
- **One record per solid**: row, name, READY/CHECK, triangles, open edges, non-manifold edges,
  winding, mesh file.
- **Detail pane**: each solid's full diagnostics text, the same `format_stl_mesh_diagnostics`
  output plus the original CAD source line.
- **Copy**: the whole text.

Both shells render it:
- **Tk**: `ReportWindow`. An empty layout still says "No rows contain Solid_3d_stl." as
  information, not as a failure.
- **Qt**: Analysis -> Inspect Optical CAD/STL Solids, also on the ribbon under Scene -> CAD with
  its own icon.

The table's Status is the text's own rule (`is_trace_ready`), so the table and the detail cannot
disagree.

## The numeric Place/Orient assistant: removed, not ported

`_open_optical_stl_numeric_placement_assistant` had **no caller**. Its one call was replaced on
2026-05-04 (a53b72a3, "Move STL placement into 3D inspector") by the 3D inspector's placement
handler, which 0925 already brought to Qt (`row_forms/stl_placement.py`). A contract check kept
pinning the dead method's source. The method, its service pass-through and the dialog class's
`short_error_message` / `axis_to_layout_z_tilts` arguments, used only by it, are gone. The
contract now asserts that the editor has NO such method.

## Guard

`validate_optical_solid_diagnostics`, penta phase **715**. It uses the Edmund 42779 prism layout
plus two added rows.
- **D**:
  - the prism reads READY: 16 triangles, 0 open edges, and its detail is exactly its own mesh
    text + "Original CAD source (STEP)";
  - the same mesh with one triangle cut out reads CHECK: 15 triangles, 3 open edges;
  - an in-memory `Solid_3d_stl` object reads CHECK;
  - a layout with no solids refuses with "No rows contain Solid_3d_stl.".
- **K**: the Tk command opens a report window whose rows are S1, S2, S3.
- **Q**: the Qt action opens the report with the same rows; selecting S2 shows "S2: Torn prism";
  the action is on the ribbon.

The ribbon guard (714) now counts 41 actions on the ribbon + Quit excluded, with all 42 icons
distinct.
- **Full gate OWED:** committed on the subset (655, 707, 713, 714, 715 pass); the full run was stopped when the user had to leave. Run `tools/penta_shard_gate.py` first next session.
