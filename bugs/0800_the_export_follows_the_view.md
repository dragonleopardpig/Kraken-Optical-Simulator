# 0800 -- the export draws what the VIEW shows, not what the model holds

Two reports in one session, one contract:

* *"the surrogate is hidden, but the STEP output still shows the surrogate."*
* *"the Show Rays is on, but fresh launch KrakenOS 3D won't show it, but export STEP will show.
  I turn off, export STEP won't show."* and *"Rays are not visible at startup during launch
  although rays is on."*

## Measured

Hiding the four surrogate rows in the 3D browser, then exporting:

    hiding rows [1, 2, 4, 5]; _step_export_hidden_state -> frozenset({1, 2, 4, 5})
    analytic surfaces WRITTEN: 7   (expected 3)

The hidden state was computed correctly and then ignored.

And on a fresh load, with the app's own loader:

| | after load | fresh 3D open | after Trace Now |
|---|---|---|---|
| `_preview_trace_deferred_until_requested` | **True** | **True** | False |
| ray paths in the scene | -- | **0** | 3249 |
| `show_rays_var` | True | True | True |
| ray polylines the export wrote | -- | **156** | 156 |

So the view drew nothing, the toggle said ON, and the file carried 156 ray tubes.

## Root cause

**The hidden rows.** This is bugs/0797's shape again. `_step_export_hidden_state` is consulted
by `_collect_3d_step_export_meshes`, `_collect_step_edge_and_extra_meshes` and
`_collect_native_step_export_shapes` -- but the two ANALYTIC writers in `cad_step_export` walk
`sdt[j]` directly and only ever checked `surf.Drawing`, the row's 2D drawing flag. The surrogate
rows are exactly what those loops write, so hiding a surrogate removed it from the view and left
it in the file.

**The rays.** A fast load sets `_preview_trace_deferred_until_requested` (bugs/0646), so the 3D
view opens BODIES ONLY. `_step_export_ray_polylines` does not read that gate -- it calls
`_trace_preview_rays` itself -- so it wrote rays that had never been on screen. Turning Show Rays
off suppressed them only because that path checks `_step_export_hidden_state()[2]`.

## Fix, and the one thing deliberately NOT done

The obvious remedy for the rays -- trace when the 3D view opens -- is wrong. **bugs/0718 made
that gate authoritative on purpose**: the non-sequential trace runs in-process and, on crashed
geometry (a forced lens-into-mirror move), wedges in the mesh ray loop and hangs the UI with no
way to interrupt it, so only a deliberate Trace Now may clear it. Clearing it on open would
re-open exactly that hang. The gate stays.

What changes instead:

* both analytic writers take `hidden_rows` and skip those rows; `export_3d_step` passes
  `_step_export_hidden_state()[0]` down both the analytic and the native worker route;
* `_step_export_ray_polylines` returns nothing while the gate is set -- the drawing follows the
  view, and the export stops running the very trace 0718 defers;
* `_pending_rays_note` makes the view say so, on both open paths (direct and after the STEP
  cache warm-up): *"rays are PENDING after a fast load: press Trace Now to trace them (the
  STEP/DXF export follows the view)."* The gate was never the problem; the silence was.

## Verified

    analytic surfaces WRITTEN: 3  (expected 3)
    rays exported while the trace is DEFERRED: 0   (the view shows 0)
    rays exported after Trace Now: 156
    hidden rows seen by the export: [1, 2, 4, 5]

## Guard

`python -m KrakenOS.UI.validate_open3d_0800_the_export_follows_the_view` -- display-free, a
synthetic scene in a temp dir. It pins that both writers accept and honour `hidden_rows` and that
`export_3d_step` supplies them; that hiding four of seven rows exports three; that the ray export
is empty while the gate is set and carries rays once traced; that the note appears only when the
trace is deferred AND rays are on; and -- the regression that matters most -- that `open_3d_view`
does **not** clear `_preview_trace_deferred_until_requested`, so bugs/0718's protection survives
this fix. Penta phase 583.
