"""Guard: Open 3D rebuilds the launch cone instead of reusing the 2D fan.

For a sequential, non-folded scene the 2D layout commits a flat ``world_envelope``
meridional fan while Open 3D wants a revolved ``world_cone`` (bug 0034). The feed
decision lives in ``Open3DTraceRefreshService._committed_scene_sampling_mode``:
the cached 2D scene bundle can only feed Open 3D when its sampling mode equals the
3D mode. That check used to trust the transient ``_active_preview_sampling_mode``,
which an Open 3D cone rebuild leaves pointing at ``world_cone`` -- so when the
committed tag was unset the cached *envelope* bundle was wrongly reported as
cone-ready and Open 3D reused the flat 2D fan (bug 0038: "3D goes back to fan").

This guards the fix: the committed mode must reflect the cached bundle's *actual*
launch mode, and ``current_or_rebuild_scene`` must rebuild the cone even after a
prior cone build left the transient at ``world_cone`` and the tag unset.

All checks are display-free (Agg backend, no Xvfb / GPU needed):

A. For a sequential scene the 3D mode is ``world_cone`` and the 2D mode is
   ``world_envelope`` (they differ, so a rebuild is required).
B. After committing the 2D envelope trace and then building a cone trace
   (transient -> ``world_cone``) with the committed tag cleared,
   ``_committed_scene_sampling_mode`` still reports ``world_envelope`` (read from
   the cached bundle), so ``_active_trace_can_feed_open3d`` is False.
C. ``current_or_rebuild_scene`` fed the cached envelope bundle returns a
   ``world_cone`` scene with the cone's (larger) ray-path count, not the fan's.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_cone_not_reused_as_fan

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from KrakenOS.UI.layout_editor import (
    LAYOUTS_DIR,
    KrakenLayoutEditor,
    _load_python_data,
    _load_python_title,
)
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor
from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService

LAYOUT_TITLE = "Zemax Double Gauss 28 Degree Field"


def _layout_path_by_title(title: str) -> "Path | None":
    for path in sorted(LAYOUTS_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            if str(_load_python_title(path)).strip() == title:
                return path
        except Exception:
            continue
    return None


def _ray_path_count(bundle) -> int:
    return len(list(getattr(bundle, "ray_paths", []) or []))


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    layout_path = _layout_path_by_title(LAYOUT_TITLE)
    if layout_path is None:
        notes.append("SKIP: Double Gauss 28 deg layout unavailable")
        return passed, notes

    info = _load_python_data(layout_path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = layout_path
    editor._normalize_special_rows()
    system = _build_runtime_system(layout_path, editor.rows)
    editor.last_system = system

    svc = Open3DTraceRefreshService(editor)

    # A. Sequential scene: 3D wants a cone, 2D stays a flat envelope.
    mode_2d = editor._preview_2d_sampling_mode()
    mode_3d = editor._preview_3d_sampling_mode()
    if mode_3d != "world_cone":
        notes.append(f"SKIP: scene 3D mode is {mode_3d!r}, not world_cone (not a sequential cone scene)")
        return passed, notes
    if mode_2d != "world_envelope":
        notes.append(f"FAIL: 2D mode is {mode_2d!r}, expected world_envelope")
        passed = False

    # Commit the 2D envelope trace, as a normal 2D refresh would.
    _sys_e, _rays_e, bundle_env = editor._build_preview_system_rays_bundle(
        sampling_mode="world_envelope", update_state=True, include_live_step_overlays=False,
    )
    fan_paths = _ray_path_count(bundle_env)

    # Build a cone trace (update_state=False) -> leaves the transient at
    # world_cone, like a prior Open 3D cone build, and clear the committed tag
    # to recreate the untagged state that triggered the reuse bug.
    editor._build_preview_system_rays_bundle(
        sampling_mode="world_cone", update_state=False, include_live_step_overlays=False,
    )
    editor._last_scene_trace_sampling_mode = None

    # B. Committed mode must come from the cached bundle (envelope), not the
    #    transient world_cone -> so the cached fan is NOT cone-ready.
    committed = svc._committed_scene_sampling_mode()
    if committed != "world_envelope":
        notes.append(f"FAIL: committed mode is {committed!r}, expected world_envelope (bundle ground truth)")
        passed = False
    if svc._active_trace_can_feed_open3d():
        notes.append("FAIL: cached envelope fan reported as cone-ready (bug 0038 reuse)")
        passed = False

    # C. Feeding the cached envelope bundle still rebuilds the cone.
    result = svc.current_or_rebuild_scene(
        system=editor.last_system, rays=editor.last_rays, scene_bundle=bundle_env,
    )
    cone_paths = _ray_path_count(result.scene_bundle)
    if result.sampling_mode != "world_cone":
        notes.append(f"FAIL: Open 3D resolved {result.sampling_mode!r}, expected world_cone")
        passed = False
    if cone_paths <= fan_paths:
        notes.append(
            f"FAIL: Open 3D reused the flat fan ({cone_paths} paths <= fan {fan_paths}); cone not rebuilt"
        )
        passed = False

    if verbose:
        notes.append(
            f"2d={mode_2d}, 3d={mode_3d}, committed={committed}, "
            f"fan_paths={fan_paths}, cone_paths={cone_paths}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Open 3D rebuilds the launch cone instead of reusing the 2D fan")
        return 0
    print("[FAIL] Open 3D cone-not-reused-as-fan guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
