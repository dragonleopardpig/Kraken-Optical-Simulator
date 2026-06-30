"""Validate the right-angle-mirror AZURE ELS-85/4.5V16K machine-vision layout.

This is the AZURE ELS-85 surrogate folded with a real PROMOTED STEP right-angle
mirror solid (Edmund 87391) instead of the earlier sequential ``Mirror`` row.  The
mirror is a non-sequential optical solid whose ``S001/F002`` face carries
``function = "Mirror"``, so the traced rays bend on the physical mirror face -- there
is only one path the ray can take.  Because the mirror is a real CAD body, the vendor
barrel STEP and the camera STEP overlays are kept (the earlier sequential-fold variant
had to drop them because the straight-axis overlay aligner could not fold a mesh).

This guard checks that:

* the layout is discoverable in the Machine Vision menu and has the expected 9 rows
  (Object -> promoted STEP mirror solid -> trailing AIR gap -> front datum -> two
  blackbox groups -> stop -> rear datum -> image);
* row 1 is a promoted STEP optical solid whose face metadata assigns a Mirror face and
  whose source STEP is the right-angle mirror;
* the paraxial ABCD matrix of the blackbox chain still reproduces EFL = 85 mm;
* both the lens STEP and the camera STEP overlays are preloaded (the fix for "surrogate
  does not come with LENS STEP" / "camera location is wrong"), and the camera model is
  kept so the image format stays camera/FOV-driven;
* the docs page exists and is indexed.

Like the other AZ85 surrogate guards this is a STANDALONE check, not a penta phase.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_library import discover_layouts, load_python_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUTS_DIR = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts"
LAYOUT_PATH = LAYOUTS_DIR / "machine_vision_AZ85_RA_Mirror.py"
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "machine_vision_azure_85_ra_mirror.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"


def _translation(distance: float) -> np.ndarray:
    return np.asarray([[1.0, distance], [0.0, 1.0]], dtype=float)


def _thin_lens(focal_length: float) -> np.ndarray:
    return np.asarray([[1.0, 0.0], [-1.0 / focal_length, 1.0]], dtype=float)


def _promoted_solid_advanced(row: dict) -> dict:
    advanced = row.get("advanced", {})
    return advanced if isinstance(advanced, dict) else {}


def _has_mirror_face(row: dict) -> bool:
    faces_meta = _promoted_solid_advanced(row).get("OpticalSolidFaces", {})
    faces = faces_meta.get("faces", []) if isinstance(faces_meta, dict) else []
    for face in faces:
        if not isinstance(face, dict):
            continue
        if str(face.get("function", "")).lower() == "mirror" or str(face.get("role", "")).lower() == "mirror":
            return True
    return False


def _solid_source_step(row: dict) -> str:
    advanced = _promoted_solid_advanced(row)
    src = advanced.get("OpticalSolidSourcePath", "")
    if not src:
        faces_meta = advanced.get("OpticalSolidFaces", {})
        if isinstance(faces_meta, dict):
            src = faces_meta.get("source_step", "")
    return str(src)


def run_checks():
    """Return (passed, failures) without printing -- usable as a phase body."""
    info = load_python_data(LAYOUT_PATH)
    layouts = discover_layouts(LAYOUTS_DIR)
    rows = info["surfaces"]
    settings = dict(info.get("settings", {}))
    surfs = [str(r.get("surface", "")) for r in rows]
    names = [str(r.get("name", "")) for r in rows]

    # Paraxial EFL from the two ideal blackbox thin-lens groups.
    # rows: 0 Object, 1 STEP mirror solid, 2 trailing AIR gap, 3 front datum,
    #       4 Group1 (Thin Lens), 5 Stop, 6 Group2 (Thin Lens), 7 rear datum, 8 Image
    efl = None
    if len(rows) == 9 and surfs[4] == "Thin Lens" and surfs[6] == "Thin Lens":
        front_to_g1 = float(rows[3]["thickness"])
        g1_to_stop = float(rows[4]["thickness"])
        stop_to_g2 = float(rows[5]["thickness"])
        g2_to_rear = float(rows[6]["thickness"])
        matrix = (
            _translation(g2_to_rear)
            @ _thin_lens(float(rows[6]["rc"]))
            @ _translation(stop_to_g2 + g1_to_stop)
            @ _thin_lens(float(rows[4]["rc"]))
            @ _translation(front_to_g1)
        )
        _a, _b, c, _d = matrix.ravel()
        efl = -1.0 / c if abs(c) > 1e-15 else None

    mirror_row = rows[1] if len(rows) > 1 else {}
    source_step = _solid_source_step(mirror_row).lower()

    doc = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
    index = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""

    checks = [
        ("layout file exists", LAYOUT_PATH.exists()),
        ("layout has nine rows", len(rows) == 9),
        ("layout is in Machine Vision menu", info["title"] in layouts.machine_vision_files),
        ("first row is Object", bool(surfs) and surfs[0] == "Object"),
        ("last row is Image", bool(surfs) and surfs[-1] == "Image"),
        (
            "row 1 is a promoted STEP optical solid",
            "OpticalSolidFaces" in _promoted_solid_advanced(mirror_row),
        ),
        ("promoted solid assigns a Mirror face", _has_mirror_face(mirror_row)),
        (
            "promoted solid sources the right-angle mirror STEP",
            "right_angle_mirror" in source_step or "87391" in source_step,
        ),
        (
            "blackbox chain follows the fold",
            len(names) > 3 and "front" in names[3].lower() and "datum" in names[3].lower(),
        ),
        ("blackbox EFL is 85 mm", efl is not None and abs(efl - 85.0) < 1e-3),
        ("preloads the lens STEP overlay", bool(settings.get("lens_step_path"))),
        ("preloads the camera STEP overlay", bool(settings.get("camera_step_path"))),
        ("keeps the camera model for FOV", settings.get("camera_model") == "Allied Vision hr25MCX"),
        ("docs page exists", DOC_PATH.exists() and "ELS-85" in doc),
        ("docs page is indexed", "machine_vision_azure_85_ra_mirror" in index),
    ]
    failures = [name for name, ok in checks if not ok]
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("AZURE ELS-85 mm right-angle-mirror layout validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "AZURE ELS-85 mm right-angle-mirror layout validation passed: "
        "Object -> promoted STEP right-angle mirror -> ELS-85 surrogate -> sensor, "
        "EFL=85 mm, lens + camera STEP overlays preloaded."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
