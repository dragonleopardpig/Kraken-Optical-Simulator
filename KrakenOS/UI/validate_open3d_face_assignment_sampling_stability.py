"""Validate that Open 3D face assignment preserves the displayed ray sample."""

from __future__ import annotations

import argparse
import inspect
from pathlib import Path
from types import MethodType

import numpy as np

from KrakenOS.UI.layout_editor import (
    Kraken3DInspector,
    KrakenLayoutEditor,
    _raykeeper_has_non_primary_branch_paths,
)
from KrakenOS.UI.panels.main_optical_solid_face_roles_dialog import MainOpticalSolidFaceRolesDialog
from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRISM_42779_STEP = PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step"


class _StatusVar:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: object) -> None:
        self.value = str(value)

    def get(self) -> str:
        return self.value


class _FakeEditor:
    def __init__(self) -> None:
        self.status_var = _StatusVar()
        self._active_preview_sampling_mode = "world_sections"
        self.build_sampling_modes: list[str | None] = []
        self.build_update_states: list[bool] = []
        self.build_include_live_step_overlays: list[bool] = []
        self.preview_3d_calls = 0
        self.debug_messages: list[str] = []
        self.current_trace = None
        self._open3d_trace_refresh_service_instance = Open3DTraceRefreshService(self)

    def _open3d_trace_refresh_service(self) -> Open3DTraceRefreshService:
        return self._open3d_trace_refresh_service_instance

    def _current_preview_scene_trace(self):
        return self.current_trace

    def _preview_3d_sampling_mode(self) -> str:
        self.preview_3d_calls += 1
        return "source_cone_world"

    def _build_preview_system_rays_bundle(
        self,
        *,
        sampling_mode: str | None = None,
        update_state: bool = True,
        include_live_step_overlays: bool = False,
    ):
        self.build_sampling_modes.append(sampling_mode)
        self.build_update_states.append(bool(update_state))
        self.build_include_live_step_overlays.append(bool(include_live_step_overlays))
        self._active_preview_sampling_mode = str(sampling_mode or "")
        return object(), object(), object()

    def _preview_render_row_names(self, scene_bundle) -> list[str]:
        return []

    def append_debug(self, message: object) -> None:
        self.debug_messages.append(str(message))


def _inspector_with_fake_editor(editor: _FakeEditor) -> Kraken3DInspector:
    inspector = object.__new__(Kraken3DInspector)
    inspector.editor = editor
    inspector.status_var = _StatusVar()
    inspector._last_refresh_sampling_mode = "world_sections"
    inspector.refresh_calls = []

    def refresh_scene(self, system, rays, row_names, *, scene_bundle=None, reset_camera=False):
        self.refresh_calls.append(
            {
                "system": system,
                "rays": rays,
                "row_names": list(row_names),
                "scene_bundle": scene_bundle,
                "reset_camera": bool(reset_camera),
            }
        )

    inspector.refresh_scene = MethodType(refresh_scene, inspector)
    return inspector


def _validate_forced_refresh_preserves_active_mode() -> None:
    editor = _FakeEditor()
    inspector = _inspector_with_fake_editor(editor)
    Kraken3DInspector.refresh_from_editor(inspector, force_retrace=True)
    if editor.build_sampling_modes != ["world_sections"]:
        raise AssertionError(
            "Forced Open 3D edit refresh should reuse the sampling mode already on screen; "
            f"got {editor.build_sampling_modes!r}."
        )
    if editor.preview_3d_calls:
        raise AssertionError("Preserved edit refresh should not recompute the default 3D sampling mode.")
    if inspector._last_refresh_sampling_mode != "world_sections":
        raise AssertionError(f"Inspector did not remember preserved mode: {inspector._last_refresh_sampling_mode!r}")


def _validate_explicit_mode_still_wins() -> None:
    editor = _FakeEditor()
    inspector = _inspector_with_fake_editor(editor)
    Kraken3DInspector.refresh_from_editor(inspector, sampling_mode="source_cone_world", force_retrace=True)
    if editor.build_sampling_modes != ["source_cone_world"]:
        raise AssertionError(f"Explicit Open 3D sampling mode should win, got {editor.build_sampling_modes!r}.")


def _validate_missing_mode_falls_back_to_3d_default() -> None:
    editor = _FakeEditor()
    editor._active_preview_sampling_mode = ""
    inspector = _inspector_with_fake_editor(editor)
    inspector._last_refresh_sampling_mode = None
    Kraken3DInspector.refresh_from_editor(inspector, force_retrace=True)
    if editor.build_sampling_modes != ["source_cone_world"]:
        raise AssertionError(f"Missing mode should fall back to Open 3D default, got {editor.build_sampling_modes!r}.")
    if editor.preview_3d_calls != 1:
        raise AssertionError(f"Expected one 3D sampling-mode fallback call, got {editor.preview_3d_calls}.")


def _validate_current_trace_records_active_mode() -> None:
    editor = _FakeEditor()
    editor._active_preview_sampling_mode = "world_envelope"
    editor.current_trace = (object(), object(), object())
    inspector = _inspector_with_fake_editor(editor)
    inspector._last_refresh_sampling_mode = None
    Kraken3DInspector.refresh_from_editor(inspector)
    if editor.build_sampling_modes:
        raise AssertionError(f"Current SceneBundle refresh should not rebuild, got {editor.build_sampling_modes!r}.")
    if inspector._last_refresh_sampling_mode != "world_envelope":
        raise AssertionError("Current SceneBundle refresh did not remember the active sampling mode.")


def _validate_trace_now_preserves_active_mode_with_transient_step_support() -> None:
    editor = _FakeEditor()
    inspector = _inspector_with_fake_editor(editor)
    result = editor._open3d_trace_refresh_service().build_trace_now_preview(inspector)
    if result.sampling_mode != "world_sections":
        raise AssertionError(f"Trace Now did not report preserved mode: {result.sampling_mode!r}.")
    if editor.build_sampling_modes != ["world_sections"]:
        raise AssertionError(
            "Trace Now should retrace the sampling mode already shown in Open 3D; "
            f"got {editor.build_sampling_modes!r}."
        )
    if editor.build_update_states != [False]:
        raise AssertionError(f"Trace Now should not overwrite the 2D preview state, got {editor.build_update_states!r}.")
    if editor.build_include_live_step_overlays != [True]:
        raise AssertionError("Trace Now should still include transient optical STEP overlays when present.")
    if editor.preview_3d_calls:
        raise AssertionError("Trace Now should not fall back to the default 3D sampler when an active mode exists.")


def _validate_face_assignment_handlers_capture_mode_before_mutation() -> None:
    assign_source = inspect.getsource(Open3DFaceAssignmentService._assign_row_face_function_from_context)
    promote_assign_source = inspect.getsource(Open3DFaceAssignmentService._promote_step_and_assign_face_function)
    for name, source in (
        ("row face assignment", assign_source),
        ("STEP promote-and-assign", promote_assign_source),
    ):
        if "refresh_sampling_mode = self._active_refresh_sampling_mode()" not in source:
            raise AssertionError(f"{name} does not capture the displayed sampling mode before metadata mutation.")
        if "sampling_mode=refresh_sampling_mode" not in source:
            raise AssertionError(f"{name} does not pass the captured sampling mode into the forced retrace.")


def _validate_done_2d_and_close_preserve_open3d_sampling() -> None:
    finish_source = inspect.getsource(Kraken3DInspector.finish_stl_placement)
    close_source = inspect.getsource(Kraken3DInspector._on_close)
    refresh_source = inspect.getsource(KrakenLayoutEditor.refresh_plot)
    if "sampling_mode: str | None = None" not in refresh_source:
        raise AssertionError("refresh_plot does not accept a caller-preserved sampling mode.")
    if "sampling_mode=self._active_refresh_sampling_mode()" not in finish_source:
        raise AssertionError("Done 2D does not pass the active Open 3D sampling mode into refresh_plot.")
    if "refresh_sampling_mode = self._active_refresh_sampling_mode()" not in close_source:
        raise AssertionError("Open 3D close does not capture the active sampling mode before destroying the inspector.")
    if "sampling_mode=refresh_sampling_mode" not in close_source:
        raise AssertionError("Open 3D close does not pass the captured sampling mode into deferred refresh_plot.")


def _validate_focus_and_vtk_teardown_are_guarded() -> None:
    editor_source = inspect.getsource(KrakenLayoutEditor)
    close_source = inspect.getsource(Kraken3DInspector._on_close)
    destroy_source = inspect.getsource(Kraken3DInspector._destroy_vtk_render_window)
    if "def _safe_focus_get" not in editor_source or "except (KeyError, tk.TclError)" not in editor_source:
        raise AssertionError("Global copy/paste focus lookup is not guarded against transient Tk dialog widgets.")
    if "_destroy_vtk_render_window()" not in close_source:
        raise AssertionError("Open 3D close does not finalize the VTK render window before Tk destroys the widget.")
    if "render_window.Finalize()" not in destroy_source:
        raise AssertionError("VTK teardown helper does not finalize the render window.")


def _validate_face_role_save_forces_stale_trace_rebuild() -> None:
    face_editor_source = inspect.getsource(MainOpticalSolidFaceRolesDialog._open_optical_solid_faces_for_row)
    refresh_source = inspect.getsource(KrakenLayoutEditor._refresh_open_3d_views)
    assign_source = inspect.getsource(KrakenLayoutEditor.assign_optical_solid_face_function)
    if "_refresh_open_3d_views(force_retrace=True)" not in face_editor_source:
        raise AssertionError("CAD/STL face-role Save Roles does not force an open Open 3D inspector to retrace.")
    if (
        "reason_text = str(reason or 'Face Editor')" not in face_editor_source
        or "_invalidate_optical_solid_face_assignment_trace(row_index, reason_text)" not in face_editor_source
    ):
        raise AssertionError("CAD/STL face-role Save Roles does not clear stale traced scene state.")
    if "def persist_face_editor_metadata" not in face_editor_source:
        raise AssertionError("CAD/STL face-role editor has no immediate row-metadata persistence helper.")
    if "persist_face_editor_metadata(f'{face_id} {function_display}')" not in face_editor_source:
        raise AssertionError("CAD/STL face-role combobox edits are not saved immediately to row metadata.")
    if "entry_widget.bind('<FocusOut>', auto_apply_selected_face_identity" not in face_editor_source:
        raise AssertionError("CAD/STL face-role text fields do not save on focus-out.")
    if "_invalidate_optical_solid_face_assignment_trace(row_index, face_id, function)" not in assign_source:
        raise AssertionError("Direct CAD/STL face assignment does not clear stale traced scene state.")
    if "force_retrace: bool = False" not in refresh_source or "refresh_from_editor(force_retrace=force_retrace)" not in refresh_source:
        raise AssertionError("Open 3D view refresh helper cannot propagate forced retrace requests.")


def _launch_signature(scene_bundle) -> tuple[tuple[float, ...], ...]:
    signature: list[tuple[float, ...]] = []
    for path in list(getattr(scene_bundle, "ray_paths", []) or []):
        points = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            continue
        origin = points[0, :3]
        direction = points[1, :3] - points[0, :3]
        norm = float(np.linalg.norm(direction))
        if not np.isfinite(norm) or norm <= 1e-12:
            continue
        direction = direction / norm
        signature.append(tuple(float(value) for value in np.round(np.concatenate((origin, direction)), 8)))
    return tuple(signature)


def _validate_world_envelope_survives_off_axis_step_promotion() -> None:
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected STEP fixture: {PRISM_42779_STEP}")
    app = KrakenLayoutEditor(headless=True)
    try:
        _system, _rays, before_bundle = app._build_preview_system_rays_bundle(
            sampling_mode="world_envelope",
            update_state=False,
        )
        before_signature = _launch_signature(before_bundle)
        if len(before_signature) < 2:
            raise AssertionError(f"Expected a multi-ray world envelope before promotion, got {len(before_signature)}.")

        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 0.0
        app.optical_step_rotation_y_deg = 90.0
        app.optical_step_rotation_z_deg = 180.0
        app.optical_step_placement_offset_xyz = (0.0, 42.217029364814806, 37.30257804865933)
        app.select_step_component("optical")
        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical",
            insert_at=1,
            open_face_editor=False,
            clear_overlay=True,
            refresh_open_3d=False,
        )
        if promoted is None:
            raise AssertionError("Off-axis STEP promotion returned no row.")
        _system, _rays, after_bundle = app._build_preview_system_rays_bundle(
            sampling_mode="world_envelope",
            update_state=False,
        )
        after_signature = _launch_signature(after_bundle)
        if len(after_signature) != len(before_signature):
            raise AssertionError(
                "World-envelope launch count changed after off-axis STEP promotion: "
                f"before={len(before_signature)}, after={len(after_signature)}."
            )
        if after_signature != before_signature:
            raise AssertionError("World-envelope launch origins/directions changed after off-axis STEP promotion.")
    finally:
        app.destroy()


def _validate_world_envelope_keeps_splitter_branch_bundles() -> None:
    class FakeRays:
        CC = [object(), object(), object()]
        BRANCH_PATH = [
            np.asarray("primary"),
            np.asarray("S1 split reflect"),
            np.asarray("S1 split transmit"),
        ]

    if not _raykeeper_has_non_primary_branch_paths(FakeRays(), expected_launch_count=1):
        raise AssertionError("World-envelope branch detection missed non-primary splitter branch paths.")

    class ExpandedRays:
        CC = [object(), object(), object()]
        BRANCH_PATH: list[object] = []

    if not _raykeeper_has_non_primary_branch_paths(ExpandedRays(), expected_launch_count=1):
        raise AssertionError("World-envelope branch detection missed expanded branch ray count.")
    if _raykeeper_has_non_primary_branch_paths(ExpandedRays(), expected_launch_count=3):
        raise AssertionError("World-envelope branch detection should not flag one output per launch.")

    trace_source = inspect.getsource(KrakenLayoutEditor._trace_selected_through_envelope)
    if "_raykeeper_has_non_primary_branch_paths(candidate_rays" not in trace_source:
        raise AssertionError("World-envelope through-ray selector is not branch-aware.")
    if "kept full" not in trace_source or "launch bundle" not in trace_source:
        raise AssertionError("World-envelope branch path does not preserve the full launch bundle.")


def _run_focused_checks() -> None:
    _validate_forced_refresh_preserves_active_mode()
    _validate_explicit_mode_still_wins()
    _validate_missing_mode_falls_back_to_3d_default()
    _validate_current_trace_records_active_mode()
    _validate_trace_now_preserves_active_mode_with_transient_step_support()
    _validate_face_assignment_handlers_capture_mode_before_mutation()
    _validate_done_2d_and_close_preserve_open3d_sampling()
    _validate_focus_and_vtk_teardown_are_guarded()
    _validate_face_role_save_forces_stale_trace_rebuild()
    _validate_world_envelope_keeps_splitter_branch_bundles()


def _run_full_checks() -> None:
    _run_focused_checks()
    _validate_world_envelope_survives_off_axis_step_promotion()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--focused",
        action="store_true",
        help="Run only fixture-free sampling contract checks.",
    )
    args = parser.parse_args(argv)
    if args.focused:
        _run_focused_checks()
        print("Focused Open 3D face assignment sampling stability validation passed.")
        return 0
    _run_full_checks()
    print("Open 3D face assignment sampling stability validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
