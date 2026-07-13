"""Validate that an auto-imported lens surrogate is a COMPLETE machine-vision
setup, not a bare optic (bug 0295).

"Import Lens from Folder" (the datasheet-only Path C in
``machine_vision_folder_import``) used to emit a surrogate whose SETTINGS carried
only ``object_mode`` + ``wavelength``.  With no field defined, the object plane
rendered as a plain disc (the coverage overlay has no image radius --
``detector_coverage_overlay``: ``sys_image_radius`` is None -> the object-FOV
rectangle loop ``continue``s) and only the on-axis ray launched.  The user
flagged it: "the Object Plane not showing FOV, just a big circular plane ... The
Field parameters are not set ... Rays launching parameters are not set as well
(only center ray) ... import from folder --> create lens surrogate seems not
complete."

The fix makes Path C carry the field the way the hand-authored ``machine_vision_*``
presets do: ``field_type='Real Image Height'``, ``field_value`` = the datasheet's
max real image height (image-circle / 2), ``field_count=3``.  That gives the
object-plane FOV rectangle + off-axis ray fans immediately; a subsequently glued
camera then overrides ``field_value`` with the true sensor half-height (Stage 2).

This guard is DISPLAY-FREE and portable (pure numbers + geometry; no VTK, no
vendor PDF/STEP -- it drives ``_core_from_datasheet_cardinals``, which the engine
splits out precisely so the cardinals->optics step is unit-testable without a
real datasheet):

  * A -- a datasheet-derived surrogate core sets field_type / field_value /
    field_count, and field_value == image_circle / 2 (fail-before / pass-after).
  * B -- fed that field, the coverage overlay emits an object_fov_rect with a
    positive half-extent (the "big disc" becomes a real FOV rectangle).
  * C -- the general path: a lens with no datasheet image circle still gets a
    field (from the lens aperture), so no datasheet-only lens is left field-less.
  * D -- Stage 2: importing the vendor camera STEP resolves back to its camera
    model (``camera_model_for_step_path``) and couples the surrogate to that
    sensor, so the field/object-FOV shrink from the datasheet max-sensor
    capability (image-circle/2 == 50 mm) to the real sensor half-diagonal
    (hr25MCX == 16.29 mm) -- the "synchronize with the subsequent camera" ask.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folder_import_completeness

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from pathlib import Path


def _pyrite_cardinals():
    """The scraped PYRITE 5.6/80/1.0x V38 datasheet cardinals (finite 1x),
    hand-built so the test needs no PDF."""
    from KrakenOS.UI.services.datasheet_prescription_import import DatasheetCardinals

    return DatasheetCardinals(
        effl=82.39,
        front_focal=-60.14,
        back_focal=60.14,
        hh=-1.31,
        span=43.19,
        fno=5.6,
        image_circle=100.0,
        magnification=-1.0,
        mag_label="1.0x",
        title="PYRITE 5.6/80/1.0x V38",
        lens_id="1097785",
    )


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    from KrakenOS.UI.services.machine_vision_folder_import import (
        LensFolderAssets,
        _core_from_datasheet_cardinals,
    )
    from KrakenOS.UI.services import detector_coverage_overlay as dco

    assets = LensFolderAssets(folder=Path("PYRITE_56_80_10x_V38_1097785"))

    # --- A. the importer core now carries the field --------------------------
    cardinals = _pyrite_cardinals()
    core = _core_from_datasheet_cardinals(cardinals, assets)
    settings = dict(core.settings_base)

    ftype = settings.get("field_type")
    fval = settings.get("field_value")
    fcount = settings.get("field_count")

    ok(ftype == "Real Image Height",
       f"A1: surrogate sets field_type='Real Image Height' (got {ftype!r})")
    expected = round(cardinals.image_circle / 2.0, 4)
    ok(fval is not None and abs(float(fval) - expected) <= 1e-6,
       f"A2: field_value == image_circle/2 == {expected:g} (got {fval!r})")
    ok(fcount is not None and int(fcount) >= 2,
       f"A3: field_count launches off-axis fans, not just the center ray (got {fcount!r})")
    ok(core.object_mode == "Finite",
       f"A4: a magnified datasheet lens is a finite conjugate (got {core.object_mode!r})")

    # --- B. that field yields an object FOV rectangle (not a bare disc) -------
    # image radius = the field's max real image height; a bare lens (no camera
    # yet) uses the largest square inscribed in that image circle.
    image_radius = float(fval) if fval is not None else 0.0
    rec_side = dco.recommended_inscribed_sensor_side(image_radius)
    mag = abs(float(cardinals.magnification))
    metrics = dco.detector_coverage_metrics(
        rec_side, rec_side, image_radius, mag, sensor_is_real=False
    )
    specs = dco.detector_coverage_overlay_specs(
        (0.0, 0.0, 0.0), (0.0, 0.0, 100.0), metrics, object_mode_finite=True
    )
    fov = next((s for s in specs if s["kind"] == "object_fov_rect"), None)
    ok(fov is not None,
       "B1: an object_fov_rect is emitted (the big disc becomes a real FOV rectangle)")
    ok(metrics.object_fov_half_width > 1e-9 and metrics.object_fov_half_height > 1e-9,
       f"B2: object FOV has a positive extent "
       f"({2 * metrics.object_fov_half_width:.1f}x{2 * metrics.object_fov_half_height:.1f} mm)")

    # --- C. general: a lens with no datasheet image circle still gets a field -
    import dataclasses

    no_circle = dataclasses.replace(cardinals, image_circle=None)
    core2 = _core_from_datasheet_cardinals(no_circle, assets)
    fval2 = core2.settings_base.get("field_value")
    ok(core2.settings_base.get("field_type") == "Real Image Height" and fval2 and float(fval2) > 0.0,
       f"C1: a datasheet lens with no image circle still gets a field from the aperture (got {fval2!r})")

    # --- D. Stage 2: importing the vendor camera STEP couples the surrogate to
    #     its sensor, so the FOV follows the REAL sensor (shrinks from the
    #     datasheet max-sensor capability to the camera's actual sensor).
    from KrakenOS.UI.camera_database import (
        camera_image_coverage_mm,
        camera_model_for_step_path,
    )

    model = camera_model_for_step_path("3D_CAD_HR25xCXP.STEP")
    ok(model == "Allied Vision hr25MCX",
       f"D1: the vendor camera STEP filename resolves back to its model (got {model!r})")
    ok(camera_model_for_step_path("random_widget.step") is None,
       "D2: an unrecognised STEP does not falsely couple a camera")

    coverage = camera_image_coverage_mm(model) if model else None
    sensor_field = coverage[1] if coverage else None
    datasheet_field = expected  # image_circle / 2 == 50 mm (the Stage-1 default)
    ok(sensor_field is not None and 0.0 < float(sensor_field) < datasheet_field,
       f"D3: coupling the camera shrinks the field from the datasheet max "
       f"{datasheet_field:g} mm to the real sensor half-diagonal (got {sensor_field!r})")

    # the object FOV follows: same bare-lens inscribed-square geometry, now sized
    # by the real sensor -> a strictly smaller object FOV than the datasheet field.
    def _object_fov_half(image_radius: float) -> float:
        side = dco.recommended_inscribed_sensor_side(image_radius)
        m = dco.detector_coverage_metrics(side, side, image_radius, mag, sensor_is_real=False)
        return m.object_fov_half_width

    ds_fov = _object_fov_half(datasheet_field)
    cam_fov = _object_fov_half(float(sensor_field)) if sensor_field else 0.0
    ok(0.0 < cam_fov < ds_fov,
       f"D4: the object FOV follows the sensor "
       f"({2 * cam_fov:.1f} mm camera-coupled < {2 * ds_fov:.1f} mm datasheet)")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print(
            "Folder-import completeness validation passed: a datasheet-imported "
            "surrogate carries the field (Real Image Height = image-circle/2, "
            "field_count 3) so the object-plane FOV rectangle + off-axis ray fans "
            "render like the hand-authored machine_vision_* presets; and importing "
            "the vendor camera STEP couples the surrogate to its sensor so the FOV "
            "follows the real sensor (Stage 2)."
        )
        return 0
    print("Folder-import completeness validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
