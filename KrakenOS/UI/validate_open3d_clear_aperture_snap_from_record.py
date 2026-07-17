#!/usr/bin/env python3
"""Display-free guard: snap the CA to the optical axis from its opening (bugs/0342).

User directive (imported LED, latest flag):
  "still can't right click snap CA to optical axis even though I set the CA first,
   then right click again to snap."

Root cause (0342):
  The center+normal "Snap Clear Aperture -> Optical Axis" was offered only when the
  right-click landed EXACTLY on the see-through opening (the ``opening_feature`` hover)
  or while the rim was PINNED. But "Set Clear Aperture (pick window face)" runs
  ``refresh_from_editor`` which drops the pin, and the follow-up right-click lands on a
  housing face (the flag's ``prior_hover_key`` was ``('step','led','F053')``), so the
  snap item was absent -- even though a CA opening now existed.

Fix:
  A clear-aperture opening's centre + unit normal are known from its analytic face
  index (``_step_overlay_fine_face_centroid_normal``); the body STEP menu and the
  pinned-opening menu offer the snap straight from that -- reachable with no live
  opening hover and no pin. bugs/0344 broadened the resolver to key off
  ``_clear_aperture_opening_face_index`` (manual record OR auto-detect); this guard
  covers the resolver's contract and that the snap is offered in both menus.

What it checks
--------------
  1. Behavioural: ``_clear_aperture_opening_center_normal`` returns the opening's world
     ``(center, normal)`` when its face resolves, and ``(None, None)`` when no opening
     face index resolves or the face cannot be resolved on the current mesh.
  2. Source contract (body menu): gated on ``opening_feature is None``, it resolves
     ``_clear_aperture_opening_center_normal`` and routes the snap to
     ``_snap_clear_aperture_to_optical_axis_from_context``.
  3. Source contract (pinned-opening menu): a ``not normal_finite`` fallback resolves the
     same helper so the snap stays reachable when the pinned rim has no usable normal.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_clear_aperture_snap_from_record

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types

import numpy as np


def _make_service(*, face_index, resolved):
    """A fake FA service whose opening resolves to ``face_index`` / ``resolved``."""
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as FA

    editor = types.SimpleNamespace(
        _step_overlay_fine_face_centroid_normal=lambda label, fid: resolved,
    )
    svc = types.SimpleNamespace(editor=editor)
    svc._clear_aperture_opening_face_index = lambda label: face_index
    svc._clear_aperture_opening_center_normal = types.MethodType(
        FA._clear_aperture_opening_center_normal, svc
    )
    return svc


def _check_helper() -> list[str]:
    failures: list[str] = []

    centroid = np.asarray([1.0, 2.0, 3.0])
    normal = np.asarray([0.0, 0.0, 1.0])

    # A resolved opening face -> world (center, normal).
    svc = _make_service(face_index=266, resolved=(centroid, normal, 42.0))
    center_out, normal_out = svc._clear_aperture_opening_center_normal("led")
    if center_out is None or normal_out is None:
        failures.append("FAIL(1): a resolved opening must yield (center, normal), got None")
    else:
        if not np.allclose(center_out, centroid):
            failures.append(f"FAIL(1): center must come from the opening centroid, got {center_out}")
        if not np.allclose(normal_out, normal):
            failures.append(f"FAIL(1): normal must come from the opening face normal, got {normal_out}")

    # No opening face index -> (None, None).
    svc_none = _make_service(face_index=None, resolved=(centroid, normal, 42.0))
    if svc_none._clear_aperture_opening_center_normal("led") != (None, None):
        failures.append("FAIL(1): no opening face index must yield (None, None)")

    # Face index present but the face cannot be resolved on the mesh -> (None, None).
    svc_unres = _make_service(face_index=266, resolved=None)
    if svc_unres._clear_aperture_opening_center_normal("led") != (None, None):
        failures.append("FAIL(1): an unresolvable opening face must yield (None, None)")

    # Non-finite geometry is rejected.
    bad = np.asarray([np.nan, 0.0, 0.0])
    svc_bad = _make_service(face_index=266, resolved=(bad, normal, 42.0))
    if svc_bad._clear_aperture_opening_center_normal("led") != (None, None):
        failures.append("FAIL(1): a non-finite opening centroid must yield (None, None)")

    return failures


def _check_source_contract() -> list[str]:
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as FA

    failures: list[str] = []

    body = inspect.getsource(FA._show_surface_function_context_menu)
    # The snap must be gated on no opening hover and route to the shared snap pipeline.
    if "if opening_feature is None:" not in body:
        failures.append("FAIL(2): the body menu must gate the snap on 'opening_feature is None'")
    if "_clear_aperture_opening_center_normal(step_label)" not in body:
        failures.append("FAIL(2): the body menu must resolve _clear_aperture_opening_center_normal")
    if "_snap_clear_aperture_to_optical_axis_from_context" not in body:
        failures.append("FAIL(2): the body menu must route the snap to _snap_clear_aperture_to_optical_axis_from_context")

    opening = inspect.getsource(FA._show_selected_opening_context_menu)
    if "if not normal_finite:" not in opening:
        failures.append("FAIL(3): the pinned-opening menu must add a 'not normal_finite' snap fallback")
    if "_clear_aperture_opening_center_normal(step_label)" not in opening:
        failures.append("FAIL(3): the pinned-opening fallback must resolve _clear_aperture_opening_center_normal")

    return failures


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    failures.extend(_check_helper())
    failures.extend(_check_source_contract())
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] the CA snap is not reachable from the resolved opening")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] a DEFINED clear aperture is snappable to the optical axis from its opening "
          "(body menu + pinned-opening fallback), no live opening hover or pin required (bugs/0342)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
