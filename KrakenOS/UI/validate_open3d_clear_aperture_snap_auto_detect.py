#!/usr/bin/env python3
"""Display-free guard: an AUTO-DETECTED clear aperture is snappable (bugs/0344).

User directive (imported LED, flag_20260717_145154_083):
  "right click snap still not working."

Root cause:
  bugs/0342 offered the "Snap Clear Aperture -> Optical Axis" only inside the
  ``step_clear_aperture(step_label) is not None`` branch -- i.e. only when a MANUAL
  bugs/0134 record existed. But the imported LED auto-detects its clear aperture
  (bugs/0319 C2: 5 candidates, top = face 266, finite centre + normal) with NO manual
  record, and the hover highlight already keys off that auto-detect via
  ``_clear_aperture_opening_face_index``. So the opening lit up on hover but had no
  snap item -- "right click snap still not working" even though nothing was "set".

  (Confirmed headless by bugs/probe_0344_led_auto_ca_snap.py:
   ``step_clear_aperture('led') is None`` yet the opening resolves to a finite
   centre + normal.)

Fix:
  Resolve the snap from ``_clear_aperture_opening_face_index`` (manual record OR
  auto-detect) and offer it OUTSIDE the manual-record gate, in both the body STEP menu
  and the pinned-opening menu. Only Center / Forget (which act on the manual record)
  stay gated on it.

What it checks
--------------
  1. ``_clear_aperture_opening_face_index`` falls back to the auto-detect candidate when
     there is no manual record (so the resolver used by the snap reaches auto-detect).
  2. Source contract: in BOTH menus the ``_clear_aperture_opening_center_normal`` snap is
     resolved BEFORE (i.e. outside) the ``step_clear_aperture(...) is not None`` gate, so
     an auto-detected opening -- with no manual record -- is snappable.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_clear_aperture_snap_auto_detect

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types


def _check_auto_detect_fallback() -> list[str]:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    failures: list[str] = []

    editor = types.SimpleNamespace(
        step_clear_aperture=lambda label: None,                     # NO manual record
        _step_path_for_label=lambda label: "/tmp/led.step",
        auto_detect_step_clear_aperture_candidates=lambda label: [
            types.SimpleNamespace(face_index=266),
            types.SimpleNamespace(face_index=306),
        ],
    )
    insp = types.SimpleNamespace(editor=editor, _ca_opening_face_index_cache={})
    insp._clear_aperture_opening_face_index = types.MethodType(
        Kraken3DInspector._clear_aperture_opening_face_index, insp
    )

    fid = insp._clear_aperture_opening_face_index("led")
    if fid != 266:
        failures.append(
            f"FAIL(1): with no manual record the opening face index must fall back to the "
            f"top auto-detect candidate (266), got {fid!r}"
        )
    return failures


def _resolver_is_ungated(src: str) -> bool:
    """True when the opening-snap resolver runs BEFORE the manual-record gate."""
    resolver_at = src.find("_clear_aperture_opening_center_normal(step_label)")
    gate_at = src.find("step_clear_aperture(step_label) is not None")
    return resolver_at >= 0 and gate_at >= 0 and resolver_at < gate_at


def _check_source_contract() -> list[str]:
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as FA

    failures: list[str] = []

    body = inspect.getsource(FA._show_surface_function_context_menu)
    if not _resolver_is_ungated(body):
        failures.append(
            "FAIL(2): the body-menu snap must resolve _clear_aperture_opening_center_normal "
            "OUTSIDE (before) the 'step_clear_aperture(...) is not None' gate so an "
            "auto-detected opening is snappable without a manual record"
        )

    opening = inspect.getsource(FA._show_selected_opening_context_menu)
    if not _resolver_is_ungated(opening):
        failures.append(
            "FAIL(2): the pinned-opening snap fallback must resolve "
            "_clear_aperture_opening_center_normal OUTSIDE the manual-record gate"
        )
    return failures


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    failures.extend(_check_auto_detect_fallback())
    failures.extend(_check_source_contract())
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] an auto-detected clear aperture is not snappable to the optical axis")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] an AUTO-DETECTED clear aperture (no manual record) is snappable to the "
          "optical axis from both the body and pinned-opening menus (bugs/0344)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
