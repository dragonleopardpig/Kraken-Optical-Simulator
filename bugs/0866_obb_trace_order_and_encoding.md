# 0866 -- two full-suite failures: a changed reference tracer, and an unencoded read

Found by running the **whole** suite in six shards before merging the Qt work back into the Tk
line (644 phases: 642 pass, plus the one known environment failure at phase 52).

## Phase 221 -- the reference tracer changed, not ours

`validate_open3d_folded_trace_perf_caches.py` check (6) demanded that `_fast_scene_ray_trace`
return **bit-exact, same-order** results as `pyvista.ray_trace`. That held only while both used
the same `obbTree`. Adding PySide6 to `devenv.nix` rebuilt the venv onto **pyvista 0.49**, whose
`ray_trace` orders its hits differently -- and pyvista now deprecates `obbTree` itself with
"does not reliably find intersections in some cases".

Checked against the geometry rather than assumed. On a radius-10 sphere, for every test ray:

| | hits | |p| |
|---|---|---|
| ours | 2 | 9.976687, 9.976687 |
| pyvista | 2 | 9.976687, 9.976687 |

The same two intersections, in the opposite order; and where a ray strikes an exact facet EDGE,
pyvista names the adjacent triangle (cell 572 where we say 531 -- both correct, the point lies on
the edge they share). Misses agree. **Our tracer is right.**

The check now orders both results along the ray before comparing, and accepts a differing cell
only when it shares an edge with ours. It compares what a tracer must get right -- where the ray
hits -- instead of an implementation detail of the library it is compared against.

## Phase 539 -- a new guard read source without an encoding

bugs/0743's rule: `Path(...).read_text()` with no encoding uses the locale, and VTK/Tk reset the C
locale mid-suite, so a guard that passes standalone fails inside the marathon.
`validate_open3d_0859_paraxial_report_shared.py` compared two exported CSVs with bare
`read_text()`. Named now.

## Why this matters beyond the two fixes

Both were invisible to the smoke gate (phases 630-644) and to every standalone run. The full
suite is what caught them, and it is what must run before the Qt work becomes the Tk line.
