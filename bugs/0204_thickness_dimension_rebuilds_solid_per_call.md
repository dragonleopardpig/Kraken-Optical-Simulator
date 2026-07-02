# 0204 — BUG: 3-D refresh is "exceptionally long" — the thickness-dimension overlay rebuilds + force-meshes the whole system once per dimension endpoint ("rebuild of solid elements")

**Status: RESOLVED. The thickness-dimension overlay now reads each row's world origin straight from
the ALREADY-BUILT system's transform list (`system.Pr3D.TRANS_2A`, the mirror of the surface-normal
`[:3, 2]` read that was already there — origin is `[:3, 3]`), instead of rebuilding the entire optical
system — and force-meshing the promoted BK7 cube — once per call. On the folded AZ85 RA-mirror scene
that is a `10629 ms → 5 ms` collapse of the thickness step (1942×); the rebuild fallback is kept only
for headless callers that pass no system.**

## Origin

The user re-flagged the working folded AZURE ELS-85 layout
(`KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`, AZ85 = ELS-85 surrogate) in an
Open-3D session (`attachment/recorded_bug_repros/flag_20260702_130129_167/`) with a perf complaint:

> *"the loading now is exceptionally long, I think old bug surfaces: rebuild of solid elements."*

The pasted `Open3DTiming` log showed a ~50 s refresh dominated by `thickness_dim_ms ≈ 40000` and a
storm of `Creating solid objects for optical elements` prints (the OCC force-mesh of the promoted
BK7 cube). The user's hypothesis — a stray rebuild of the solid elements — was essentially correct.

## Root cause

The 3-D thickness-dimension overlay (`services/open3d_thickness_dimensions.py`) draws one dimension
per thickness-loop row and calls `_surface_reference_world_point` **twice** per dimension (near + far
endpoint). The AZ85 scene has 16 dimensions → **32 calls per refresh**.

`_surface_reference_world_point` (`services/scene_placement_commands.py`) fell through to
`_surface_origin_for_rows` → `_surface_transform_for_rows`
(`services/layout_table_workbench.py:3636`), which does:

```python
system = _build_system_from_specs(self._serializable_specs_for_rows(rows))
```

with the DEFAULT `apply_optical_solid_output_ports=True`, so **every one of the 32 calls rebuilt the
whole optical system AND force-meshed the promoted BK7 cube** via
`apply_optical_solid_output_port_system_overrides` (~1.3 s each, the "Creating solid objects…" print)
→ ~40 s per refresh. This is the same force-mesh cost class as bugs/0166.

The tell that it was avoidable: the *sibling* method `_surface_reference_world_normal` already read
the surface normal straight from the passed system's transform list (`[:3, 2]`) with no rebuild. The
origin is the same 4×4 transform's `[:3, 3]` column — it was there for free the whole time.

## Fix

`services/scene_placement_commands.py` `_surface_reference_world_point`: before the rebuild fallback,
read the row's origin from the passed-in system's transform list (mirroring the normal read):

```python
transforms = self._system_transform_list(system)
if transforms is not None and 0 <= row_index < len(transforms):
    origin = np.asarray(transforms[row_index], dtype=float).reshape(4, 4)[:3, 3]
    if origin.size >= 3 and np.all(np.isfinite(origin)):
        return origin.astype(float)
# else fall through to the old _surface_origin_for_rows rebuild
```

The overlay already builds the scene system once and passes it in, so the 32 calls now cost one array
slice each. The rebuild fallback is kept for headless callers that pass no system (or one carrying no
transforms). STL rows and `use_folded` rows still return earlier via their own branches — the fast
path only fires for the non-STL, non-folded rows that previously reached the fallback (the RA-mirror
`use_nonseq` case).

## Verification (display-free)

`bugs/probe_0204_thickness_fastpath.py` and the standalone guard
`KrakenOS/UI/validate_open3d_thickness_dimension_no_rebuild.py` both patch counters onto
`layout_table_workbench._build_system_from_specs` and
`layout_editor.apply_optical_solid_output_port_system_overrides` (the force-mesh is imported into the
`layout_editor` namespace, so it must be patched THERE) and compare the two paths over every
thickness-loop row `rows[:-1]`:

```
FAST rebuilds=0 force-mesh=0; SLOW rebuilds=8 force-mesh=8; rows compared=8; max |Δorigin|=3.26e-27 mm
RESULT: PASS
```

- **correctness**: the fast path's origins are bit-identical to the old rebuild (max |Δ| ≈ 3e-27 mm) —
  the fix moves no dimension.
- **no-rebuild**: the fast path triggers 0 rebuilds / 0 force-meshes, while the control slow path
  force-meshes the BK7 cube once per row (≥1) — a revert to the rebuild is caught.

Guard wired as `phase_182_thickness_dimension_no_rebuild` in the comprehensive penta validator;
baseline updated `"182": "pass"`.
