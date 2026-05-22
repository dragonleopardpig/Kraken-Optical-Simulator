"""Validate that Open 3D face assignment preserves the displayed ray sample."""

from __future__ import annotations

import inspect
from types import MethodType

from KrakenOS.UI.layout_editor import Kraken3DInspector


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
        self.preview_3d_calls = 0
        self.debug_messages: list[str] = []
        self.current_trace = None

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
    ):
        self.build_sampling_modes.append(sampling_mode)
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


def _validate_face_assignment_handlers_capture_mode_before_mutation() -> None:
    assign_source = inspect.getsource(Kraken3DInspector._assign_row_face_function_from_context)
    promote_assign_source = inspect.getsource(Kraken3DInspector._promote_step_and_assign_face_function)
    for name, source in (
        ("row face assignment", assign_source),
        ("STEP promote-and-assign", promote_assign_source),
    ):
        if "refresh_sampling_mode = self._active_refresh_sampling_mode()" not in source:
            raise AssertionError(f"{name} does not capture the displayed sampling mode before metadata mutation.")
        if "sampling_mode=refresh_sampling_mode" not in source:
            raise AssertionError(f"{name} does not pass the captured sampling mode into the forced retrace.")


def main() -> int:
    _validate_forced_refresh_preserves_active_mode()
    _validate_explicit_mode_still_wins()
    _validate_missing_mode_falls_back_to_3d_default()
    _validate_current_trace_records_active_mode()
    _validate_face_assignment_handlers_capture_mode_before_mutation()
    print("Open 3D face assignment sampling stability validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
