from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.layout_library import (
    discover_examples,
    discover_layouts,
    discover_zemax_prescriptions,
    example_file_has_import_side_effects,
    example_file_is_menu_loadable,
    example_menu_category,
    layout_menu_category,
    load_python_data,
    python_code_imports_common_layout,
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    kraken_root = Path(__file__).resolve().parents[1]
    project_root = kraken_root.parent
    layouts_dir = kraken_root / "common_optical_layouts"
    examples_dir = kraken_root / "Examples"
    zemax_root = project_root / "attachment" / "zemax"

    layouts = discover_layouts(layouts_dir, default_layout_title="Doublet Lens")
    _require(layouts.layout_names, "no common layouts discovered")
    _require(layouts.layout_names[0] == "Doublet Lens", "default common layout is not first")
    _require("Doublet Lens" in layouts.layout_files, "Doublet Lens layout missing")
    _require(layouts.machine_vision_names, "machine-vision layout menu is empty")
    _require(
        all(not layouts.layout_files[name].stem.startswith("machine_vision_") for name in layouts.layout_names),
        "machine-vision layouts leaked into the common layout menu",
    )

    doublet = layouts.layout_files["Doublet Lens"]
    doublet_info = load_python_data(doublet)
    _require(len(doublet_info["surfaces"]) >= 2, "Doublet Lens did not load at least Object/Image surfaces")
    _require(layout_menu_category("Doublet Lens", doublet) == "Starter Lenses", "Doublet category changed")
    _require(
        layout_menu_category("Michelson Interferometer Ray Only", layouts.layout_files.get("Michelson Interferometer Ray Only"))
        == "Beam Splitters / Folds",
        "Michelson layout category changed",
    )

    examples = discover_examples(examples_dir, zemax_root)
    _require("Examp_Doublet_Lens" in examples.example_files, "Examp_Doublet_Lens missing from examples")
    _require(example_file_is_menu_loadable(examples.example_files["Examp_Doublet_Lens"]), "Doublet example is not menu-loadable")
    _require(
        example_menu_category("Examp_Michelson_Interferometer", examples.example_files.get("Examp_Michelson_Interferometer"))
        == "Beam Splitters / Interferometers",
        "Michelson example category changed",
    )
    _require(
        example_file_has_import_side_effects("open('generated.txt', 'w').write('x')"),
        "write-mode side-effect screening failed",
    )
    galvo_duplicate = examples_dir / "Examp_Galvo_FTheta_Laser_Scanner.py"
    _require(python_code_imports_common_layout(galvo_duplicate.read_text(encoding="utf-8")), "common-layout wrapper detection missed Galvo example")
    _require(
        not example_file_is_menu_loadable(galvo_duplicate),
        "common-layout Galvo wrapper leaked into the Examples menu",
    )
    leaked_wrappers = [
        path.name
        for path in sorted(examples_dir.glob("*.py"))
        if python_code_imports_common_layout(path.read_text(encoding="utf-8", errors="ignore"))
        and example_file_is_menu_loadable(path)
    ]
    _require(
        not leaked_wrappers,
        "common-layout wrappers leaked into the Examples menu: " + ", ".join(leaked_wrappers),
    )
    cooke_helper = examples_dir / "Examp_Cooke_Triplet_Optimization_Case_Study.py"
    _require(
        not example_file_is_menu_loadable(cooke_helper),
        "analysis helper without top-level SURFACES/SETTINGS leaked into the Examples menu",
    )

    zemax_files = discover_zemax_prescriptions(zemax_root)
    _require(isinstance(zemax_files, dict), "Zemax discovery did not return a dictionary")

    print(
        "Layout library validation passed: "
        f"layouts={len(layouts.layout_names)}, "
        f"machine_vision={len(layouts.machine_vision_names)}, "
        f"examples={len(examples.example_names)}, "
        f"zemax={len(zemax_files)}"
    )


if __name__ == "__main__":
    main()
