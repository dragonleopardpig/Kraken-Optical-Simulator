"""Regenerate every om05a attachment deliverable clobbered by the 18:48 rewind."""
import importlib.util
import json
import sys
import time
from pathlib import Path

SCRATCH = Path("/tmp/claude-1000/-home-thinky-Projects/15653223-dbcf-4a7a-bb47-d26cbd830f16/scratchpad")
T0 = time.time()


def note(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def run(name, fn="main"):
    spec = importlib.util.spec_from_file_location(name, SCRATCH / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    getattr(mod, fn)()
    note(f"{name}.{fn} done")
    return mod


def main():
    note("1/8 components (asm_split)")
    run("asm_split")
    note("2/8 camera re-extract (mount -> -z)")
    run("fix_camera_step")
    note("3/8 SV25 camera registration")
    p = Path("attachment/Cameras/imported_cameras.json")
    data = json.loads(p.read_text())
    data["CAM-SV25MCCXP"] = {
        "camera_front_to_sensor_mm": 17.6,
        "image_diameter_mm": 23.04,
        "pixel_size_um": [4.5, 4.5],
        "resolution_px": [5120, 5120],
        "sensor_diagonal_mm": 32.58348047707611,
        "sensor_height_mm": 23.04,
        "sensor_width_mm": 23.04,
        "step_path": "attachment/om05a_components/camera_sv25mccxp.step",
    }
    p.write_text(json.dumps(data, indent=2, sort_keys=True))
    note("SV25 registered")
    note("4/8 straight scene (real PYRITE) + refocus")
    mod = run("build_om05a2", "build_layout_file")
    mod.edit_scene()
    mod.measure_and_refocus()
    mod.measure_and_refocus()
    note("5/8 FOV 54x54 (13 fields) + Manual sensor + camera model + lens flip")
    run("set_fov54")
    run("fix_sensor")
    run("fix_flag2")
    note("6/8 folded-view spec injection + renders")
    run("fold_spec_om05a")
    note("7/8 folded-only scene (both mirrors) + verify")
    run("build_folded2", "extract_mirror2_s")
    m = importlib.util.module_from_spec(importlib.util.spec_from_file_location("bf2", SCRATCH / "build_folded2.py"))
    spec = importlib.util.spec_from_file_location("bf2", SCRATCH / "build_folded2.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.build()
    m.verify()
    note("8/8 solved-cell disc check")
    sf = Path("attachment/cells/solved/solved_front.py")
    if sf.exists():
        text = sf.read_text()
        note(f"solved_front: 320.1778 x{text.count('320.1778')}, 50.0591 x{text.count('50.0591')}")
        if "320.1778" in text:
            run("repair_solved")
    else:
        note("solved_front.py missing entirely")
    note("ALL DONE")


if __name__ == "__main__":
    main()
