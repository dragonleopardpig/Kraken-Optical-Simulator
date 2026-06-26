#!/usr/bin/env python3
"""Display-free guard for bugs/0155: the imported Imaging Lens STEP is a pure
decoration whose right-click menu matches the LED and Camera decorations -- it
must NOT offer "Promote to Optical Element" or any optical face assignment.

The one synchronization the user asked to keep: the native KrakenOS surrogate we
build for the lens tracks the vendor STEP. "Glue STEP to Surrogate" re-pins the
surrogate's Front Datum onto the STEP front face (via glue_step_overlay_to_surrogate)
AND its Rear Datum onto the STEP rear face (via improve_lens_surrogate_rear_to_step),
so the surrogate span matches the vendor CAD. That glue is a reset, never a promote,
so it stays on the menu for the lens just like the LED/Camera resets.

This mirrors validate_open3d_decoration_not_promotable (the promote/assign block) but
pins the *menu shape* and the *surrogate datum wiring* that are specific to 0155.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_imaging_lens_decoration

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace


class _FakeMenu:
    """Collect the labels a right-click menu builder appends -- no Tk."""

    def __init__(self) -> None:
        self.items: list[tuple[str, str | None]] = []

    def add_command(self, *_args, label=None, command=None, **_kwargs) -> None:
        self.items.append(("command", label))

    def add_separator(self, *_args, **_kwargs) -> None:
        self.items.append(("separator", None))

    def add_cascade(self, *_args, label=None, menu=None, **_kwargs) -> None:
        self.items.append(("cascade", label))

    def command_labels(self) -> list[str]:
        return [lbl for kind, lbl in self.items if kind == "command" and lbl is not None]


def _build_service():
    """A face-assignment service whose fake editor keeps the two-body BS<->LED glue
    inert (no LED path), so the element menu reduces to the per-label reset + resize
    (+ Promote only for the genuine 'optical' overlay)."""
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    editor = SimpleNamespace(
        _step_overlay_display_label=lambda lbl: str(lbl),
        optical_led_glued=lambda: False,
        _step_path_for_label=lambda label: None,
        _promoted_optical_solid_row_index=lambda label: None,
        append_debug=lambda *a, **k: None,
    )
    inspector = SimpleNamespace(
        editor=editor,
        status_var=SimpleNamespace(set=lambda msg: None),
        _debug_trace=lambda *a, **k: None,
    )
    return Open3DFaceAssignmentService(inspector)


def _menu_labels_for(label: str) -> list[str]:
    svc = _build_service()
    menu = _FakeMenu()
    svc.append_element_context_actions(menu, step_label=label)
    return menu.command_labels()


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    from KrakenOS.UI.services.step_overlay_labels import is_step_overlay_decoration
    from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    PROMOTE = "Promote to Optical Element"
    GLUE = "Glue STEP to Surrogate"

    # 1) Classification: the imaging lens is a decoration now (like LED/camera).
    if not is_step_overlay_decoration("lens"):
        failures.append("FAIL: 'lens' must be a decoration (bugs/0155)")
    if is_step_overlay_decoration("optical"):
        failures.append("FAIL: 'optical' must stay a promotable optical overlay")

    # 2) Menu shape parity: the lens menu matches the LED/camera decorations -- it
    #    offers its surrogate reset + Resize but NOT Promote; only 'optical' promotes.
    lens_menu = _menu_labels_for("lens")
    led_menu = _menu_labels_for("led")
    camera_menu = _menu_labels_for("camera")
    optical_menu = _menu_labels_for("optical")

    if PROMOTE in lens_menu:
        failures.append(f"FAIL: Imaging Lens menu must NOT offer Promote (got {lens_menu})")
    if PROMOTE in led_menu or PROMOTE in camera_menu:
        failures.append("FAIL: LED/Camera decorations must not offer Promote")
    if PROMOTE not in optical_menu:
        failures.append(f"FAIL: the 'optical' overlay must still offer Promote (got {optical_menu})")
    if GLUE not in lens_menu:
        failures.append(f"FAIL: Imaging Lens must keep '{GLUE}' (the surrogate datum sync) (got {lens_menu})")
    if "Resize Solid..." not in lens_menu:
        failures.append(f"FAIL: Imaging Lens must keep 'Resize Solid...' (got {lens_menu})")

    # 3) Display label rename: "Lens" -> "Imaging Lens".
    if StepOverlayImportService._step_overlay_display_label("lens") != "Imaging Lens":
        failures.append("FAIL: lens display label must be 'Imaging Lens'")
    kwdefaults = getattr(StepOverlayImportService.import_lens_step, "__kwdefaults__", {}) or {}
    if kwdefaults.get("display_label") != "Imaging Lens STEP":
        failures.append(f"FAIL: import_lens_step display_label default must be 'Imaging Lens STEP' (got {kwdefaults.get('display_label')!r})")

    # 4) Surrogate Front+Rear datum sync wiring is intact (the lone synchronization).
    glue_ctx_src = inspect.getsource(Open3DFaceAssignmentService._glue_step_to_surrogate_from_context)
    if "glue_selected_step_to_surrogate" not in glue_ctx_src:
        failures.append("FAIL: the lens surrogate reset menu item must call glue_selected_step_to_surrogate")
    glue_src = inspect.getsource(Kraken3DInspector.glue_selected_step_to_surrogate)
    if "glue_step_overlay_to_surrogate" not in glue_src:
        failures.append("FAIL: glue_selected_step_to_surrogate must re-pin the surrogate FRONT datum (glue_step_overlay_to_surrogate)")
    if "improve_lens_surrogate_rear_to_step" not in glue_src:
        failures.append("FAIL: glue_selected_step_to_surrogate must sync the surrogate REAR datum (improve_lens_surrogate_rear_to_step)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0155 imaging lens decoration menu/surrogate-sync")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Imaging Lens is a decoration (no Promote, matches LED/Camera); surrogate Front/Rear datum glue intact (bugs/0155)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
