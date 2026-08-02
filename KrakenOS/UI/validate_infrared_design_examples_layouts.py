"""Validate the Infrared Design Examples Appendix B common layouts."""

from __future__ import annotations

import contextlib
import io
import math
from pathlib import Path

import KrakenOS as Kos

from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.layout_library import discover_layouts, layout_menu_category, load_python_data
from KrakenOS.common_optical_layouts._infrared_design_examples import (
    DESIGNS,
    OMITTED_SOURCE_DESIGNS,
    load_design,
)


LAYOUTS_DIR = Path(__file__).resolve().parents[1] / "common_optical_layouts"
EXPECTED_IDS = set(range(1, 16))
TITLE_PREFIX = "IDE B."
ALLOWED_GLASS = {"AIR", "MIRROR", "AMTIR1", "GERMANIUM", "ZNSE", "ZNS_IR"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _trace_reaches_image(surfaces: list[dict], wavelength_um: float) -> None:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        system = _build_system_from_specs(
            surfaces,
            build=0,
            apply_optical_solid_output_ports=False,
        )
        keeper = Kos.raykeeper(system)
        system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], float(wavelength_um))
        keeper.push()
    _require(len(system.SDT) == len(surfaces), "runtime surface count changed")
    _require(bool(system.SURFACE), "trace produced no surface events")
    _require(
        int(system.SURFACE[-1]) == len(surfaces) - 1,
        f"trace stopped at surface {system.SURFACE[-1]}, before Image {len(surfaces) - 1}",
    )
    _x, _y, z, _l, _m, _n = keeper.pick(-1)
    _require(bool(len(z)), "raykeeper produced no terminal intercept")
    _require(math.isfinite(float(z[-1])), "terminal intercept is not finite")


def main() -> None:
    _require(set(DESIGNS) == EXPECTED_IDS, "source catalog must contain designs 1-15")
    wrappers = sorted(LAYOUTS_DIR.glob("ide_b_*.py"))
    _require(len(wrappers) == 15, f"expected 15 wrapper modules, found {len(wrappers)}")

    discovery = discover_layouts(LAYOUTS_DIR)
    names = [name for name in discovery.layout_names if name.startswith(TITLE_PREFIX)]
    _require(len(names) == 15, f"expected 15 discovered IDE layouts, found {len(names)}")

    total_source_rows = 0
    total_ui_rows = 0
    for design_id in sorted(EXPECTED_IDS):
        title, expected_surfaces, expected_settings, system_data = load_design(design_id)
        _require(title in discovery.layout_files, f"design {design_id} was not discovered")
        path = discovery.layout_files[title]
        _require(path.name.startswith(f"ide_b_{design_id:02d}_"), f"design {design_id} wrapper mismatch")
        _require(
            layout_menu_category(title, path) == "Infrared Design Examples",
            f"design {design_id} is not in the dedicated menu category",
        )
        info = load_python_data(path)
        surfaces = info["surfaces"]
        settings = info["settings"]
        _require(surfaces == expected_surfaces, f"design {design_id} wrapper changed its prescription")
        _require(settings == expected_settings, f"design {design_id} wrapper changed its settings")
        _require(surfaces[0]["surface"] == "Object", f"design {design_id} lacks an Object row")
        _require(surfaces[-1]["surface"] == "Image", f"design {design_id} lacks an Image row")
        _require(
            system_data["pdf_pages"] == [DESIGNS[design_id]["pdf_page"]] * 2,
            f"design {design_id} source-page metadata changed",
        )
        for row in surfaces:
            for key in ("rc", "thickness", "diameter"):
                _require(math.isfinite(float(row[key])), f"design {design_id} has non-finite {key}")
            _require(float(row["diameter"]) > 0.0, f"design {design_id} has non-positive diameter")
            _require(str(row["glass"]) in ALLOWED_GLASS, f"design {design_id} has unknown glass {row['glass']}")
        _trace_reaches_image(surfaces, float(settings["wavelength"]))
        total_source_rows += len(DESIGNS[design_id]["rows"])
        total_ui_rows += len(surfaces)

    # Exact sentinels cover reflective folds, coincident stop/optic expansion,
    # a prose variant, all four doublets, the printed-thickness triplet, and the
    # scan-decimal/conic interpretation in the fifty-degree lens.
    _require(DESIGNS[1]["rows"][0]["radius"] == 181.2, "SEAL radius changed")
    _require(DESIGNS[1]["rows"][1]["k"] == -0.404, "SEAL conic changed")
    _require(DESIGNS[3]["image_radius"] == -27.0, "curved Schwarzschild image changed")
    _require(DESIGNS[4]["rows"][0]["k"] == 0.508e-7, "reflective Schmidt conic changed")
    _require(DESIGNS[5]["rows"][0]["radius"] == -9912.3925, "reoptimized corrector changed")
    _require(DESIGNS[6]["image_radius"] == -30.0022, "correctorless Schmidt image changed")
    _require(DESIGNS[8]["rows"][1]["thickness"] == 353.3419, "ZnSe inferred BFL changed")
    _require(DESIGNS[9]["rows"][2]["radius"] == -11.5083, "AMTIR/ZnS doublet changed")
    _require(DESIGNS[10]["rows"][2]["material"] == "AMTIR1", "Ge/AMTIR doublet changed")
    _require(DESIGNS[11]["rows"][3]["radius"] == -1.4730, "Ge/ZnS doublet changed")
    _require(DESIGNS[12]["rows"][2]["material"] == "ZNSE", "Ge/ZnSe doublet changed")
    _require(DESIGNS[13]["rows"][-1]["thickness"] == 20.2265, "meniscus triplet BFL changed")
    _require(all(row["thickness"] == 2.0 for row in DESIGNS[14]["rows"]), "Fischer 2-unit spacings changed")
    _require(DESIGNS[15]["rows"][1]["radius"] == 96.70241, "cold-lens decimal changed")
    _require(DESIGNS[15]["rows"][-1]["k"] == 0.743390, "cold-lens conic changed")

    reflective_stop_rows = load_design(4)[1]
    _require(
        any(row["surface"] == "Aperture" for row in reflective_stop_rows)
        and any(row["surface"] == "Mirror" and row["rc"] == -66752.0 for row in reflective_stop_rows),
        "coincident reflective stop was not expanded",
    )
    triplet_stop_rows = load_design(13)[1]
    _require(
        any(row["surface"] == "Aperture" for row in triplet_stop_rows)
        and any(row["glass"] == "GERMANIUM" and row["rc"] == 18.3021 for row in triplet_stop_rows),
        "coincident refractive stop was not expanded",
    )
    _require(len(OMITTED_SOURCE_DESIGNS) == 4, "incomplete-source audit changed")
    _require(
        all("no " in reason.lower() or "blank" in reason.lower() for reason in OMITTED_SOURCE_DESIGNS.values()),
        "an omitted design lacks a numerical-incompleteness reason",
    )

    print(
        "Infrared Design Examples layout validation passed: "
        f"designs=15, source_rows={total_source_rows}, ui_rows={total_ui_rows}, "
        f"documented_omissions={len(OMITTED_SOURCE_DESIGNS)}"
    )


if __name__ == "__main__":
    main()
