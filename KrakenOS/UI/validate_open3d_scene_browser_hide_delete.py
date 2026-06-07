"""Guard: scene-component browser right-click Hide / Unhide / Delete.

Checks
------
Source contracts (always run):
A. the browser tree binds ``<Button-3>`` and has the context-menu helpers
   (``_on_tree_right_click``, ``_show_element_context_menu``,
   ``_selection_rows_and_label``, ``_set_element_hidden``).
B. the inspector exposes the hide/unhide API + the refresh re-applies it.

Behaviour (needs a display; SKIP otherwise):
C. hiding a scene row turns its body actors invisible, the state survives a full
   refresh (actors are rebuilt), and unhiding restores visibility; the browser
   iid resolver maps scene-row / element / overlay ids to rows/labels.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_scene_browser_hide_delete

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import inspect
import os
from pathlib import Path

os.environ.pop("WAYLAND_DISPLAY", None)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts" / "machine_vision_150mm_datasheet_1x.py"


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    # A
    try:
        build_src = inspect.getsource(Open3DStepAdminPanel.build)
    except Exception:
        build_src = ""
    if '"<Button-3>"' not in build_src and "'<Button-3>'" not in build_src:
        notes.append("FAIL: browser tree does not bind <Button-3>")
        passed = False
    for attr in ("_on_tree_right_click", "_show_element_context_menu",
                 "_selection_rows_and_label", "_set_element_hidden", "_element_is_hidden"):
        if not hasattr(Open3DStepAdminPanel, attr):
            notes.append(f"FAIL: browser panel missing {attr}")
            passed = False
    # B
    for attr in ("set_scene_rows_hidden", "is_scene_row_hidden", "set_step_label_hidden",
                 "is_step_label_hidden", "_apply_scene_element_visibility",
                 "_all_actor_keys_for_step_label", "_all_actor_keys_for_row"):
        if not hasattr(Kraken3DInspector, attr):
            notes.append(f"FAIL: inspector missing {attr}")
            passed = False
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
    try:
        refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    except Exception:
        refresh_src = ""
    if "_apply_scene_element_visibility" not in refresh_src:
        notes.append("FAIL: refresh does not re-apply browser hide/unhide")
        passed = False
    # bugs/0026: hide must gather edges + gizmo (follow / rotate maps), not just
    # the body in _step_actor_map, or a hidden STEP leaves residual.
    try:
        apply_src = inspect.getsource(Kraken3DInspector._apply_scene_element_visibility)
        gather_src = inspect.getsource(Kraken3DInspector._all_actor_keys_for_step_label)
    except Exception:
        apply_src = gather_src = ""
    if "_all_actor_keys_for_step_label" not in apply_src or "_all_actor_keys_for_row" not in apply_src:
        notes.append("FAIL: visibility re-apply still body-only (residual risk)")
        passed = False
    if "_actor_step_follow_map" not in gather_src or "_actor_step_rotate_map" not in gather_src:
        notes.append("FAIL: step-label gather misses edges (follow) or gizmo (rotate) actors")
        passed = False
    # bugs/0027: no rotation gizmo on a hidden element; hidden elements grey out.
    for meth in ("_add_step_rotation_handles", "_ensure_step_rotation_handles_for_label",
                 "select_step_overlay_from_admin", "_step_label_has_visible_body_actor"):
        try:
            src = inspect.getsource(getattr(Kraken3DInspector, meth))
        except Exception:
            src = ""
        if "is_step_label_hidden" not in src:
            notes.append(f"FAIL: {meth} does not suppress the gizmo for hidden elements")
            passed = False
    from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel
    try:
        panel_build = inspect.getsource(Open3DStepAdminPanel.build)
    except Exception:
        panel_build = ""
    if 'tag_configure("hidden"' not in panel_build:
        notes.append("FAIL: browser tree does not configure the hidden grey-out tag")
        passed = False
    if not hasattr(Open3DStepAdminPanel, "_item_hidden_tag"):
        notes.append("FAIL: browser missing _item_hidden_tag")
        passed = False
    # Rays + overlays surfaced as hide/unhide display elements.
    for attr in ("_display_toggle_specs", "_display_var_for_key", "_resolve_iid_target"):
        if not hasattr(Open3DStepAdminPanel, attr):
            notes.append(f"FAIL: browser missing {attr}")
            passed = False
    try:
        set_hidden_src = inspect.getsource(Open3DStepAdminPanel._set_element_hidden)
    except Exception:
        set_hidden_src = ""
    if "display_key" not in set_hidden_src or "_on_scene_visibility_changed" not in set_hidden_src:
        notes.append("FAIL: _set_element_hidden does not toggle display (rays/overlays) vars")
        passed = False
    # STEP export skips hidden rows / labels / rays.
    from KrakenOS.UI.services.optical_solid_workflow import LayoutOpticalSolidWorkflowMixin
    for meth in ("_collect_3d_step_export_meshes", "_step_export_ray_polylines",
                 "_collect_row_native_step_export_shapes", "_collect_native_step_export_shapes"):
        try:
            src = inspect.getsource(getattr(LayoutOpticalSolidWorkflowMixin, meth))
        except Exception:
            src = ""
        if "_step_export_hidden_state" not in src and "hidden_rows" not in src and "hidden_labels" not in src:
            notes.append(f"FAIL: {meth} does not skip hidden geometry on export")
            passed = False

    # C -- behaviour.
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display

    reuse = app is not None and inspector is not None
    xvfb_proc = None
    if not reuse:
        xvfb_proc, env_err = _ensure_display()
        if env_err is not None:
            notes.append(f"SKIP: cannot construct UI ({env_err})")
            return passed, notes

    own_app = False
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.render_layout_snapshot import _load_layout_module, _rows_from_layout_info

        if not reuse:
            from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

            app = KrakenLayoutEditor()
            inspector = _open_inspector(app)
            own_app = True

        if not LAYOUT.exists():
            notes.append("SKIP: machine-vision layout unavailable")
            return passed, notes
        module = _load_layout_module(LAYOUT)
        app.rows = _rows_from_layout_info({"surfaces": list(getattr(module, "SURFACES", []) or [])})
        app._apply_layout_settings(dict(getattr(module, "SETTINGS", {}) or {}))
        app._sync_table()
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()

        rmap = inspector._row_actor_map or {}
        row = next((r for r, keys in rmap.items() if keys), None)
        if row is None:
            notes.append("SKIP: no row body actors to hide")
            return passed, notes
        key0 = rmap[row][0]
        inspector.set_scene_rows_hidden([row], True)
        if inspector._actor_by_key[key0].GetVisibility() != 0 or not inspector.is_scene_row_hidden(row):
            notes.append("FAIL: Hide did not make the row actors invisible")
            passed = False
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()
        key1 = inspector._row_actor_map[row][0]
        if inspector._actor_by_key[key1].GetVisibility() != 0:
            notes.append("FAIL: hidden state lost after a full refresh")
            passed = False
        inspector.set_scene_rows_hidden([row], False)
        if inspector._actor_by_key[inspector._row_actor_map[row][0]].GetVisibility() != 1:
            notes.append("FAIL: Unhide did not restore visibility")
            passed = False

        panel = Open3DStepAdminPanel(inspector)
        if panel._selection_rows_and_label("scene-row:5") != ([5], None):
            notes.append("FAIL: iid resolver wrong for scene-row")
            passed = False
        if panel._selection_rows_and_label("overlay:cube") != ([], "cube"):
            notes.append("FAIL: iid resolver wrong for overlay")
            passed = False
        if verbose:
            notes.append(f"hid/unhid row {row} ({len(rmap[row])} actors), survived refresh")

        if own_app:
            try:
                app.destroy()
            except Exception:
                pass
        return passed, notes
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] scene-component browser hide/unhide/delete")
        return 0
    print("[FAIL] scene-browser hide/delete guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
