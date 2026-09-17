"""Instrument the REAL _surface_reference_world_point on the folded AZ85 scene:
which branch does it take, how many times per add_overlays, and its total cost --
plus per-internal-call timing of add_overlays with a wrapper that tallies the
heavy helpers. Confirms whether the folded scene rebuilds the system per row or
takes the cheap folded branch, and whether add_overlays cost tracks ray count."""
from __future__ import annotations
import contextlib, io, sys, time

import KrakenOS as _Kos  # noqa: F401
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_timing import reset_open3d_timing_log

_AZ85 = "machine_vision_AZ85_RA_Mirror.py"


def log(m):
    sys.stdout.write(m + "\n"); sys.stdout.flush()


def main() -> int:
    reset_open3d_timing_log(reason="probe_srwp")
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1500x920+20+20")
        app.auto_save_plot_var.set(False)
        app.load_layout_by_name(_AZ85, refresh=False)
        app.show_physical_distances_var.set(True)
        app.open_3d_view()
        with contextlib.suppress(Exception):
            app.update()
        insp = app._three_d_inspector
        if insp is None or not insp.available:
            log(f"inspector unavailable: {getattr(insp, 'unavailable_reason', '?')}")
            return 2
        insp.show_rays_var.set(True)

        # Wrap the heavy helpers with counters+timers.
        tally = {}

        def wrap(obj, name):
            orig = getattr(obj, name)
            key = name

            def wrapped(*a, **k):
                t0 = time.perf_counter()
                try:
                    return orig(*a, **k)
                finally:
                    d = tally.setdefault(key, [0, 0.0])
                    d[0] += 1
                    d[1] += (time.perf_counter() - t0) * 1000.0
            setattr(obj, name, wrapped)
            return orig

        # editor-level (bound on the app instance)
        o1 = wrap(app, "_surface_reference_world_point")
        o2 = wrap(app, "_surface_origin_for_rows")
        o3 = wrap(app, "_surface_transform_for_rows")
        o4 = wrap(app, "_compute_world_folded_layout_geometry_for_rows")
        o5 = wrap(app, "_resolved_trace_mode")
        # inspector-level
        i1 = wrap(insp, "_scene_bounds")
        i2 = wrap(insp, "_row_scene_bounds")
        i3 = wrap(insp, "_visible_actor_bounds")

        # check folded intent
        try:
            ts = app._resolved_trace_mode(system=getattr(app, "last_system", None))
            log(f"use_folded = {ts.get('use_folded')}  active={ts.get('active')}")
        except Exception as exc:
            log(f"resolved_trace_mode failed: {exc}")

        for rc in (41, 201):
            with contextlib.suppress(Exception):
                app.ray_count_var.set(str(rc))
            app._invalidate_preview_scene_trace()
            with contextlib.redirect_stdout(io.StringIO()):
                insp.refresh_from_editor(force_retrace=True)
                with contextlib.suppress(Exception):
                    app.update()
            c = insp._debug_actor_counts()
            svc = insp._open3d_thickness_dimension_service()
            system = getattr(app, "last_system", None)
            bundle = getattr(insp, "_current_scene_bundle", None)
            tally.clear()
            with contextlib.redirect_stdout(io.StringIO()):
                t0 = time.perf_counter()
                n = svc.add_overlays(system, bundle)
                dt = (time.perf_counter() - t0) * 1000.0
            log(f"\n--- ray_count={rc}  ray_actors={c.get('ray_actors')}  view_props={c.get('view_props')}  "
                f"thickness_actors={c.get('thickness_dimension_actors')}  add_overlays={dt:.1f}ms  n={n} ---")
            for k in sorted(tally, key=lambda x: -tally[x][1]):
                cnt, ms = tally[k]
                log(f"    {k:48s} calls={cnt:4d}  total={ms:8.1f}ms")
        return 0
    finally:
        with contextlib.suppress(Exception):
            app.destroy()


if __name__ == "__main__":
    sys.exit(main())
