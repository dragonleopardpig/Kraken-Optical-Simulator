# 0650 — Export the current 3D viewport as a DXF R12 vector drawing (FEATURE)

**User:** "The software can now output to STEP file, can you also add output to DXF or
DWG file? Output from the current viewport." DWG is a closed binary with no in-process
writer (the repo's in-process-libs rule); DXF R12 ASCII opens in every CAD package
(AutoCAD/FreeCAD/LibreCAD) and converts to DWG there losslessly — so the exporter
writes R12 by hand, zero new dependencies (`KrakenOS/UI/services/dxf_viewport_export.py`).

**What it does:** flattens the scene orthographically into the CURRENT camera's view
plane in TRUE millimetres (perspective deliberately not applied — CAD wants true
lengths). Layers: `KRAKEN_RAYS` (per-actor colour), `KRAKEN_AXES` (one continuous line
per axis from the MODEL records, DASHED by linetype), `KRAKEN_BODIES` (view-direction
silhouettes + feature/boundary edges), `KRAKEN_MEASURES`, `KRAKEN_OVERLAYS`.
Menus: 3D window "Export View DXF" (next to Export STEP) + File → "Export 3D View
DXF...". Guard = `validate_open3d_0650_dxf_viewport_export`, penta **phase 487**.

## Three user review rounds, all folded in (the release-quality history)

1. **"the output lens only have horizontal lines, missing those vertical and slanted
   lines of the housing"** — the first cut exported mesh actors' stray tessellation
   LINE cells (61k horizontal segments on the user's Pyrite90 file) and never computed
   silhouettes. A turned housing's slanted/vertical profile in a side view IS its
   silhouette (view-dependent contour, not a crease). Fix: meshes export
   `vtkPolyDataSilhouette` (camera direction) + `vtkFeatureEdges`, never their raw line
   cells; ray classification consults BOTH registries (`_actor_ray_map` +
   `_ray_actor_map`) plus a many-segment heuristic for illumination bundles
   (73k polylines had landed unclassified in OVERLAYS).
2. **"many lines where each of them are assembled of many short line segments ... a
   line should be one vector line"** — FeatureEdges/Silhouette emit per-edge 2-point
   cells. Fix: endpoint stitching into maximal chains + Ramer-Douglas-Peucker
   (0.02 mm) so collinear runs collapse to single vectors while real bends survive;
   dashed axes export as ONE continuous model polyline (the layer linetype dashes it).
3. **"some boxes not closed, missing lines at one side, not symmetry"** — three
   post-processing defects: (a) one non-finite vertex killed a WHOLE stitched chain at
   the writer's finite gate (split into finite runs instead); (b) the stitcher's
   quantised-bin endpoint lookup missed joins straddling a bin edge — a float lottery
   that broke symmetric parts asymmetrically (3×3 neighbour-bin lookup); (c) the same
   edge from silhouette+feature passes stitched into a doubled back-and-forth line
   (direction-invariant fragment dedupe BEFORE stitching).

Guard F pins the round-3 contracts numerically: a 4-fragment box closes into one
5-point chain, bin-edge joins hold, poisoned vertices split not kill, duplicates
collapse, bends survive RDP.

4. **"check attachment/DXF.png, still have some open sides"** — per-prop diagnosis
   (diag v2, GetViewProps with class names + registry membership) found two more:
   (a) every STEP body draws a COMPANION edges actor (pre-extracted CAD feature edges,
   lines-only, unregistered — 6.9k/30k segments on this scene) that carried the body's
   own crease work but the many-segment heuristic misfiled into RAYS; the scene dict's
   `cad_step_actors` (label → [("mesh"|"edges", actor)]) now classifies BOTH kinds into
   BODIES; (b) the walk used `renderer.GetActors()`, which excludes assemblies and
   non-vtkActor prop classes — now `GetViewProps()` with `GetParts()` descent.
   Verified visually: the exported DXF re-rendered to PNG shows fully closed camera and
   lens boxes with both verticals (scratchpad pyrite90_zoom.png vs the user's DXF.png).
   Investigation scars: a long-running per-actor silhouette A/B (vtkCleanPolyData)
   DISPROVED the unshared-topology theory for the big bodies (dup=0, silhouettes
   identical) — the small row discs alone benefit from cleaning; and "how long to go"
   was a STUCK MONITOR, not a stuck job — check the worker's CPU% before believing a
   wait loop.
