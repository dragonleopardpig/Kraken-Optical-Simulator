# 0126 — Ray Count ignored on a non-branching non-seq scene (20 → 201 cone explosion)

## Symptom

Two flags on the same scene (a 150 mm machine-vision chain with one promoted BK7
mesh solid slid +27.5 mm along the axis):

- `flag_20260624_084750_167`:
  > "enabled Show rays, seems the rays don't respect the ray count."
- `flag_20260624_085043_656`:
  > "click Trace Now, it takes extraordinary long time, although ray count is 20."

`Ray Count` is 20 but Open 3D draws a dense disk of rays (`ray_actor_count = 2770`)
and a "Trace Now" runs for ~70 s.

## Root cause

`step_overlay_poses` / `promoted_solid_rows` pin the scene: a single promoted solid,
`desp = [0, 0, 27.5]` (an AXIAL slide only), `tilt = [0, 0, 0]`, `diameter = 78`,
`glass = BK7`. It never branches or folds — it is one rotationally-symmetric
converging cone about the global axis. The promoted mesh forces `use_nonseq = True`.

The launch pupil used to hand **every** `use_nonseq` / `use_folded` scene the
area-filling disk. In `world_cone` mode that disk is the meridional fan revolved
about the axis: `1 + (count // 2) * azimuths = 1 + (20//2)*20 = 201` pupil samples.
Each sample is a slow non-seq mesh trace, so:

- **Show rays** drew 201 pupil rays (≈ 2770 ray-segment actors), not 20; and
- **Trace Now** ran 201 mesh traces instead of 20 (~70 s).

`_launch_pupil_prefers_meridional_fan` keyed only on `use_nonseq` / `use_folded`:

```python
if bool(trace_state.get("use_nonseq")) or bool(trace_state.get("use_folded")):
    return False   # -> area-filling disk, revolved to 201 in world_cone
return True
```

The recorded `sampling_diagnostics` also show the mode churning around this: with
the solid promoted, `preview_3d_mode` flipped to `world_envelope` (intended 20-ray
golden disk) but the committed / cached / inspector bundle stayed `world_cone`
(`cached_bundle_mode = "world_cone"`, `prefers_meridional_fan = false`). `Trace Now`
(`build_trace_now_preview`) re-uses the inspector's last refresh mode (`world_cone`)
and re-samples it, so the non-seq revolve fires and produces the 201-ray bundle.

`has_nonseq_geometry` could not be used to gate this: it is `True` for ANY non-zero
`tilt` OR `desp` — **including the axial `desp_z = 27.5`** — so it would force the
disk on exactly the scene we want on the fan.

## Fix

`_launch_pupil_prefers_meridional_fan` now reasons about branching, not bare
`use_nonseq`. A non-seq / folded scene keeps the area-filling disk only when it can
genuinely **branch** (`has_beam_splitter` / `has_probabilistic_nonseq` /
`has_diffuse_scatter`), **fold** (`use_folded` / a `Mirror` surface), or **break
rotational symmetry** (a tilt or a transverse `desp_x` / `desp_y`). Otherwise — a
provably non-branching, rotationally-symmetric in-line refractive solid — it
collapses back to the uniform Ray-Count fan (exactly `count` rays):

```python
if not (use_nonseq or use_folded):
    return True
if use_folded or has_beam_splitter or has_probabilistic_nonseq or has_diffuse_scatter:
    return False
if self._scene_breaks_rotational_symmetry():     # tilt / desp_x/y / Mirror; NOT desp_z
    return False
if not has_optical_stl_solid:                     # unexplained use_nonseq -> fail to the disk
    return False
return True
```

A new `_scene_breaks_rotational_symmetry` helper flags any `tilt_*`, `desp_x` /
`desp_y`, or a `Mirror` surface — but deliberately **not** an axial `desp_z` (an
element slid along the optical axis keeps the symmetry).

This collapses the flagged scene to a 20-ray fan and also keeps `preview_3d_mode`
**stable** (`world_cone` both before and after the promote), so the seq→non-seq
transition no longer leaves `Trace Now` re-sampling a stale `world_cone` disk. The
design **fails toward the disk**: anything that branches, folds, or goes off-axis
still gets the full sagittal width, so rays never silently vanish from a split path.

## Test

`KrakenOS/UI/validate_open3d_ray_count_respects_nonbranching.py::run_checks` —
display-free; binds the real `TracePreviewSamplingMixin` methods onto a light fake
editor and checks the predicate + the resulting pupil sample count:

- **A** sequential scene prefers the fan (baseline unchanged);
- **B** the axial non-branching solid (`use_nonseq` + `has_optical_stl_solid`,
  `desp_z` only) prefers the fan, and `_sample_ray_count_cone_points` returns
  exactly `count` (20) — no 20 → 201 explosion;
- **C** a beam splitter keeps the full revolved disk (201);
- **D** a tilted element keeps the disk; **E** a transverse `desp_x` keeps the disk;
- **F** a folded preview keeps the disk; **G** a `Mirror` surface keeps the disk;
- **H** an axial `desp_z` does NOT break rotational symmetry;
- **source contract** — the predicate consults `has_beam_splitter`,
  `_scene_breaks_rotational_symmetry`, `has_probabilistic_nonseq`, and early-returns
  the fan for non-branched scenes (not a bare `use_nonseq` → disk).

Penta **phase 117** runs this guard. Mutation-tested: reverting the predicate to the
old `use_nonseq → disk` form flips B to FAIL ("got 201 pupil samples, expected 20")
plus the source-contract checks.

## Note — in-app eyeball owed

Headless can't drive the embedded-VTK Open 3D draw or "Trace Now", so the visible
20-ray fan and the fast retrace are verified in-app. The guard pins the pupil-count
math; if a non-branching scene still explodes, `sampling_diagnostics`
(`prefers_meridional_fan`, `cached_bundle_mode`) plus `ray_actor_count` isolate the
remainder to the launch-mode resolution.
