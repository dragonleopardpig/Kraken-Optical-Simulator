"""Definitive cProfile of the REAL thickness-dimension overlay path on the REAL
AZ85 folded RA-mirror scene. Sweeps ray count to see whether add_overlays cost
grows with ray-actor count, and cProfiles the WORST case. Builds a real headless
KrakenLayoutEditor + Kraken3DInspector (real offscreen render window)."""
from __future__ import annotations
import contextlib, cProfile, io, pstats, sys, time

import KrakenOS as _Kos  # noqa: F401
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_timing import reset_open3d_timing_log

_AZ85 = "machine_vision_AZ85_RA_Mirror.py"


def log(m):
    sys.stdout.write(m + "\n"); sys.stdout.flush()


def _counts(insp):
    try:
        return insp._debug_actor_counts()
    except Exception:
        return {}


def main() -> int:
    reset_open3d_timing_log(reason="probe_thickness_profile")
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1500x920+20+20")
        app.auto_save_plot_var.set(False)
        app.load_layout_by_name(_AZ85, refresh=False)
        app.show_physical_distances_var.set(True)
        app.open_3d_view()
        try:
            app.update(); app.update_idletasks()
        except Exception:
            pass
        insp = app._three_d_inspector
        if insp is None or not insp.available:
            log(f"inspector unavailable: {getattr(insp, 'unavailable_reason', '?')}")
            return 2
        insp.show_rays_var.set(True)
        insp.show_detector_overlays_var.set(True)
        svc = insp._open3d_thickness_dimension_service()

        for rc in (11, 41, 121):
            try:
                app.ray_count_var.set(str(rc))
            except Exception:
                pass
            app._invalidate_preview_scene_trace()
            with contextlib.redirect_stdout(io.StringIO()):
                t0 = time.perf_counter()
                insp.refresh_from_editor(force_retrace=True)
                try:
                    app.update()
                except Exception:
                    pass
                refresh_ms = (time.perf_counter() - t0) * 1000.0
            c = _counts(insp)
            system = getattr(app, "last_system", None)
            bundle = getattr(insp, "_current_scene_bundle", None)
            times = []
            for _ in range(3):
                with contextlib.redirect_stdout(io.StringIO()):
                    t0 = time.perf_counter()
                    n = svc.add_overlays(system, bundle)
                    times.append((time.perf_counter() - t0) * 1000.0)
            log(f"ray_count={rc:4d}  ray_actors={c.get('ray_actors')}  view_props={c.get('view_props')}  "
                f"thickness_actors={c.get('thickness_dimension_actors')}  full_refresh={refresh_ms:8.1f}ms  "
                f"add_overlays(min/med/max)={min(times):7.1f}/{sorted(times)[1]:7.1f}/{max(times):7.1f}ms  n={n}")

        # cProfile ONE add_overlays at the HIGH ray count (state from last loop).
        pr = cProfile.Profile()
        with contextlib.redirect_stdout(io.StringIO()):
            pr.enable()
            svc.add_overlays(system, bundle)
            pr.disable()
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(30)
        log("=== cumulative profile of ONE add_overlays (high ray count) ===")
        log(s.getvalue())
        s2 = io.StringIO()
        pstats.Stats(pr, stream=s2).sort_stats("tottime").print_stats(20)
        log("=== tottime ===")
        log(s2.getvalue())
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
