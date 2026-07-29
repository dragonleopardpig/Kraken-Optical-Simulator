"""bugs/0476 -- the camera anti-crash must see PROMOTED solids, and remove-defocus must ask it.

Flag flag_20260729_185536_867: "unhide the Camera STEP: the anti-crash algorithm not
functioning. Camera crash to RA mirror." Measured overlap on all three axes, yet no warning.

Two independent defects, guarded separately here:

1. ``camera_body_collisions`` scanned only the STEP-overlay labels ("lens", "led", "optical").
   Once a beam splitter or fold mirror is PROMOTED its overlay is gone, so on the reported
   scene -- BS row 3, RA mirror row 7, no "optical" overlay at all -- it returned [] no matter
   how deep the camera sat inside the mirror. Its own docstring promised promoted solids.

2. "Remove defocus" moves the detector, and the camera is glued to it, but its wrapper never
   ran the check. It was the only camera-moving action without one.

Display-free: a stub over the REAL mixins (so the genuine
``_promoted_solid_world_bounds`` runs, not a reimplementation) plus a source-level check that
the remove-defocus wrapper still asks. No Tk, no render window.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0476_camera_body_collision_promoted
"""
from __future__ import annotations

import inspect
from pathlib import Path


class _Mesh:
    def __init__(self, bounds):
        self.bounds = tuple(float(v) for v in bounds)


class _Row:
    def __init__(self, name, mn, mx):
        self.name = name
        self.advanced = {
            "StepOverlayPromotion": {
                "bounds_min_world": list(mn),
                "bounds_max_world": list(mx),
            }
        }


def _make_stub(camera_bounds, rows):
    """A ScenePlacementMixin + LayoutTableWorkbenchMixin instance with only the hooks
    ``camera_body_collisions`` actually touches."""
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    class _Stub(ScenePlacementMixin, LayoutTableWorkbenchMixin):
        pass

    stub = object.__new__(_Stub)
    stub.rows = list(rows)
    # Only the camera has an overlay mesh; the obstacles are PROMOTED, so their overlay
    # lookups return None -- exactly the reported scene's shape.
    stub._transformed_imported_step_mesh_for_label = (
        lambda label: _Mesh(camera_bounds) if str(label) == "camera" else None
    )
    # Force the metadata-centre fallback in _promoted_solid_world_bounds so the geometry is
    # deterministic (the live-centre path needs a rendered scene bundle).
    stub._promoted_solid_current_center = lambda row_index: None
    return stub


# The flagged geometry, verbatim from state.json of flag_20260729_185536_867.
CAMERA_BOUNDS = (194.93, 264.93, -35.0, 35.0, 6.49, 80.12)
RA_MIRROR_MIN = (193.65338401197525, -12.5, 59.397137058600165)
RA_MIRROR_MAX = (218.65338401197525, 12.5, 84.39713705860017)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        stub = _make_stub(CAMERA_BOUNDS, [_Row("Promoted RA mirror", RA_MIRROR_MIN, RA_MIRROR_MAX)])
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: collision deps unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. the reported geometry is a real 3-axis overlap -------------------
    overlaps = all(
        CAMERA_BOUNDS[2 * i] < (RA_MIRROR_MAX[i]) - 1e-6 and (RA_MIRROR_MIN[i]) < CAMERA_BOUNDS[2 * i + 1] - 1e-6
        for i in range(3)
    )
    check(overlaps, "A0: precondition -- the flagged camera/mirror AABBs really do overlap on all 3 axes")

    # --- B. the promoted mirror is REPORTED (the bug) ------------------------
    hits = stub.camera_body_collisions("camera")
    check(bool(hits), f"B1: a promoted solid overlapping the camera is reported (got {hits})")
    check(
        any("mirror" in h.lower() or h.startswith("row S") for h in hits),
        f"B2: the hit names the promoted row, not an overlay label (got {hits})",
    )

    # --- C. no false alarm when the camera is clear --------------------------
    clear = _make_stub(
        (194.93, 264.93, -35.0, 35.0, -200.0, -120.0),
        [_Row("Promoted RA mirror", RA_MIRROR_MIN, RA_MIRROR_MAX)],
    )
    check(clear.camera_body_collisions("camera") == [], "C1: a camera clear of the mirror reports nothing")

    # --- D. a row without promotion metadata is ignored, not crashed ---------
    class _Bare:
        name = "plain row"
        advanced = {}

    bare = _make_stub(CAMERA_BOUNDS, [_Bare()])
    check(bare.camera_body_collisions("camera") == [], "D1: a non-promoted row is skipped (no crash)")

    # --- E. overlays are still scanned (a scene can have both) ---------------
    both = _make_stub(CAMERA_BOUNDS, [])
    both._transformed_imported_step_mesh_for_label = (
        lambda label: _Mesh(CAMERA_BOUNDS) if label in ("camera", "optical") else None
    )
    check(
        both.camera_body_collisions("camera") == ["optical"],
        "E1: an overlapping STEP OVERLAY is still reported (overlay scan not lost)",
    )

    # --- F. remove-defocus asks the question ---------------------------------
    try:
        from KrakenOS.UI import open3d_inspector

        src = inspect.getsource(open3d_inspector.Kraken3DInspector._snap_detector_to_image_plane)
    except Exception as exc:
        notes.append(f"SKIP: could not read the remove-defocus wrapper ({type(exc).__name__}: {exc})")
        return ok, notes
    check(
        "camera_body_collisions" in src,
        "F1: the remove-defocus wrapper runs the camera collision check",
    )
    check(
        src.index("_apply_model_change") < src.index("camera_body_collisions")
        if "camera_body_collisions" in src
        else False,
        "F2: it checks AFTER the rebuild (the transformed mesh is memoized, bugs/0331)",
    )

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP") or note.startswith("PASS")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
