"""Guard: the imported-solid resize is wired into the overlay mesh pipeline.

Builds on ``validate_open3d_solid_resize`` (the pure-geometry kernel) and checks
that the editor-side overlay plumbing applies it:

* ``ScenePlacementMixin._set/_get/_signature_step_resize`` store and report a
  per-axis target-extents spec (None clears it; unknown labels are ignored).
* ``_apply_step_overlay_resize`` scales a freshly loaded base mesh to the target
  extents in the native frame, honours an anchored (fixed-face) grow, and is a
  strict no-op (same object) when there is no spec.
* SOURCE CONTRACT: every per-label builder in ``LayoutPolylineDisplayMixin``
  applies the resize after load and folds the resize signature into its cache
  key (so a resize invalidates the memoised overlay mesh).
* ``_step_overlay_resize_axes`` detects the coupling axes off the original B-rep
  (SKIP if the vendor STEP / OCC is unavailable).

Display-free (needs pyvista for the box mesh, no VTK render).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_solid_resize_overlay

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

_VENDOR_STEP = Path("attachment/prisms/Beam_Splitter/32704/step_32704.step")


class _FakeEditor:
    """Minimal stand-in exposing only the hooks the resize methods touch."""

    def __init__(self) -> None:
        self._live_step_overlay_trace_plan_cache: dict = {}
        self._vendor_path = _VENDOR_STEP if _VENDOR_STEP.exists() else None

    # cache-invalidation hooks (no-ops here)
    def _invalidate_step_overlay_face_metadata_cache(self, _label: str) -> None:
        pass

    def _invalidate_preview_scene_trace(self) -> None:
        pass

    def append_debug(self, *_a, **_k) -> None:
        pass

    # used only by _step_overlay_resize_axes
    def _step_path_for_label(self, label: str):
        return self._vendor_path if str(label).strip().lower() == "optical" else None


def _bind():
    """Return the ScenePlacementMixin resize methods bound to a fake editor."""
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    editor = _FakeEditor()
    # borrow the unbound mixin methods onto the fake instance
    for name in (
        "_set_step_resize_for_label",
        "_step_resize_for_label",
        "_step_resize_signature",
        "_apply_step_overlay_resize",
        "_step_overlay_resize_axes",
    ):
        setattr(editor, name, getattr(ScenePlacementMixin, name).__get__(editor, _FakeEditor))
    return editor


def _cube(size_xyz=(50.0, 50.0, 50.0), center=(0.0, 0.0, 0.0)):
    import pyvista as pv

    sx, sy, sz = size_xyz
    return pv.Cube(center=center, x_length=sx, y_length=sy, z_length=sz)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.services import open3d_solid_resize as R

    editor = _bind()

    # --- W1. set / get round-trip + clear + unknown label --------------------
    editor._set_step_resize_for_label("optical", (55.0, 55.0, 78.0), coupled=True)
    spec = editor._step_resize_for_label("optical")
    ok(spec is not None and tuple(spec["target_extents"]) == (55.0, 55.0, 78.0) and spec["coupled"],
       "W1a: set/get round-trips the target extents + coupled flag")
    editor._set_step_resize_for_label("optical", None)
    ok(editor._step_resize_for_label("optical") is None, "W1b: passing None clears the resize spec")
    editor._set_step_resize_for_label("not-a-label", (10.0, 10.0, 10.0))
    ok(editor._step_resize_for_label("not-a-label") is None, "W1c: unknown labels are ignored")

    # --- W2. signature reflects the spec (cache key) -------------------------
    ok(editor._step_resize_signature("optical") is None, "W2a: no spec -> no signature")
    editor._set_step_resize_for_label("optical", (55.0, 55.0, 78.0))
    sig1 = editor._step_resize_signature("optical")
    editor._set_step_resize_for_label("optical", (60.0, 60.0, 78.0))
    sig2 = editor._step_resize_signature("optical")
    ok(sig1 is not None and sig2 is not None and sig1 != sig2,
       "W2b: changing the target changes the cache signature")

    # --- W3. apply scales a base mesh to the target extents ------------------
    editor._set_step_resize_for_label("optical", (55.0, 55.0, 78.0), coupled=True)
    resized = editor._apply_step_overlay_resize(_cube(), "optical")
    ext = R.extents_of(np.asarray(resized.points, dtype=float))
    ok(np.allclose(ext, [55.0, 55.0, 78.0], atol=1e-6),
       "W3: apply scales a 50^3 base mesh to 55 x 55 x 78")

    # --- W4. no spec is a strict no-op (same object) -------------------------
    editor._set_step_resize_for_label("optical", None)
    base = _cube()
    ok(editor._apply_step_overlay_resize(base, "optical") is base,
       "W4: no resize spec returns the same mesh object (no-op)")

    # --- W5. anchored grow keeps the fixed face put -------------------------
    editor._set_step_resize_for_label("optical", (None, None, 78.0), anchor_axis=2, anchor_at_max=False)
    grown = editor._apply_step_overlay_resize(_cube(center=(0.0, 0.0, 25.0)), "optical")  # z in [0,50]
    pts = np.asarray(grown.points, dtype=float)
    ok(np.isclose(pts[:, 2].min(), 0.0, atol=1e-6) and np.isclose(R.extents_of(pts)[2], 78.0, atol=1e-6),
       "W5: anchored grow keeps the fixed (min-Z) face and only depth changes")

    # --- W6. coupled target keeps the 45-deg coating (kernel parity) --------
    axes = R.detect_coupling_from_faces([((0.7071, 0.7071, 0.0), 3535.5)])
    scales = R.coupled_scales(axes, (50.0, 50.0, 50.0), cross_section=55.0, depth=78.0)
    ok(R.is_coating_preserved((0.7071, 0.7071, 0.0), scales),
       "W6: a coupled (square) target keeps the coating at 45 deg")

    # --- W7. SOURCE CONTRACT: every builder applies resize + signs the key ---
    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin

    builders = {
        "lens": LayoutPolylineDisplayMixin._transformed_imported_lens_step_mesh,
        "optical": LayoutPolylineDisplayMixin._transformed_imported_optical_step_mesh,
        "camera": LayoutPolylineDisplayMixin._transformed_imported_camera_step_mesh,
        "led": LayoutPolylineDisplayMixin._transformed_imported_led_step_mesh,
    }
    for label, fn in builders.items():
        src = inspect.getsource(fn)
        ok(f'_apply_step_overlay_resize(mesh, "{label}")' in src
           and f'_step_resize_signature("{label}")' in src,
           f"W7-{label}: builder applies resize + folds the resize signature into its cache key")

    # --- W8. coupling detection off the original B-rep (SKIP if no file) -----
    if _VENDOR_STEP.exists():
        try:
            vendor_axes = editor._step_overlay_resize_axes("optical")
            ok(vendor_axes is not None and vendor_axes.free_axis == 2 and vendor_axes.coupled_axes == (0, 1),
               "W8: _step_overlay_resize_axes detects free=Z, coupled={X, Y} on the vendor part")
        except Exception as exc:  # pragma: no cover - env dependent
            skip(f"W8: vendor-file detection unavailable ({type(exc).__name__}: {exc})")
    else:
        skip("W8: vendor beam-splitter STEP not present")

    # --- W9/W10. UI wiring source contracts (heavy import -> SKIP on fail) ---
    try:
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
        from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

        menu_src = inspect.getsource(Open3DFaceAssignmentService._show_surface_function_context_menu)
        ok('"Resize Solid..."' in menu_src and "_open_step_overlay_resize_popup(" in menu_src,
           "W9: the STEP-overlay right-click menu offers 'Resize Solid...'")

        popup_src = inspect.getsource(Kraken3DInspector._open_step_overlay_resize_popup)
        ok("Cross-section (mm):" in popup_src and "Depth (mm):" in popup_src
           and "Width (mm):" in popup_src and "axes is not None" in popup_src
           and "_apply_step_overlay_resize_solve(" in popup_src,
           "W10a: popup builds coupled cross-section/depth vs free W/H/D and calls the apply")

        apply_src = inspect.getsource(Kraken3DInspector._apply_step_overlay_resize_solve)
        ok("_set_step_resize_for_label(" in apply_src
           and "_begin_history_capture" in apply_src
           and "refresh_from_editor" in apply_src,
           "W10b: apply captures history, sets the resize spec, and retraces")
    except Exception as exc:  # pragma: no cover - heavy/optional import
        skip(f"W9/W10: inspector source-contract import unavailable ({type(exc).__name__}: {exc})")

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Open 3D solid-resize overlay-wiring validation passed.")
        return 0
    print("Open 3D solid-resize overlay-wiring validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
