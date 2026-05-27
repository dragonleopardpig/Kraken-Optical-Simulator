"""Validate the saved five-penta cascade with imported lens layout.

This is a fixture-level guard for saved row-backed optical solids plus a live
imported optical STEP lens. It avoids opening Tk/VTK, but it checks that the
saved layout remains loadable and still produces the expected source bundle.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_PATH = PROJECT_ROOT / "attachment" / "five_penta_prism_cascade_with_lens.py"


def _portable_fixture_path(path_text: object) -> Path:
    path = Path(str(path_text or "")).expanduser()
    if path.exists():
        return path
    marker = "Kraken-Optical-Simulator/"
    text = str(path_text or "")
    if marker in text:
        candidate = PROJECT_ROOT / text.split(marker, 1)[1]
        if candidate.exists():
            return candidate
    return path


def _load_layout_module():
    spec = importlib.util.spec_from_file_location("kraken_five_penta_with_lens_layout", LAYOUT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load layout module from {LAYOUT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures: list[str] = []
    if not LAYOUT_PATH.exists():
        print(f"missing saved layout: {LAYOUT_PATH}")
        return 1

    try:
        module = _load_layout_module()
    except Exception as exc:
        print(f"Five-penta-with-lens layout validation failed to import: {exc}")
        return 1

    surfaces = list(getattr(module, "SURFACES", []) or [])
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    settings["optical_step_path"] = str(_portable_fixture_path(settings.get("optical_step_path")))
    module.SETTINGS = settings
    solid_rows = [row for row in surfaces if dict(row).get("surface") == "Solid 3D STL"]
    if len(surfaces) != 7:
        failures.append(f"Expected 7 saved rows, got {len(surfaces)}.")
    if len(solid_rows) != 5:
        failures.append(f"Expected 5 penta optical-solid rows, got {len(solid_rows)}.")
    for index, row in enumerate(solid_rows, start=1):
        advanced = dict(row.get("advanced", {}) or {})
        metadata = dict(advanced.get("OpticalSolidFaces", {}) or {})
        if metadata.get("source_stl"):
            metadata["source_stl"] = str(_portable_fixture_path(metadata.get("source_stl")))
            advanced["OpticalSolidFaces"] = metadata
        faces = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
        functions = {str(face.get("face_id", "") or ""): str(face.get("function", "") or "") for face in faces}
        if functions.get("F003") != "Mirror" or functions.get("F004") != "Mirror":
            failures.append(f"Penta row {index} does not preserve F003/F004 Mirror assignments.")
        for path_key in ("OpticalSolidSourcePath", "Solid_3d_stl"):
            path_text = str(advanced.get(path_key, "") or "")
            fixture_path = _portable_fixture_path(path_text)
            advanced[path_key] = str(fixture_path)
            if not path_text or not fixture_path.exists():
                failures.append(f"Penta row {index} missing readable {path_key}: {path_text!r}.")
        row["advanced"] = advanced

    module.SURFACES = surfaces
    optical_step_path = _portable_fixture_path(settings.get("optical_step_path"))
    if not optical_step_path.exists():
        failures.append(f"Imported lens STEP path is missing: {optical_step_path}.")
    if str(settings.get("source_model", "")) != "Collimated disk source":
        failures.append(f"Expected Collimated disk source, got {settings.get('source_model')!r}.")
    if str(settings.get("trace_mode", "")) != "Non-Sequential Preview":
        failures.append(f"Expected Non-Sequential Preview, got {settings.get('trace_mode')!r}.")

    try:
        system = module.build_runtime_system()
        rays = module.build_rays(system)
        ray_count = int(getattr(rays, "nrays", 0) or 0)
        valid_count = len(list(getattr(rays, "valid")()))
    except Exception as exc:
        failures.append(f"Saved layout failed runtime build/source trace: {exc}")
    else:
        if ray_count != 13:
            failures.append(f"Expected 13 saved source rays, got {ray_count}.")
        if valid_count != 13:
            failures.append(f"Expected 13 valid source traces, got {valid_count}.")

    if failures:
        print("Five-penta-with-lens layout validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Five-penta-with-lens layout validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
