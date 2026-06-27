# 0171 — pupil first-order reference crashes on a promoted-solid / beam-splitter scene (int EEE)

## Symptom (user log, machine_vision_150mm_measured_test + glued beam-splitter cube)

Spammed on every preview/analysis refresh:

```
[pupil] reference launch failed, geometric fallback:
    MeshRayTraceError('non-sequential surface 1: int has no ray_trace or extract_surface method.')
3D source envelope: splitter/branch paths detected; kept full 117-ray launch bundle ...
```

and the **"Best image solve" (Solve Best Focus) failed** on the Lens Rear Datum gap in
that beam-splitter scene.

## Root cause

`KrakenSys` builds the per-surface mesh array `EEE` two ways
(`KrakenOS/Prerequisites3D.py`): `BUILD == 1` → `Prerequisites3DSolids` (real PyVista
meshes); else `Prerequisites3DSolidsDummy`, which sets `lens = 0` and
`self.EEE.append(lens)` for **every** surface — so `EEE = [0, 0, …]`, the main entries are
the int `0`. A non-sequential trace then calls
`trace_mesh_ray(self.EEE[jj], …)` (`KrakenOS/InterNormalCalc.py:411`) →
`raytrace_compatible_mesh` (`KrakenOS/MeshRayTrace.py:560`) → `MeshRayTraceError('… int has
no ray_trace …')`.

The per-branch first-order **pupil reference** (`_pupil_model_inputs`,
`KrakenOS/UI/services/analysis_compute_workflow.py`) built its reference system with
`build=0, apply_optical_solid_output_ports=False` (bugs/0166), on the assumption it "only
feeds PupilCalc paraxial math; it never NS-traces through the solid meshes." That holds for
a centered-sequential chain — but when the reference chain still carries a **promoted
optical SOLID** (a glued beam-splitter cube / STL body), `PupilCalc`'s reference launch is
NON-SEQUENTIAL and traces *through* the solid mesh. With `build=0` + `ports=False` the
system keeps the dummy int-`EEE`, so that trace dies and silently falls back to a coarse
geometric launch aim — wrong EPD/aim, error spam, and an unreliable ray-traced RMS that
breaks the best-image solve.

(The 2-D Spot Diagram itself is unaffected: `_build_geometric_image_samples_full` runs its
own `PupilCalc` on the full mesh-built system, not on this reference. The reference feeds
the 3-D ray-launch aim, `_collect_optics_info`'s EPD readout, and the best-focus solve.)

## Fix (general, not scene-specific)

`_pupil_model_inputs` now gates the reference build on geometry:

```python
pupil_needs_geometry = self._rows_require_geometry_build(pupil_rows)
pupil_system = _build_system_from_specs(
    self._serializable_specs_for_rows(pupil_rows),
    build=1 if pupil_needs_geometry else 0,
    apply_optical_solid_output_ports=False,
)
```

When the reference rows carry a solid/STL body (`_rows_require_geometry_build` → True) it
builds real meshes so the NS reference trace works; the bugs/0166 speedup still holds for
the centered-sequential case (no solids → `build=0`, no force-mesh). Verified on the
measured beam-splitter scene: pupil-system `EEE` int-entries `[0..7] → []`,
`PupilCalc.Pattern` raises → OK.

## Does the Spot Diagram change?

No — the 2-D/3-D Spot trace already runs on the full mesh system, so the spot RMS/shape is
unchanged. What the fix corrects is the **ray-launch reference / EPD** (the aim of the rays
drawn in 3-D), removes the error spam, and restores a clean ray-traced RMS so **Solve Best
Focus** can converge on a beam-splitter scene. In-app eyeball owed for the ray aim + solve.

## Guard

`validate_open3d_pupil_reference_solid_mesh` (display-free): the `build=0`+`ports=False`
trap (int `EEE`), the `build=1` real-mesh remedy, and the `_pupil_model_inputs` source gate
(`_rows_require_geometry_build` → `build=1`). Penta phase 165.
