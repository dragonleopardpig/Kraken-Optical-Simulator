# Kraken UI Layout Editor Refactor Plan

Status: Active. The file `KrakenOS/UI/layout_editor.py` is currently over
53,000 lines, so continued feature work should avoid adding more unrelated
logic to the monolith.

## Why Split It

The editor now owns too many responsibilities:

- Tk layout construction and event wiring;
- editable surface table state;
- common layout/example loading;
- source/object/scene-source controls;
- 2D rendering orchestration;
- embedded 3D inspector and CAD/STL handlers;
- analysis calculations and export state;
- optimization and tolerance workflows;
- case-study/demo helpers and compatibility wrappers.

This makes small changes harder to review and increases the risk that a UI
edit accidentally changes ray tracing, analysis, or CAD behavior.

## Refactor Rules

1. Preserve user-facing behavior in each slice.
2. Extract pure services before splitting Tk widgets.
3. Give every extraction a small validator before moving to the next one.
4. Keep `KrakenLayoutEditor` as the compatibility facade until enough modules
   are stable.
5. Do not mix cosmetic UI theming with structural refactors.

## Proposed Module Boundaries

| Area | Target module | First extraction |
| --- | --- | --- |
| Layout/example loading | `KrakenOS/UI/layout_library.py` | title/category discovery, menu filtering, Python layout loading |
| Surface table model | `KrakenOS/UI/surface_table_model.py` | row serialization, special row normalization, row validation summaries |
| 2D plot orchestration | `KrakenOS/UI/layout_plot_controller.py` | refresh signatures, scene projection filters, plot status labels |
| Analysis mode dispatch | `KrakenOS/UI/analysis_controller.py` | mode-to-render dispatch and export-state reset |
| Wavefront/Zernike services | `KrakenOS/UI/wavefront_analysis.py` | pupil sampling, wavefront export rows, Zernike fit rows |
| Optimization UI state | `KrakenOS/UI/optimization_panel_state.py` | operand variable maps, selected operand serialization |
| 3D inspector UI | `KrakenOS/UI/inspector3d.py` | move `Kraken3DInspector` after CAD metadata helpers are stable |
| Dialogs and context menus | `KrakenOS/UI/dialogs/` | large standalone dialogs with minimal editor callbacks |

## Suggested Next Slice

The first slice has started with `KrakenOS/UI/layout_library.py`, covering
title/category discovery, menu filtering, Python layout loading, and Zemax
attachment discovery. `KrakenOS/UI/validate_layout_library.py` validates this
without constructing a Tk window.

The next slice should extract row serialization and table-safe row
normalization into `surface_table_model.py`. This slice now includes the
`SurfaceRow` dataclass, row cloning, endpoint normalization, serializable row
specs, surface-row clipboard payload helpers, component-row extraction,
append/insert row helpers, duplicate-row helpers, and paste filtering.
`KrakenOS/UI/layout_editor.py` still re-exports `SurfaceRow` for existing
imports.

The next row-model slice should move pure table display formatting helpers, or
pause row-model extraction and start the next proposed boundary:
`layout_plot_controller.py`.

## Stop Condition For Each Slice

- `python -m KrakenOS.UI.validate_menu_smoke` still passes.
- The relevant case-study validators still pass.
- The extracted module has at least one direct validator that does not require
  a live Tk window.
