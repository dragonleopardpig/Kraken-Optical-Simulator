"""Validate the folded AZURE ELS-85/4.5V16K machine-vision layout.

The folded layout is the straight ``machine_vision_85mm_azure_datasheet_05x_20x``
surrogate with a single 45-degree sequential ``Mirror`` inserted ahead of the lens, so
the ELS-85 imaging chain + sensor sit on the reflected branch.  This guard checks that:

* the layout is discoverable in the Machine Vision menu and has the expected 8 rows
  (Object -> Mirror -> front datum -> two blackbox groups -> stop -> rear datum -> image);
* the fold mirror is a real reflector (``glass="MIRROR"``, ``|tilt_x| == 45``);
* the fold split (object->mirror + mirror->front vertex) still equals the straight
  surrogate's 1X object working distance, so the 1X conjugate is preserved;
* the paraxial ABCD matrix of the post-mirror lens chain still reproduces EFL = 85 mm;
* a real KrakenOS sequential trace (build=0, no GL) folds the axis -- the on-axis ray
  reaches the sensor on the reflected (+Y) branch, well off the straight Z axis;
* the straight-axis CAD overlays are dropped (the overlay aligner cannot fold a mesh)
  while the camera model is kept so the image format stays camera/FOV-driven;
* the docs page exists and is indexed.

Like the straight AZ85 surrogate guard this is a STANDALONE check, not a penta phase.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_library import discover_layouts, load_python_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUTS_DIR = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts"
LAYOUT_PATH = LAYOUTS_DIR / "machine_vision_85mm_azure_datasheet_05x_20x_folded.py"
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "machine_vision_azure_85_folded.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"


def _translation(distance: float) -> np.ndarray:
    return np.asarray([[1.0, distance], [0.0, 1.0]], dtype=float)


def _thin_lens(focal_length: float) -> np.ndarray:
    return np.asarray([[1.0, 0.0], [-1.0 / focal_length, 1.0]], dtype=float)


def _folded_image_branch_y() -> float | None:
    """Mean image-plane global Y from a real build=0 sequential trace, or None if the
    headless trace stack is unavailable."""
    try:
        from KrakenOS.UI.services import paraxial_tools
        import KrakenOS as Kos
    except Exception:
        return None
    try:
        info = load_python_data(LAYOUT_PATH)
        system = paraxial_tools._build_system_from_specs(info["surfaces"], build=0)
        keeper = Kos.raykeeper(system)
        ys: list[float] = []
        for x0, y0 in [(0.0, 0.0), (3.0, 0.0), (0.0, 3.0), (-3.0, 0.0), (0.0, -3.0)]:
            system.Trace([x0, y0, 0.0], [0.0, 0.0, 1.0], 0.55)
            keeper.push()
            _x, y, _z, _l, _m, _n = keeper.pick(-1)
            ys.append(float(y[-1]))
        if not ys:
            return None
        return float(np.mean(ys))
    except Exception:
        return None


def run_checks():
    """Return (passed, failures) without printing -- usable as a phase body."""
    base = importlib.import_module(
        "KrakenOS.common_optical_layouts.machine_vision_85mm_azure_datasheet_05x_20x"
    )
    info = load_python_data(LAYOUT_PATH)
    layouts = discover_layouts(LAYOUTS_DIR)
    rows = info["surfaces"]
    settings = dict(info.get("settings", {}))
    names = [str(r.get("name", "")) for r in rows]
    surfs = [str(r.get("surface", "")) for r in rows]

    # Paraxial EFL from the lens chain that FOLLOWS the mirror.
    # rows: 0 Object, 1 Mirror, 2 FrontDatum, 3 Group1, 4 Stop, 5 Group2, 6 RearDatum, 7 Image
    efl = None
    span = None
    if len(rows) == 8 and surfs[3] == "Thin Lens" and surfs[5] == "Thin Lens":
        group_1_z = float(rows[2]["thickness"])
        g1_to_stop = float(rows[3]["thickness"])
        stop_to_g2 = float(rows[4]["thickness"])
        g2_to_rear = float(rows[5]["thickness"])
        span = group_1_z + g1_to_stop + stop_to_g2 + g2_to_rear
        matrix = (
            _translation(g2_to_rear)
            @ _thin_lens(float(rows[5]["rc"]))
            @ _translation(stop_to_g2 + g1_to_stop)
            @ _thin_lens(float(rows[3]["rc"]))
            @ _translation(group_1_z)
        )
        a, _b, c, _d = matrix.ravel()
        efl = -1.0 / c if abs(c) > 1e-15 else None

    fold_split = float(rows[0]["thickness"]) + float(rows[1]["thickness"]) if len(rows) >= 2 else None
    image_branch_y = _folded_image_branch_y()

    doc = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
    index = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""

    checks = [
        ("layout file exists", LAYOUT_PATH.exists()),
        ("layout has eight rows", len(rows) == 8),
        ("layout is in Machine Vision menu", info["title"] in layouts.machine_vision_files),
        ("first row is Object", bool(surfs) and surfs[0] == "Object"),
        ("second row is the fold Mirror", len(surfs) > 1 and surfs[1] == "Mirror"),
        ("fold mirror is a reflector", len(rows) > 1 and str(rows[1].get("glass")) == "MIRROR"),
        (
            "fold mirror tilts 45 degrees",
            len(rows) > 1 and abs(abs(float(rows[1].get("tilt_x", 0.0))) - 45.0) < 1e-9,
        ),
        (
            "lens chain follows the mirror",
            len(names) > 2 and "front" in names[2].lower() and "datum" in names[2].lower(),
        ),
        ("last row is Image", bool(surfs) and surfs[-1] == "Image"),
        (
            "fold preserves the 1X object working distance",
            fold_split is not None
            and abs(fold_split - float(base.OBJECT_TO_FRONT_VERTEX_1X)) < 1e-6,
        ),
        ("lens span matches the straight surrogate", span is not None and abs(span - float(base.FRONT_VERTEX_TO_REAR_VERTEX)) < 1e-6),
        ("post-mirror EFL is 85 mm", efl is not None and abs(efl - 85.0) < 1e-6),
        (
            "trace folds the axis to the reflected branch",
            image_branch_y is not None and abs(image_branch_y) > 50.0,
        ),
        ("does not preload the lens STEP overlay", settings.get("lens_step_path") == ""),
        ("does not preload the camera STEP overlay", settings.get("camera_step_path") == ""),
        ("keeps the camera model for FOV", settings.get("camera_model") == "Allied Vision hr25MCX"),
        ("docs page exists", DOC_PATH.exists() and "ELS-85" in doc),
        ("docs page is indexed", "machine_vision_azure_85_folded" in index),
    ]
    failures = [name for name, ok in checks if not ok]
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("AZURE ELS-85 mm folded layout validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    branch_y = _folded_image_branch_y()
    branch = "unavailable" if branch_y is None else f"{branch_y:+.1f} mm"
    print(
        "AZURE ELS-85 mm folded layout validation passed: "
        "Object -> 45deg fold -> ELS-85 surrogate -> sensor, EFL=85 mm, "
        f"image on the reflected branch (mean Y={branch})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
