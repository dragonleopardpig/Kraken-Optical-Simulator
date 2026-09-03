# 0716 — "LENS-10F238 looks different to freecad.png" + "thoroughly fix STEP importing"

(flag_20260904_074059 + user directive)

## Root cause

The vendor assembly mixes 25 SOLID breps with 10 SHELL-BASED components (a
knurled focus ring and housing parts are modelled as open shells, not
solids). `load_step_analytic_document` enumerated faces PER SOLID —
`solid_sources = solids if solids else [shape]` — so whenever any solid
existed, every free shell was dropped. The drawn lens showed two separated
groups with a hole where the shell parts belong (327 faces' worth);
FreeCAD, which draws all products, showed the full lens. (Not a reader
problem: both the simple and XDE OCC readers compose the assembly
identically — the loss was our face enumeration.)

## Fix

- Free shells (shells not owned by any solid, mapped via `topexp.MapShapes`)
  join the face-source list after the solids; each gets its own S-index, so
  face ids, mesh tagging and metadata flow unchanged. Shells-only files keep
  prefixed ids (no collisions).
- Cache versions bumped (`analytic doc v1→v2`, `analytic mesh v2→v3`): the
  same input file now yields more geometry, so every stale cache regenerates
  on first touch (a one-time rebuild per STEP).

Measured on 10F238: 33,579 → 49,961 mesh points; the render now matches
FreeCAD (both knurled rings, continuous body, no floating screw).

## Thorough-fix audit (the directive)

- 0715: whole-assembly import default (largest-component amputation closed).
- 0716: free-shell inclusion (this fix).
- Bounds/barrel/glass measures explore TopAbs_FACE on the composed shape —
  they always saw shell faces; unaffected.
- Promotion/tracing require closed solids by design; shells are decoration.

## Guard

`validate_open3d_0716_step_shell_import` = penta phase 515 (A1/A2 source
pins, B cache versions, C real-file gap-face census, skip-if-absent).
Regression: 0702 (10 checks), import-service, 0668 — all green.
