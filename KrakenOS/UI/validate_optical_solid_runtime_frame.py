from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


def _load_penta_module():
    repo_root = Path(__file__).resolve().parents[2]
    layout_path = repo_root / "attachment" / "penta.py"
    spec = importlib.util.spec_from_file_location("kraken_ui_penta_layout", layout_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {layout_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = _load_penta_module()
    system = module.build_runtime_system()
    rays = module.build_rays(system)
    overrides = getattr(system, "_optical_solid_output_port_pose_overrides", {}) or {}
    row6_pose = overrides.get(6, {})
    if "source_to_runtime_world" not in row6_pose:
        raise AssertionError("Row 6 runtime-frame calibration missing from output-port overrides.")
    image_hits = 0
    row6_hits = 0
    stopped_at_row5 = 0
    for ray_index, surface_ids_raw in enumerate(getattr(rays, "SURFACE", ())):
        surface_ids = np.asarray(surface_ids_raw, dtype=int).ravel()
        if surface_ids.size == 0:
            raise AssertionError(f"Ray {ray_index} recorded no surfaces.")
        if int(surface_ids[-1]) == 7:
            image_hits += 1
        if np.any(surface_ids == 6):
            row6_hits += 1
        if int(surface_ids[-1]) == 5:
            stopped_at_row5 += 1
    total_rays = int(len(getattr(rays, "CC", ()) or ()))
    if total_rays <= 0:
        raise AssertionError("Penta layout produced no rays.")
    if row6_hits != total_rays:
        raise AssertionError(f"Expected every ray to hit row 6, got {row6_hits}/{total_rays}.")
    if image_hits != total_rays:
        raise AssertionError(f"Expected every ray to reach the Image plane, got {image_hits}/{total_rays}.")
    if stopped_at_row5 != 0:
        raise AssertionError(f"Expected no rays to stop at row 5 after runtime-frame correction, got {stopped_at_row5}.")
    print(
        "validate_optical_solid_runtime_frame: "
        f"rays={total_rays}, row6_hits={row6_hits}, image_hits={image_hits}, stopped_at_row5={stopped_at_row5}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
