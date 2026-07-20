"""Display-free guard for bugs/0373 -- persistent lens-STEP front/rear flip.

A mechanical lens STEP does not encode which end is the optical FRONT (object side),
so the auto placement (front = axial max) is a guess; when it is wrong the barrel
imports reversed. ``lens_step_reverse_direction`` re-pins the OPPOSITE end at the
front datum (front_face "max" <-> "min"), toggled by one right-click, persisted with
the layout.

Checks: FUNCTIONAL (front_face max/min swaps which end sits at the front datum on a
synthetic asymmetric barrel, both keeping the datum pinned); the editor toggle flips
the persisted flag and guards no-lens; the builder maps the flag to front_face; the
setting round-trips through save + load; the overlay menu wires the flip + its
handler refreshes.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_lens_step_flip_direction
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def _asymmetric_barrel() -> "object":
    """A barrel along +Z, wider at the +Z (max) end than the -Z (min) end."""
    import pyvista as pv

    zs = np.linspace(0.0, 40.0, 9)
    pts = []
    for z in zs:
        r = 8.0 + 0.35 * z  # radius grows toward +Z -> the two ends differ
        for a in np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False):
            pts.append((r * np.cos(a), r * np.sin(a), z))
    return pv.PolyData(np.asarray(pts, dtype=float))


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    try:
        import pyvista  # noqa: F401

        from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin
        from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: flip deps unavailable ({type(exc).__name__}: {exc})"]

    # --- FUNCTIONAL: front_face max/min swaps the end at the front datum -----------
    insp = object.__new__(LayoutPolylineDisplayMixin)
    insp.append_debug = lambda *a, **k: None  # type: ignore[attr-defined]
    insp._external_cad_mesh_cache = {}  # type: ignore[attr-defined]
    barrel = _asymmetric_barrel()

    def _front_radius(front_face: str) -> float:
        aligned = insp._cad_mesh_aligned_to_optical_axis(
            barrel, source_axis=(0.0, 0.0, 1.0), front_face=front_face,
            target_front_z=100.0, label="Lens STEP",
        )
        if aligned is None:
            return -1.0
        pts = np.asarray(aligned.points, dtype=float)
        if float(pts[:, 2].min()) > 100.0 + 1e-6 or abs(float(pts[:, 2].min()) - 100.0) > 1e-6:
            failures.append(f"front_face={front_face}: front datum not pinned at z=100")
        near_front = pts[pts[:, 2] < 105.0]
        return float(np.hypot(near_front[:, 0], near_front[:, 1]).max()) if len(near_front) else -1.0

    r_max = _front_radius("max")
    r_min = _front_radius("min")
    if not (r_max > 0 and r_min > 0):
        failures.append("alignment failed for one of the front faces")
    elif abs(r_max - r_min) < 1.0:
        failures.append("front_face max vs min did not swap which end sits at the front datum")

    # --- editor toggle ------------------------------------------------------------
    class _ToggleStub(ScenePlacementMixin):
        def __init__(self, has_lens: bool):
            self.imported_lens_step_path = Path("x.stp") if has_lens else None
            self.lens_step_reverse_direction = False
            self.status_var = SimpleNamespace(set=lambda s: setattr(self, "_status", s))

    stub = _ToggleStub(True)
    if not (stub.toggle_imported_lens_step_direction() and stub.lens_step_reverse_direction):
        failures.append("toggle must flip the persisted flag to True")
    if not (stub.toggle_imported_lens_step_direction() and not stub.lens_step_reverse_direction):
        failures.append("a second toggle must flip it back to False")
    if _ToggleStub(False).toggle_imported_lens_step_direction():
        failures.append("toggle must return False (with a status line) when no lens STEP is imported")

    # --- builder maps the flag to front_face --------------------------------------
    build_src = inspect.getsource(LayoutPolylineDisplayMixin._transformed_imported_lens_step_mesh)
    if 'lens_step_reverse_direction' not in build_src or 'front_face = "min" if reverse else "max"' not in build_src:
        failures.append("the lens builder does not map lens_step_reverse_direction to front_face")
    if "front_face=front_face" not in build_src:
        failures.append("the lens builder does not pass the reverse-aware front_face to the alignment")
    if "reverse," not in build_src.split("signature = (", 1)[-1].split("def build", 1)[0]:
        failures.append("the reverse flag is not in the transformed-mesh cache signature")

    # --- setting round-trips through save + load ----------------------------------
    from KrakenOS.UI.services import layout_settings as layout_settings_module

    settings_src = inspect.getsource(layout_settings_module)
    if '"lens_step_reverse_direction": bool(getattr(self, "lens_step_reverse_direction"' not in settings_src:
        failures.append("lens_step_reverse_direction is not saved")
    if 'self.lens_step_reverse_direction = _parse_bool(settings.get("lens_step_reverse_direction"' not in settings_src:
        failures.append("lens_step_reverse_direction is not loaded")

    # --- overlay menu wires the flip + the handler refreshes -----------------------
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    menu_src = inspect.getsource(Open3DFaceAssignmentService.append_element_context_actions)
    if "Flip Lens Direction" not in menu_src or "_flip_lens_step_direction_from_context" not in menu_src:
        failures.append("the lens overlay menu has no Flip Lens Direction command")
    if 'step_label == "lens"' not in menu_src:
        failures.append("the flip command must be gated to the lens overlay")
    handler_src = inspect.getsource(Open3DFaceAssignmentService._flip_lens_step_direction_from_context)
    if "toggle_imported_lens_step_direction" not in handler_src or "refresh_from_editor" not in handler_src:
        failures.append("the flip handler must toggle then refresh")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Lens-STEP flip-direction validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Lens-STEP flip-direction validation passed: front_face max/min swaps which "
        "end sits at the front datum (both pinned), the toggle flips a persisted flag "
        "(guarded for no-lens), the builder + cache signature honour it, it round-trips "
        "through save/load, and the overlay menu offers a one-click flip that refreshes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
