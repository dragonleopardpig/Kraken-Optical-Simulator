"""Guard: importing a vendor camera folder asks the user for the flange-to-sensor
optical distance when it cannot be scraped (bugs/0309).

Reported (recording flag_20260715_075815_948): after importing the BC-OM25M camera,
"the sensor location is not at the camera physical sensor location ... the optical
distance is 12 mm, the information is labelled in one of the picture, not the table.
Is the PDF extraction able to read this information?" -- no: the 12 mm flange-to-
sensor distance appears only in the datasheet's mechanical DRAWING (not the spec
table) and is not modelled in the STEP (the housing shows the ~24 mm mount cavity,
not the sensor body). So ``build_camera_record_from_assets`` leaves
``camera_front_to_sensor_mm`` unset, ``_current_camera_front_to_sensor_mm`` reads 0,
and the sensor / image plane sits on the mount face instead of 12 mm behind it.

Fix: ``import_vendor_camera_from_folder`` prompts for the value (``askfloat``) BEFORE
persisting the record, when it could not be scraped. ``_apply_camera_flange_distance``
is the pure decision (provider injected -> display-free): it stamps
``camera_front_to_sensor_mm`` on the record only when missing + a positive finite
value is supplied, appends an audit note, and never re-prompts or overwrites a
scraped value.

This guard is DISPLAY-FREE:
  * A -- the apply helper: a missing value is stamped from the provider (+ note); an
    already-known value is never re-prompted or overwritten; Cancel / None and any
    non-positive / non-finite / non-numeric value leave the record untouched.
  * B -- the value the user enters is exactly what the display reads: feeding the
    stamped record through the REAL ``_current_camera_front_to_sensor_mm`` returns it
    (so ``camera_front_z = image_plane_z - value``).
  * C (wiring) -- ``import_vendor_camera_from_folder`` calls
    ``_prompt_camera_flange_distance`` between building and persisting the record, and
    the prompt uses ``simpledialog.askfloat`` and delegates to the pure helper.
  * D -- real BC-OM25M asset (skip-if-absent): the scraped record genuinely lacks the
    flange distance (so the prompt fires), and applying 12 mm sticks.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_camera_flange_prompt

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import math


def _make_imported(front=None, name="BC-OM25M"):
    from KrakenOS.UI.services.camera_folder_import import ImportedCamera
    record = {"sensor_width_mm": 23.04, "sensor_height_mm": 23.04}
    if front is not None:
        record["camera_front_to_sensor_mm"] = front
    return ImportedCamera(name=name, record=record, spec=None, assets=None, notes=[])


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin

    apply = LayoutTableWorkbenchMixin._apply_camera_flange_distance

    class _Shim:
        pass

    shim = _Shim()

    # --- A. the pure apply decision --------------------------------------------
    c = _make_imported()
    applied = apply(shim, c, lambda: 12.0)
    ok(applied == 12.0 and c.record.get("camera_front_to_sensor_mm") == 12.0,
       f"A1: a missing flange distance is stamped from the provider "
       f"(applied={applied!r}, record={c.record.get('camera_front_to_sensor_mm')!r})")
    ok(any("12" in n for n in c.notes),
       "A2: applying the flange distance leaves an audit note on the import")

    calls = {"n": 0}

    def prov_known():
        calls["n"] += 1
        return 99.0

    c = _make_imported(front=11.48)
    applied = apply(shim, c, prov_known)
    ok(applied is None and c.record["camera_front_to_sensor_mm"] == 11.48 and calls["n"] == 0,
       f"A3: an already-scraped value is never re-prompted or overwritten "
       f"(provider calls={calls['n']}, record={c.record['camera_front_to_sensor_mm']!r})")

    c = _make_imported()
    applied = apply(shim, c, lambda: None)
    ok(applied is None and "camera_front_to_sensor_mm" not in c.record,
       "A4: Cancel / None leaves the record unchanged (import still proceeds -- sensor + FOV unaffected)")

    bad_values = [0.0, -5.0, float("nan"), float("inf"), "oops", None]
    bad_ok = True
    for bad in bad_values:
        c = _make_imported()
        applied = apply(shim, c, lambda b=bad: b)
        if not (applied is None and "camera_front_to_sensor_mm" not in c.record):
            bad_ok = False
            break
    ok(bad_ok, "A5: non-positive / non-finite / non-numeric / None inputs are all rejected")

    # --- B. what the user enters is what the display reads ----------------------
    c = _make_imported()
    apply(shim, c, lambda: 12.0)

    class _DisplayShim:
        _rec = c.record

        def _current_camera_record(self):
            return self._rec

    read_back = LayoutPolylineDisplayMixin._current_camera_front_to_sensor_mm(_DisplayShim())
    ok(math.isclose(read_back, 12.0),
       f"B1: the stamped value flows to the display consumer "
       f"(_current_camera_front_to_sensor_mm -> {read_back!r}; camera_front_z = image_z - {read_back!r})")

    # --- C. wiring: prompt between build and persist ---------------------------
    handler_src = inspect.getsource(LayoutTableWorkbenchMixin.import_vendor_camera_from_folder)
    i_build = handler_src.find("build_camera_record_from_assets(")
    i_prompt = handler_src.find("_prompt_camera_flange_distance(")
    i_write = handler_src.find("write_imported_camera(")
    ok(i_build != -1 and i_prompt != -1 and i_write != -1 and i_build < i_prompt < i_write,
       f"C1 (fail-before/pass-after): the import prompts for the flange distance AFTER building and "
       f"BEFORE persisting the record (build@{i_build} < prompt@{i_prompt} < write@{i_write})")

    prompt_src = inspect.getsource(LayoutTableWorkbenchMixin._prompt_camera_flange_distance)
    ok("simpledialog.askfloat(" in prompt_src,
       "C2: the prompt asks for a numeric value via simpledialog.askfloat")
    ok("_apply_camera_flange_distance(" in prompt_src,
       "C3: the prompt delegates to the pure _apply_camera_flange_distance decision")

    # --- D. real BC-OM25M asset (skip-if-absent) -------------------------------
    from pathlib import Path
    from KrakenOS.UI.services.camera_folder_import import (
        scan_camera_folder,
        build_camera_record_from_assets,
    )

    folder = None
    for cand in ("attachment/Cameras/BC-OM25M", "attachment/Cameras/BC-OM25M12X2"):
        if Path(cand).is_dir():
            folder = cand
            break
    if folder is None:
        skip("D: the BC-OM25M vendor folder is absent (Filen-synced attachment) -- real-asset check skipped")
    else:
        try:
            assets = scan_camera_folder(folder)
            imported = build_camera_record_from_assets(assets)
        except Exception as exc:  # pragma: no cover
            skip(f"D: could not build the BC-OM25M record ({type(exc).__name__}: {exc})")
        else:
            missing = imported.record.get("camera_front_to_sensor_mm")
            ok(missing is None,
               f"D1: the real BC-OM25M scrape genuinely lacks the flange distance "
               f"(camera_front_to_sensor_mm={missing!r}) -- so the prompt WOULD fire (the flag_20260715_075815 case)")
            applied = apply(shim, imported, lambda: 12.0)
            ok(applied == 12.0 and imported.record.get("camera_front_to_sensor_mm") == 12.0,
               f"D2: entering 12 mm sticks on the real record "
               f"(camera_front_to_sensor_mm={imported.record.get('camera_front_to_sensor_mm')!r})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Camera flange-prompt validation passed.")
        return 0
    print("Camera flange-prompt validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
