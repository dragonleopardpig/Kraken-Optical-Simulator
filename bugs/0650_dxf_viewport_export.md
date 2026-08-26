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

5. **"refer to attachment/freecad.png ... some right side open ended"** (rounds 5+6) —
   the user's symmetry framing cracked it. Quantified: 1583 left-side body segments had
   no right twin vs 197 the other way. Two causes, one dead end:
   - DEAD END (kept as a code comment): classifying `_actor_step_follow_map` keys into
     BODIES swallowed ~1100 ILLUMINATION-RAY polylines (they follow their LED via the
     same map). The correct discriminator is ROW TRACKING: CAD edge/rim companions
     register with `track_row_index` → `_row_actor_map` (row → [keys]; NOT the
     key→row `_actor_row_map` — a naming trap), illumination bundles are follow-only.
   - THE ASYMMETRY ITSELF: `vtkPolyDataSilhouette`'s facing-flip test is a knife-edge
     at tangency, and OCC tessellation is not mirror-symmetric — contour steps on one
     side of a body of revolution fall exactly on the threshold and vanish while their
     mirror twins survive. Fix: UNION the silhouettes of three slightly perturbed view
     directions (±~0.6°); the fragment dedupe absorbs the overlap.
   Verified: the tight lens zoom renders fully symmetric (ring steps, flange chamfers,
   neck pillars, closed boxes on BOTH sides — scratchpad round6_lens_tight.png vs the
   user's freecad.png). A left/right mirror-twin metric was built
   (scratchpad symmetry_check.py) but over-counts on stitched+RDP output (symmetric
   curves keep different points) — the rendered eyeball is the arbiter.

6. **"many of them consist of black segment line joining the green ... the camera, first
   line from the bottom seems broken"** (round 7, lens.png / camera.png) — measured on the
   user's 20:19 export: the RAYS layer held 1120 polylines ALL of ACI 94 (dark green) —
   the STEP bodies' companion edge actors. They have NO row (`_add_mesh_actor(...,
   follow_step_label=...)`, follow-only), so the round-6 row-tracked keys never covered
   them, and the ≥20-segment heuristic filed them as rays. The "broken" camera bottom
   edge was not a gap: at y −40 it was NINE overlapping collinear pieces on two layers
   (green companion copy 54.6→58.1→63.1→82.1 + black silhouette copy 58.1→59.4→62.7,
   63.1→82.1), each copy cut wherever the lower plate touches it — endpoint stitching
   can only join shared endpoints, it cannot see overlap. Two general fixes:
   - CLASSIFY BY CONTAINMENT: a lines-only, unregistered actor whose bounds sit inside a
     STEP body's bounds (+2 mm) is that body's edge work → BODIES (`_inside_step_body`).
     Illumination rays leave their LED's bounds, so the follow-map trap does not recur.
   - MERGE COLLINEAR OVERLAP before the stitch: `merge_collinear_segments_2d` groups
     2-point fragments by (direction, perpendicular offset) with a SORT-based sweep (no
     bin lottery) and unions the parameter intervals (angle 2e-4 rad, perp 0.03 mm,
     gap 0.05 mm); chains of 3+ points pass through untouched; zero-length runs drop.
   Measured after: RAYS = 640 polylines, colours {4,3,30,8,1,2} — zero ACI 94; BODIES
   3225 → 2054 polylines; the camera bottom edge + both chamfers = ONE 4-point polyline
   (guard section G reproduces the nine pieces verbatim). Renders: scratchpad
   r7_zoom_lens.png / r7_zoom_camera.png — every housing line black and continuous.
   Side find while the baseline re-cut ran: phase 452 (guard 0594) flipped PASS→FAIL
   with no code change — its fixture hard-coded a thickness (125.5793 mm) that only
   collided on the pre-0647 ELS85 numbers; the fixture now CONSTRUCTS the collision
   from the live geometry (sensor position is linear in the booked thickness on a frozen
   fold — two samples, solve for the solid's centre). Baseline: 487 phases, 46 known
   environment failures, 452 restored to pass.
