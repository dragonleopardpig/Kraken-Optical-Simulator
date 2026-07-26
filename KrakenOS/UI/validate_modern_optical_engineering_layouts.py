"""Validate the 62 Modern Optical Engineering Chapter 19 common layouts."""

from __future__ import annotations

import math
from pathlib import Path

from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.layout_library import discover_layouts, layout_menu_category, load_python_data
from KrakenOS.common_optical_layouts._modern_optical_engineering_ch19 import DESIGNS, load_design


LAYOUTS_DIR = Path(__file__).resolve().parents[1] / "common_optical_layouts"
EXPECTED_FIGURES = set(range(1, 63))
TITLE_PREFIX = "MOE 19."


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    _require(set(DESIGNS) == EXPECTED_FIGURES, "source catalog must contain figures 19.1-19.62")
    wrappers = sorted(LAYOUTS_DIR.glob("moe_19_[0-9][0-9].py"))
    _require(len(wrappers) == 62, f"expected 62 wrapper modules, found {len(wrappers)}")

    discovery = discover_layouts(LAYOUTS_DIR)
    names = [name for name in discovery.layout_names if name.startswith(TITLE_PREFIX)]
    _require(len(names) == 62, f"expected 62 discovered MOE layouts, found {len(names)}")

    total_source_rows = 0
    total_ui_rows = 0
    for figure in sorted(EXPECTED_FIGURES):
        title, expected_surfaces, expected_settings, system_data = load_design(figure)
        _require(title in discovery.layout_files, f"figure 19.{figure} was not discovered")
        path = discovery.layout_files[title]
        _require(path.name == f"moe_19_{figure:02d}.py", f"figure 19.{figure} wrapper mismatch")
        _require(
            layout_menu_category(title, path) == "Modern Optical Engineering",
            f"figure 19.{figure} is not in the dedicated menu category",
        )
        info = load_python_data(path)
        surfaces = info["surfaces"]
        settings = info["settings"]
        _require(surfaces == expected_surfaces, f"figure 19.{figure} wrapper changed its prescription")
        _require(settings == expected_settings, f"figure 19.{figure} wrapper changed its settings")
        _require(surfaces[0]["surface"] == "Object", f"figure 19.{figure} lacks an Object row")
        _require(surfaces[-1]["surface"] == "Image", f"figure 19.{figure} lacks an Image row")
        _require(
            system_data["pdf_pages"][0] <= system_data["pdf_pages"][1],
            f"figure 19.{figure} has invalid source-page metadata",
        )
        for row in surfaces:
            for key in ("rc", "thickness", "diameter"):
                _require(math.isfinite(float(row[key])), f"figure 19.{figure} has non-finite {key}")
            _require(float(row["diameter"]) > 0.0, f"figure 19.{figure} has a non-positive UI diameter")
            glass = str(row["glass"])
            _require(
                glass in {"AIR", "MIRROR"} or glass.startswith(("nvk,", "manual_n,")),
                f"figure 19.{figure} has a non-embedded material: {glass}",
            )
        system = _build_system_from_specs(
            surfaces,
            build=0,
            apply_optical_solid_output_ports=False,
        )
        _require(
            len(system.SDT) == len(surfaces),
            f"figure 19.{figure} runtime surface count changed",
        )
        total_source_rows += len(DESIGNS[figure]["rows"])
        total_ui_rows += len(surfaces)

    # Exact sentinels cover ordinary refractive, polynomial-asphere, catadioptric,
    # coincident-stop/glass, curved-image, and Smith-cc conversion paths.
    _require(DESIGNS[1]["rows"][0]["radius"] == 50.098, "figure 19.1 radius sentinel changed")
    _require(DESIGNS[14]["rows"][0]["sa"] == 448.4, "figure 19.14 semi-aperture sentinel changed")
    _require(DESIGNS[43]["rows"][0]["k"] == 1.326, "figure 19.43 kappa sentinel changed")
    _require(
        DESIGNS[43]["rows"][0]["asphere"][-1] == -4.346e-19,
        "figure 19.43 AG sentinel changed",
    )
    _require(DESIGNS[52]["rows"][2]["thickness"] == -99.45, "figure 19.52 fold spacing changed")
    _require(DESIGNS[60]["rows"][-1]["image_surface"], "figure 19.60 curved image lost")
    figure_54_surfaces = load_design(54)[1]
    _require(
        any(row["surface"] == "Aperture" for row in figure_54_surfaces)
        and any(row["glass"].startswith("nvk,1.517,64.2") for row in figure_54_surfaces),
        "figure 19.54 coincident stop/BK7 surface was not expanded",
    )
    figure_61_surfaces = load_design(61)[1]
    _require(abs(figure_61_surfaces[1]["k"] - 4.8284) < 1e-12, "figure 19.61 cc-to-k conversion changed")
    _require(
        abs(figure_61_surfaces[2]["k"] - (-0.82843)) < 1e-12,
        "figure 19.61 secondary cc-to-k conversion changed",
    )
    _require(load_design(43)[3]["pdf_pages"] == [593, 594], "figure 19.43 two-page source mapping changed")
    _require(load_design(62)[3]["pdf_pages"] == [613, 613], "figure 19.62 source mapping changed")

    print(
        "Modern Optical Engineering layout validation passed: "
        f"designs=62, source_rows={total_source_rows}, ui_rows={total_ui_rows}"
    )


if __name__ == "__main__":
    main()
