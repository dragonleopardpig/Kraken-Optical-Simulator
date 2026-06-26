"""Display-free guard for bugs/0166: toggling a display-layer overlay
(reference surfaces / detector overlays / thickness dimensions / terminal
diagnostics / placement handles) must RE-RENDER the cached scene, never rebuild
the optical solids + re-trace.

The three overlay checkboxes all fire ``Kraken3DInspector._on_scene_visibility_changed``.
It used to call ``refresh_from_editor()`` unconditionally; on a saved promoted
beam-splitter scene that forces a full retrace
(``has_promoted_step_optical_solid_rows`` -> ``requires_open3d_retrace``), which
re-meshes every solid (the user's ~46x "Creating solid objects" prints). The fix
routes the handler through ``can_reuse_current_scene_for_display_toggle`` and a
render-only ``refresh_scene`` whenever the inspector still holds a valid, non-dirty
cached scene -- mirroring the Show Rays fast toggle.

This guard pins, all headless (no VTK):

  * a real full refresh of ``machine_vision_150mm_GN.py`` DOES build solids
    (baseline: so a toggle that rebuilt would pay the same cost);
  * right after that refresh the display-toggle gate is reusable (True) -- so the
    overlay toggle re-renders with ZERO new solid builds;
  * dirtying the preview trace (a geometry edit) flips the gate back to False, so
    real edits still rebuild;
  * a missing cached scene -> False (first render still builds);
  * (source contract) ``_on_scene_visibility_changed`` routes through the gate and
    ``refresh_scene``, and ``refresh_scene`` is render-only -- it never calls
    ``build_system`` / ``_build_preview_system_rays_bundle`` / ``Prerequisites3DSolids``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_overlay_toggle_no_rebuild

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import inspect
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from KrakenOS.Prerequisites3D import Prerequisites
from KrakenOS.UI.layout_editor import Kraken3DInspector, _load_python_data
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

_SCENE = Path(__file__).resolve().parents[2] / "attachment" / "machine_vision_150mm_GN.py"


class _FakeInspector:
    """Mirror the per-scene cache that refresh_scene stores on the real inspector."""

    def __init__(self, editor) -> None:
        bundle = editor._last_scene_bundle
        self._current_system = editor.last_system
        self._current_rays = editor.last_rays
        self._current_scene_bundle = bundle
        try:
            self._current_row_names = list(editor._preview_render_row_names(bundle) or [])
        except Exception:
            self._current_row_names = ["row"]


def _build_editor():
    info = _load_python_data(_SCENE)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.tk = object()  # break tkinter __getattr__ recursion on the __new__ instance
    editor.current_layout_file = str(_SCENE)
    editor._normalize_special_rows()
    return editor


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    if not _SCENE.exists():
        return False, [f"FAIL: scene fixture missing: {_SCENE}"]

    editor = _build_editor()

    # --- one real full refresh: populate the scene cache AND count solid builds.
    build_count = [0]
    orig_solids = Prerequisites.Prerequisites3DSolids

    def _counting_solids(self):
        build_count[0] += 1
        return orig_solids(self)

    Prerequisites.Prerequisites3DSolids = _counting_solids
    try:
        capture = io.StringIO()
        with redirect_stdout(capture), redirect_stderr(capture):
            editor._build_preview_system_rays_bundle(
                sampling_mode=editor._preview_2d_sampling_mode(),
                update_state=True,
                include_live_step_overlays=False,
            )
    finally:
        Prerequisites.Prerequisites3DSolids = orig_solids

    # Baseline: a full refresh of this beam-splitter scene DOES mesh solids, so a
    # toggle that rebuilt would pay the same cost -- the fix is meaningful only
    # because the refresh is expensive.
    if build_count[0] <= 0:
        failures.append(
            "FAIL: the full refresh built no solids -- baseline broken, the guard "
            "cannot prove the toggle now avoids a rebuild"
        )
    if editor.last_system is None or editor.last_rays is None or editor._last_scene_bundle is None:
        failures.append("FAIL: the full refresh did not populate the scene cache (last_system/rays/bundle)")
        return (not failures), failures

    svc = editor._open3d_trace_refresh_service()
    insp = _FakeInspector(editor)

    # 1) right after a clean refresh the display-toggle gate must be reusable.
    if not svc.can_reuse_current_scene_for_display_toggle(insp):
        failures.append(
            "FAIL: can_reuse_current_scene_for_display_toggle is False after a clean "
            "refresh -- an overlay toggle would rebuild + re-mesh the solids (bug 0166)"
        )

    # 2) a geometry edit dirties the preview trace -> gate False -> real rebuild.
    editor._preview_scene_trace_dirty = True
    if svc.can_reuse_current_scene_for_display_toggle(insp):
        failures.append(
            "FAIL: gate stayed True while _preview_scene_trace_dirty -- a geometry edit "
            "would no longer rebuild (stale display)"
        )
    editor._preview_scene_trace_dirty = False

    # 3) no cached scene yet -> gate False (first render still builds).
    insp_empty = _FakeInspector(editor)
    insp_empty._current_system = None
    if svc.can_reuse_current_scene_for_display_toggle(insp_empty):
        failures.append("FAIL: gate True with no cached system -- would skip the first render's build")

    # 4) source contract: the overlay handler routes through the gate + refresh_scene.
    handler_src = inspect.getsource(Kraken3DInspector._on_scene_visibility_changed)
    if "can_reuse_current_scene_for_display_toggle" not in handler_src:
        failures.append("FAIL: _on_scene_visibility_changed does not consult the display-toggle reuse gate")
    if "refresh_scene(" not in handler_src:
        failures.append("FAIL: _on_scene_visibility_changed has no render-only refresh_scene fast path")

    # 5) render-only contract: refresh_scene must never rebuild the system.
    refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    for forbidden in ("build_system(", "_build_preview_system_rays_bundle(", "Prerequisites3DSolids"):
        if forbidden in refresh_src:
            failures.append(f"FAIL: refresh_scene references {forbidden!r} -- not render-only")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0166 overlay toggle must not rebuild the optical solids")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] overlay toggles re-render the cached scene -- no solid rebuild (bugs/0166)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
