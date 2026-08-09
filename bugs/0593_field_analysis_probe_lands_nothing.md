# 0593 — the field-aberration overlays draw nothing, and only numpy said so (PARTIALLY FIXED)

Flag `flag_20260809_094851_598`: *"Normal to sensor works but none of the actual analysis overlay
works."* Then, separately, the user noticed these in the app's terminal:

```
numpy/_core/fromnumeric.py:3824: RuntimeWarning: Mean of empty slice
numpy/_core/_methods.py:142:    RuntimeWarning: invalid value encountered in scalar divide
```

They are the same defect. The warnings were the ONLY evidence the analysis suite was failing.

## Reproduced

On `machine_vision_Apo75.py` (0433-frozen, folded: BS +Z→+X, RA prism +X→−Z), exercising every
analysis overlay:

| overlay | result |
|---|---|
| `best_focus_surface_overlay_spec` | **None** |
| `distortion_grid_overlay_spec` | **None** |
| `astigmatism_surfaces_overlay_spec` | **None** |
| `illumination_marker_rays_overlay_spec` | None (no markers on this scene — expected) |
| `source_illumination_overlay_spec` | dict ✅ (fixed by bugs/0592) |
| `receiving_cone_overlay_spec` | dict ✅ |
| `source_illumination_rays_overlay_spec` | dict ✅ |

`spot_field_map_overlay_spec` and `pixel_grid_overlay_spec` call the same sampler per field
(`three_d_scene_tools.py:4847`) and are a fourth and fifth casualty — the table above understates
the blast radius.

Warning provenance, 54 occurrences of each of 6 sites (54 field points × 3 means × 2 warnings):

```
KrakenOS/PupilTool.py:271/272/276   RMS_Pupil
  ← KrakenOS/PupilTool.py:572        __init__
  ← KrakenOS/UI/services/geometric_analysis.py:611  _build_geometric_image_samples_full
  ← KrakenOS/UI/services/analysis_plot.py:234       _sample
```

## Root cause

`RMS_Pupil` traces a small set of probe rays and then does `(X, Y, Z, L, M, N) = RP.pick(Surf)`.
On this scene **the pick comes back EMPTY** — the probe rays never reach the target surface — so
`np.mean(X)` warns and yields `NaN`, `R_RMS` is `NaN`, and every overlay built from those samples
silently becomes "no spec".

`Kos.PupilCalc` drives a **sequential** pupil probe through a scene whose rows carry baked WORLD
placement. Verified on the flagged scene — rows 1,2,3,4,5,7,8 are world-placed, and the beam does
not run in row order:

```
#  name                             thickness   world_center
0  Object at 1X                      118.9700   [   0.000  0.000    0.000]
1  Front Optical Vertex Datum          1.4839   [  82.039 -0.000   54.283]
5  Rear Optical Vertex Datum          83.3811   [ 132.043 -0.000   54.283]
6  Promoted OPTICAL STEP (splitter)    0.0000   [  -0.122  0.000   54.459]   <-- physically FIRST
7  Promoted OPTICAL STEP (RA prism)   72.5194   [ 179.788  0.000   54.321]
8  Image / Sensor at 1X                0.0000   [ 179.788 -0.000   -3.349]
```

The beam is object → **splitter** (+Z, fold to +X) → lens → RA prism → sensor. The splitter is
row 6 but sits at world x = −0.122, *before* the lens at x = 82…132. A sequential probe walked in
row order jumps 132 mm backwards and then 180 mm forwards, reaches no stop, and returns nothing.

## Done here

1. `RMS_Pupil` detects the empty pick and returns `NaN` quietly, restoring system state
   (`SurfFlat`, `TargSurf`, `Vignetting`, `RP.clean()`) on the way out. The 216 warnings → zero.
2. **The failure is now VISIBLE.** `_build_geometric_image_samples_full` wraps the `PupilCalc`
   construction and re-raises with `_pupil_probe_failure_reason`, which names the world-placed
   rows. The user now reads, instead of a blank canvas:

   > Best-focus surface: field-curvature scan failed: the sequential pupil probe cannot run on
   > this scene: rows [1, 2, 3, 4, 5, 7, 8] carry baked WORLD placement (a folded / frozen
   > layout), so the probe reaches no aperture stop and returns no rays. The field-aberration
   > analysis needs a world-order instrument here (bugs/0593). [index 0 is out of bounds …]

   The three inspector overlays also log which overlay stayed dark, and the sampler counts and
   reports starved field samples. All three messages were confirmed firing on the flagged scene —
   bugs/0593's earlier visibility attempt was reverted precisely because it could not fire.

**The overlays still return None on a folded scene.** The measurement instrument is still missing.

## Rejected: substituting `_folded_optical_solid_straight_equivalent_rows()`

The obvious fix — measure on the straight equivalent, since a fold is a rigid transform that
changes no aberration — was built, measured, and **rejected**. Recording it so it is not rebuilt.

The invariance argument itself is sound. All three overlays consume only `focus` (referenced to
the on-axis focus, i.e. a difference), `image_height` (transverse, renormalized to the drawn image
circle) and `distortion` (a ratio); and all three take their *placement* from the world scene
bundle (`center_world`/`normal_world`/`tangent_world`), never from the measurement frame. Wired up,
it worked in the narrow sense: all three specs became non-None, the bowl landed **0.0000 mm** from
the world anchor, and numpy warnings stayed at zero.

It is still the wrong instrument, because `_folded_optical_solid_straight_equivalent_rows()` takes
its axial chain from `row.thickness` **in row order**, and on this scene that is a different
machine, not a different frame:

* sum of thicknesses **324.87 mm** vs sum of world centre-to-centre legs **518.12 mm**;
* object leg 118.970 prescribed vs 136.376 in world (+17.41); image leg 155.900 vs 105.416 (−50.48);
* the frozen image-side gaps run backwards (`world leg = const − thickness`, bugs/0478): 
  83.3811 + 47.7842 = 131.17 and 72.5194 + 57.6317 = 130.15;
* row order ≠ beam order (the splitter, above).

Field curvature, astigmatic separation and distortion are all **conjugate-dependent**, so this
would report the aberration field of a system imaging at a materially different magnification —
replacing "nothing drawn" with "something plausible drawn that is wrong". That is bugs/0576 one
layer out. The measured result was in fact *identically* zero (focus span 1e-14, distortion
0.0000%) because the flattening also renders both promoted solids optically inert — a flat bowl
for a machine that is not the user's.

## Open — what the real fix needs

1. **Replace the LAUNCH, keep the trace and the pick.** The trace already runs on the real solids,
   and `_pick_image_plane_data_static` already picks in the sensor's LOCAL frame
   (`rays.pick(-1, coordinates="local")`, `layout_editor.py:2255`) — which is exactly the frame the
   three overlays want, so the measurement is fold-invariant *the moment rays land*. Only the
   sequential launch is broken. Give the analysis sampler the PupilCalc-free geometric fallback the
   2D preview already has (`trace_preview.py:810-817`, finite branch at `:896-931`).
2. **Aim it with WORLD geometry, walked in BEAM order** — consecutive `_split_row_world_center`
   distances along the traced path — not `row.thickness` in row order. That is a genuine rigid
   unfold and is defensible; today's straight equivalent is not.
3. **The field axis is station-frame too.** `_current_field_height` converts through
   `_current_object_distance`, a sum of thicknesses (`paraxial_tools.py:634-656`), and the drawn
   rim `field_image_radius` rides the same first order. On a frozen scene both must come from world
   geometry or the swept grid and the rim describe the prescription, not the scene.
4. **Guard the invariance claim, not just the presence of a spec.** On a tracked folded scene
   assert (a) the specs are non-None, (b) `ring_dz` / `max_astigmatism_mm` agree with the same
   optical system authored straight — the frame-invariance claim itself, tested — (c) the drawn
   centre/normal match the traced detector, and (d) the negative: `sum(world legs) != sum(thicknesses)`,
   so the straight equivalent can never quietly become the instrument again. Use a tracked layout
   (`machine_vision_AZ85_RA_Mirror.py` is the only tracked promoted-mirror fold) rather than a
   gitignored `attachment/` scene, so the phase cannot silently SKIP the way
   `validate_open3d_analysis_overlays_reached_image_branch` does today.

## Note — a pre-existing, unrelated failure

`validate_open3d_analysis_overlays_reached_image_branch` fails at HEAD (`REAL: expected one usable
reached-image branch, found 0`), verified identical with these changes stashed. Not caused here.
