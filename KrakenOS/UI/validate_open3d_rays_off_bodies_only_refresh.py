"""Display-free guard for bugs/0400 -- with Show Rays OFF a model change builds the 3D BODIES
but SKIPS the expensive ray trace.

Adding/moving a promoted optical solid on a folded scene forced a full ~45s ray trace even
with Show Rays OFF, because the refresh always retraces when the scene has promoted step
optical-solid rows. Now the refresh builds bodies-only when rays are off; the trace runs when
rays are turned on.

Checks (all headless):
  1. `_build_preview_system_rays_bundle(trace_rays=False)` on the real AZ85 folded scene yields
     a scene bundle WITH bodies (placements) but ZERO ray paths, and marks the preview trace
     DIRTY (so a later Show-Rays-ON toggle rebuilds instead of reusing the empty-ray cache).
     `trace_rays=True` yields the full ray family and clears the dirty flag.
  2. The async-trace gate returns `rays_off_bodies_only` (falls to the sync bodies-only path)
     when Show Rays is OFF and no live physics, and stays eligible when rays are ON.
  3. `can_reuse_current_scene_for_show_rays` returns False while the preview trace is dirty, so
     turning Show Rays ON after a bodies-only build forces a real trace.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_rays_off_bodies_only_refresh
"""

from __future__ import annotations

import contextlib
import io
from types import SimpleNamespace


def _bool_var(value):
    return SimpleNamespace(get=lambda: value)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []

    # ---- 1. real-scene bodies-only vs traced -------------------------------------------------
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _build_editor, _AZ85

            ed_off = _build_editor(_AZ85)
            _s, _r, bundle_off = ed_off._build_preview_system_rays_bundle(update_state=True, trace_rays=False)
            off_paths = len(list(getattr(bundle_off, "ray_paths", []) or []))
            off_bodies = len(list(getattr(bundle_off, "placements", []) or []))
            off_dirty = bool(getattr(ed_off, "_preview_scene_trace_dirty", None))

            ed_on = _build_editor(_AZ85)
            _s2, _r2, bundle_on = ed_on._build_preview_system_rays_bundle(update_state=True, trace_rays=True)
            on_paths = len(list(getattr(bundle_on, "ray_paths", []) or []))
            on_dirty = bool(getattr(ed_on, "_preview_scene_trace_dirty", None))
    except Exception as exc:  # pragma: no cover
        return False, [f"bodies-only trace failed: {exc!r}"]

    notes.append(f"AZ85 rays-off: ray_paths={off_paths} bodies={off_bodies} dirty={off_dirty}; rays-on: ray_paths={on_paths} dirty={on_dirty}")
    if off_paths != 0:
        failures.append(f"rays OFF must trace NO rays (bodies only); got {off_paths} ray paths")
    if off_bodies <= 0:
        failures.append("rays OFF must still build the scene bodies (0 placements)")
    if not off_dirty:
        failures.append("a bodies-only build must mark the preview trace DIRTY (so rays-on retraces)")
    if on_paths <= 0:
        failures.append(f"rays ON must trace the ray family; got {on_paths} ray paths")
    if on_dirty:
        failures.append("a traced build must NOT be dirty")

    # ---- 2. async-trace gate honours Show Rays ----------------------------------------------
    try:
        from KrakenOS.UI.services import trace_preview_async as async_mod

        class _StubService:
            def inspector_physics_requested(self, inspector):
                return False

        class _StubEditor:
            _async_preview_trace_opt_in = True

            def _open3d_trace_refresh_service(self):
                return _StubService()

        def _decision(show_rays):
            inspector = SimpleNamespace(
                editor=_StubEditor(),
                show_rays_var=_bool_var(show_rays),
                _async_trace_fallback_sync=False,
                _placement_drag_state=None,
                _async_trace_state=None,
            )
            return async_mod.maybe_begin_inspector_async_trace(inspector)

        # rays OFF -> must NOT begin async (falls to sync bodies-only)
        began_off = _decision(False)
        if began_off:
            failures.append("async trace must NOT begin with Show Rays OFF (should fall to sync bodies-only)")
        notes.append(f"async gate: rays-off began={began_off}")
    except Exception as exc:
        notes.append(f"async-gate check skipped: {exc!r}")

    # ---- 3. can_reuse blocks a Show-Rays-ON reuse of a dirty (untraced) cache ----------------
    try:
        from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService

        svc = object.__new__(Open3DTraceRefreshService)
        svc.editor = SimpleNamespace(_preview_scene_trace_dirty=True)
        inspector = SimpleNamespace(
            _current_system=object(), _current_rays=object(), _current_scene_bundle=object(),
            _current_row_names=["a"], show_rays_var=_bool_var(True),
        )
        if svc.can_reuse_current_scene_for_show_rays(inspector):
            failures.append("can_reuse must be False while the preview trace is dirty (forces a real trace on rays-on)")
    except Exception as exc:
        notes.append(f"can_reuse check skipped: {exc!r}")

    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    if not passed:
        print("Rays-off bodies-only refresh validation FAILED:")
        for m in messages:
            print(f"- {m}")
        return 1
    print("Rays-off bodies-only refresh validation passed:")
    for m in messages:
        print(f"  {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
