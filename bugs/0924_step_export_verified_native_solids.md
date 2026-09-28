# 0924 -- the STEP export writes each prism as its native solid, on the body the 3D draws

`validate_five_penta_native_step_export` (ungated) failed in every version. Two of its checks
failed:
- "face count stayed well below faceted fallback": 4979 faces against a 1000 limit;
- "serialized step bodies stayed on traced bodies": `no_roundtrip_body_candidates`.

## Measured

- The exported file is 15 MB, with 189 solids and 4979 faces.
- **Every one of the 189 solids is a 0.5 mm ray-tube segment** (3 faces each). That part is by
  design: 9 envelope rays.
- **No prism is a solid.** Each of the five came out as a `TopoDS_Shell` of **882 loose
  triangles**, although its source `attachment/prisms/42779/step_42779.step` is one clean solid
  with 7 faces.
- The round-trip reader therefore found nothing prism-sized to compare.

## Why

bugs/0300 made every STL-backed optical-solid row export as a faceted shell of its drawn mesh.
The periscope's RA prisms share one STEP *template*, in a different local frame from each
instance's STL, and the template landed ~11 mm off. That fallback is right for 0300, but it hit
every STL-backed row, including ones whose STL is simply a tessellation of their own STEP.

Making the export verify the native solid exposed a second, deeper fault. **The 0300 "drawn
mesh" was not the drawn mesh.**
- `_optical_solid_row_world_step_shell` rebuilt the drawn body as the STL under
  `_row_optical_solid_display_world_transform`.
- Headless, that transform is `TRANS_2A`, whose rotation order differs from the traced mesh's
  for tilted rows (compare bugs/0448).
- The live 3D does not use it for the body. `_iter_3d_optical_surface_meshes` draws a
  file-backed solid from `_runtime_trace_surface_mesh` (`system.EEE`) untouched.

On the cascade:

| row | tilt | traced / drawn body centre | 0300 reconstruction centre | off |
|---|---|---|---|---|
| prism 1 | (-90, 0, 90) | (0, 5.34, 62.84) | (-17.84, 0, 39.66) | 26.7 mm |
| prism 3 | (0, -90, -90) | (145.34, -140, 52.16) | (127.5, -145.34, 75.34) | 26.7 mm |
| prism 4 | (-90, 0, -90) | (140, -145.34, 202.84) | (157.84, -140, 190.34) | 26.3 mm |
| prisms 2, 5 | flat / roll | -- | -- | 0.0 mm |

So a STEP exported without the 3D view open placed the tilted prisms ~26 mm off the body the view
shows. The old round-trip filtered the faceted shells out, so this was never measured.

## Fix (`services/optical_solid_workflow.py`)

- **`_optical_solid_row_world_mesh`** returns the traced mesh the 3D draws
  (`_runtime_trace_surface_mesh`). The STL under the display transform is only the fallback when
  there is no traced mesh. `_optical_solid_row_world_step_shell` builds its shell from it.
- **`_verified_native_row_export_shape`** places the row's native STEP with
  `_row_native_step_alignment_affine`. It keeps that solid **only if** it lies on the drawn mesh:
  - distance is measured point-to-surface (`compute_implicit_distance`) in both directions;
  - the tolerance is max(0.05 mm, 0.2% of the body diagonal);
  - otherwise it returns `None` and the collector writes the faceted drawn mesh, which is 0300's
    shared-template case.

## After

| | before | after |
|---|---|---|
| faces | 4979 | 604 |
| file size | 15 MB | 1.4 MB |
| prisms read back as solids | 0 / 5 | 5 / 5 (p95 <= 0.001 mm to the traced bodies) |

## Guards

- `validate_five_penta_native_step_export`, now penta phase **703**. It runs in its own process
  (bugs/0661). Three checks are new:
  - the export body is the traced mesh the 3D draws, for all 5 prisms;
  - the native solid is **accepted** where it lies on the drawn body;
  - it is **refused** when the drawn body is 11 mm off (0300's miss).
- `validate_open3d_step_export_matches_display` (0300):
  - C1 and C3 were source-text pins of the old call names. They are re-pointed at the new design:
    the drawn traced mesh with the display-transform fallback, and verified-native-else-faceted.
  - Its geometry checks A, B2 and D3 still SKIP, because `attachment/machine_vision_AZ85_RA_Mirror.py`
    is absent. The 0300 scene is therefore not re-measured here. The refusal check above stands
    in for it.
