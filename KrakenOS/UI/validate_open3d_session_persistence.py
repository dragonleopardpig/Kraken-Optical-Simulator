"""Validate full-scene Save/Open for the Open 3D inspector.

The user asked: *"When clicked save, please save all visible and invisible items
in the layout. Must exactly reproduce when re-opened."* and *"also add a Save As
in 3D."*

The layout ``.py`` already persists the heavy state (STEP-overlay poses, promoted
solids, scene sources, glue, thickness dims, dimension-anchor overrides). What it
does NOT carry is the inspector-only 3D-session state:

* manual measurements (``_measure_segments`` / ``_hidden_measure_segments``),
* per-item hidden state (``_hidden_scene_rows`` / ``_hidden_step_labels`` /
  ``_hidden_source_ids``),
* the scene overlay toggles (rays, references, detectors, the field-aberration
  overlays, the illumination overlays),
* the camera pose.

The fix writes those to a ``<layout>.open3d.json`` sidecar next to the layout on
Save / Save As, and restores them (once per layout file) when the 3D view opens
that layout -- the imminent rebuild re-draws the measurements and re-applies the
hidden sets from the restored state, and the camera is applied after the rebuild.

Display-free: this binds the real inspector methods to a fake ``self`` (fake Tk
vars / camera / renderer -- no Tk, no render) and proves a genuine JSON round-trip
through a temp sidecar file, plus source asserts on the save/restore wiring.

Exposes ``run_checks() -> (passed, failures)`` so it doubles as a penta phase.
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

from KrakenOS.UI.open3d_inspector import Kraken3DInspector


class _FakeVar:
    def __init__(self, value: bool) -> None:
        self._v = bool(value)

    def get(self) -> bool:
        return self._v

    def set(self, value) -> None:
        self._v = bool(value)


class _FakeCamera:
    def __init__(self) -> None:
        self._pos = (1.0, 2.0, 3.0)
        self._foc = (4.0, 5.0, 6.0)
        self._up = (0.0, 1.0, 0.0)
        self._scale = 42.5
        self._par = True

    def GetPosition(self):
        return self._pos

    def GetFocalPoint(self):
        return self._foc

    def GetViewUp(self):
        return self._up

    def GetParallelScale(self):
        return self._scale

    def GetParallelProjection(self):
        return self._par

    def SetPosition(self, x, y, z):
        self._pos = (float(x), float(y), float(z))

    def SetFocalPoint(self, x, y, z):
        self._foc = (float(x), float(y), float(z))

    def SetViewUp(self, x, y, z):
        self._up = (float(x), float(y), float(z))

    def SetParallelScale(self, s):
        self._scale = float(s)

    def SetParallelProjection(self, b):
        self._par = bool(b)


class _FakeRenderer:
    def __init__(self, camera) -> None:
        self._camera = camera

    def GetActiveCamera(self):
        return self._camera

    def ResetCameraClippingRange(self) -> None:
        pass


class _FakeEditor:
    def __init__(self, layout_path=None) -> None:
        self.current_layout_file = layout_path

    def append_debug(self, msg) -> None:
        pass


class _Fake:
    """Minimal stand-in carrying only what the session helpers read/write."""

    _SESSION_TOGGLE_VAR_NAMES = Kraken3DInspector._SESSION_TOGGLE_VAR_NAMES
    _open3d_session_sidecar_path = Kraken3DInspector._open3d_session_sidecar_path
    _capture_open3d_session_camera = Kraken3DInspector._capture_open3d_session_camera
    _open3d_session_state_dict = Kraken3DInspector._open3d_session_state_dict
    _write_open3d_session_sidecar = Kraken3DInspector._write_open3d_session_sidecar
    _maybe_restore_open3d_session_state = Kraken3DInspector._maybe_restore_open3d_session_state
    _apply_open3d_session_state = Kraken3DInspector._apply_open3d_session_state
    _coerce_int_set = staticmethod(Kraken3DInspector._coerce_int_set)
    _apply_pending_session_camera = Kraken3DInspector._apply_pending_session_camera

    def __init__(self, *, editor, renderer=None) -> None:
        self.editor = editor
        self._renderer = renderer
        self._session_restored_for_path = None
        self._pending_session_camera = None
        self._rendered = False
        self._measure_segments = []
        self._hidden_measure_segments = set()
        self._hidden_scene_rows = set()
        self._hidden_step_labels = set()
        self._hidden_source_ids = set()
        for name in self._SESSION_TOGGLE_VAR_NAMES:
            setattr(self, name, _FakeVar(False))

    def render(self) -> None:
        self._rendered = True


def _sample_segments():
    # Same shape _record_measure_point builds: p0/r0/dz0/n0 + p1/r1/dz1 + id, and
    # the user-nudged lane standoff (seg["offset"]).
    return [
        {
            "p0": [10.0, 0.0, 0.0], "r0": 2, "dz0": 0.0, "n0": [0.0, 0.0, 1.0],
            "p1": [175.0, 0.0, 0.0], "r1": 5, "dz1": 0.0, "id": 0, "offset": 47.5,
        },
        {
            "p0": [0.0, 0.0, 0.0], "r0": 0, "dz0": 0.0, "n0": None,
            "p1": [0.0, 12.0, 0.0], "r1": 0, "dz1": 0.0, "id": 1,
        },
    ]


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        layout_path = Path(tmp) / "scene_layout.py"
        sidecar_path = layout_path.with_suffix(".open3d.json")

        # --- 1) a saved scene -> a JSON sidecar next to the layout ---------------
        src = _Fake(editor=_FakeEditor(layout_path), renderer=_FakeRenderer(_FakeCamera()))
        src._measure_segments = _sample_segments()
        src._hidden_measure_segments = {1}
        src._hidden_scene_rows = {3, 7}
        src._hidden_step_labels = {"lens", "camera"}
        src._hidden_source_ids = {"source:zemax-rayfile:1"}
        src.show_rays_var.set(False)               # a non-default overlay toggle
        src.show_distortion_grid_var.set(True)
        src.show_source_illumination_var.set(True)

        src._write_open3d_session_sidecar(layout_path)
        if not sidecar_path.exists():
            failures.append("Save did not write the <layout>.open3d.json sidecar")
            return (not failures), failures
        try:
            on_disk = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(f"sidecar is not valid JSON: {exc}")
            return (not failures), failures
        if not isinstance(on_disk, dict) or "measure_segments" not in on_disk:
            failures.append("sidecar JSON is missing the measure_segments block")

        # --- 2) re-open the layout -> the inspector reproduces the scene ---------
        dest_cam = _FakeCamera()
        dest = _Fake(editor=_FakeEditor(layout_path), renderer=_FakeRenderer(dest_cam))
        dest._maybe_restore_open3d_session_state()

        if [dict(s) for s in dest._measure_segments] != _sample_segments():
            failures.append("measurements did not round-trip through the sidecar")
        if dest._hidden_measure_segments != {1}:
            failures.append("hidden measurement set did not round-trip")
        if dest._hidden_scene_rows != {3, 7}:
            failures.append("hidden scene rows did not round-trip")
        if dest._hidden_step_labels != {"lens", "camera"}:
            failures.append("hidden STEP labels did not round-trip")
        if dest._hidden_source_ids != {"source:zemax-rayfile:1"}:
            failures.append("hidden source ids did not round-trip")
        if dest.show_rays_var.get() is not False:
            failures.append("show_rays toggle did not round-trip (should be OFF)")
        if dest.show_distortion_grid_var.get() is not True:
            failures.append("distortion-grid toggle did not round-trip (should be ON)")
        if dest.show_source_illumination_var.get() is not True:
            failures.append("source-illumination toggle did not round-trip (should be ON)")

        # camera is buffered, then applied after the rebuild (via refresh_scene).
        if not isinstance(dest._pending_session_camera, dict):
            failures.append("camera pose was not buffered for post-rebuild apply")
        dest._apply_pending_session_camera()
        if dest_cam.GetPosition() != (1.0, 2.0, 3.0):
            failures.append("restored camera position was not applied")
        if dest_cam.GetFocalPoint() != (4.0, 5.0, 6.0):
            failures.append("restored camera focal point was not applied")
        if abs(float(dest_cam.GetParallelScale()) - 42.5) > 1e-9:
            failures.append("restored camera parallel scale was not applied")
        if dest._pending_session_camera is not None:
            failures.append("camera buffer was not cleared after apply (would re-apply every refresh)")
        if not dest._rendered:
            failures.append("camera apply did not trigger a render")

        # --- 3) restore is guarded: a second pass never clobbers live edits ------
        dest._measure_segments = []            # simulate the user clearing a measurement
        dest._hidden_scene_rows = set()
        dest._maybe_restore_open3d_session_state()
        if dest._measure_segments != [] or dest._hidden_scene_rows != set():
            failures.append("restore re-fired for the same layout and clobbered live edits")

        # --- 4) a layout with no sidecar -> restore is a harmless no-op ----------
        empty_layout = Path(tmp) / "no_sidecar.py"
        fresh = _Fake(editor=_FakeEditor(empty_layout))
        fresh._maybe_restore_open3d_session_state()
        if fresh._measure_segments != [] or fresh._pending_session_camera is not None:
            failures.append("restore fabricated state when no sidecar exists")
        if fresh._session_restored_for_path != str(empty_layout):
            failures.append("restore did not mark a sidecar-less layout attempted (would retry every refresh)")

    # --- 5) wiring (source asserts) ---------------------------------------------
    ref_src = inspect.getsource(Kraken3DInspector.refresh_from_editor)
    if "_maybe_restore_open3d_session_state" not in ref_src:
        failures.append("refresh_from_editor does not restore the session before the rebuild")
    scene_src = inspect.getsource(Kraken3DInspector.refresh_scene)
    if "_apply_pending_session_camera" not in scene_src:
        failures.append("refresh_scene does not apply the restored camera after the rebuild")
    save_src = inspect.getsource(Kraken3DInspector.save_layout)
    if "_write_open3d_session_sidecar" not in save_src:
        failures.append("save_layout does not write the 3D-session sidecar")
    try:
        saveas_src = inspect.getsource(Kraken3DInspector.save_layout_as)
    except Exception:
        saveas_src = ""
    if "save_layout_as" not in saveas_src or "_write_open3d_session_sidecar" not in saveas_src:
        failures.append("inspector save_layout_as is missing or does not write the sidecar")

    import KrakenOS.UI.panels.open3d_top_controls as topc

    tc_src = inspect.getsource(topc)
    if "save_layout_as" not in tc_src or "Save As" not in tc_src:
        failures.append("the 3D toolbar has no 'Save As' button wired to save_layout_as")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Open 3D session-persistence validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Open 3D session-persistence validation passed: Save / Save As write a "
        "<layout>.open3d.json sidecar carrying measurements, hidden items, overlay "
        "toggles and the camera; re-opening the layout restores them (once per file) "
        "so the whole 3D scene -- not just the optical prescription -- reproduces."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
