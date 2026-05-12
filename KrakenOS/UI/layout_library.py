"""Layout/example discovery helpers for the KrakenOS UI.

This module keeps source-file inventory and menu categorization out of the
Tk editor.  It deliberately avoids importing ``layout_editor`` so it can be
validated without constructing a GUI.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path


LAYOUT_CATEGORY_ORDER = (
    "Starter Lenses",
    "Imported / Camera Lenses",
    "Beam Splitters / Folds",
    "Sources / Illumination",
    "Advanced Surfaces / Materials",
    "Analysis / Diagnostics",
)

EXAMPLE_CATEGORY_ORDER = (
    "Starter Lens Examples",
    "Non-Sequential / Advanced Surfaces",
    "Beam Splitters / Interferometers",
    "Sources / Gaussian",
    "Prisms / Gratings / Spectrometers",
    "Telescopes / Instruments",
    "Optimization / System / Data",
    "Other Examples",
)

ZEMAX_PRESCRIPTION_SUFFIXES = frozenset({".zmx"})


@dataclass(frozen=True)
class LayoutDiscovery:
    layout_files: dict[str, Path]
    layout_names: list[str]
    machine_vision_files: dict[str, Path]
    machine_vision_names: list[str]


@dataclass(frozen=True)
class ExampleDiscovery:
    example_files: dict[str, Path]
    example_names: list[str]
    zemax_example_files: dict[str, Path]


def load_python_data(path: Path) -> dict:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load layout file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    title = getattr(module, "TITLE", path.stem.replace("_", " ").title())
    surfaces = getattr(module, "SURFACES", None)
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError(f"{path.name} does not define a non-empty SURFACES list.")
    settings = getattr(module, "SETTINGS", {})
    if not isinstance(settings, dict):
        settings = {}
    return {"title": title, "surfaces": surfaces, "settings": settings}


def load_python_title(path: Path) -> str:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load layout file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "TITLE", path.stem.replace("_", " ").title())


def layout_menu_category(name: str, path: Path | None = None) -> str:
    stem = path.stem if path is not None else ""
    haystack = f"{name} {stem}".lower()
    if any(
        token in haystack
        for token in (
            "wavefront",
            "wide_field",
            "wide field",
            "psf",
            "spot map",
            "rtheta",
            "r-theta",
            "atmospheric",
        )
    ):
        return "Analysis / Diagnostics"
    if any(
        token in haystack
        for token in (
            "beam_splitter",
            "beam splitter",
            "interferometer",
            "michelson",
            "mach-zehnder",
            "mach_zehnder",
            "twyman",
            "mirror",
            "nonseq",
            "non-sequential",
            "branch_tree",
            "branch tree",
        )
    ):
        return "Beam Splitters / Folds"
    if any(
        token in haystack
        for token in (
            "source",
            "illumination",
            "gaussian_beam",
            "gaussian beam",
            "laser",
            "galvo",
            "f-theta",
            "f_theta",
            "scanner",
        )
    ):
        return "Sources / Illumination"
    if any(
        token in haystack
        for token in (
            "coating",
            "metal",
            "surface",
            "diffuse",
            "scatter",
            "brdf",
            "zernike",
            "error map",
            "native variable",
        )
    ):
        return "Advanced Surfaces / Materials"
    if any(token in haystack for token in ("zemax", "machine_vision", "machine vision")):
        return "Imported / Camera Lenses"
    return "Starter Lenses"


def example_menu_category(name: str, path: Path | None = None) -> str:
    stem = path.stem if path is not None else str(name)
    haystack = f"{name} {stem}".lower()
    if any(token in haystack for token in ("beam_splitter", "beam splitter", "michelson", "twyman", "mach_zehnder", "mach-")):
        return "Beam Splitters / Interferometers"
    if any(
        token in haystack
        for token in (
            "gaussian",
            "source_distribution",
            "source distribution",
            "laser",
            "galvo",
            "f-theta",
            "f_theta",
            "scanner",
        )
    ):
        return "Sources / Gaussian"
    if any(token in haystack for token in ("prism", "grating", "czerny", "echelle", "abbe", "dispersion", "fresnel", "ronchi")):
        return "Prisms / Gratings / Spectrometers"
    if any(token in haystack for token in ("stl", "extra_shape", "extrashape", "uda", "coating", "nonsec", "non_sec", "mirror", "parabole")):
        return "Non-Sequential / Advanced Surfaces"
    if any(token in haystack for token in ("tel_2m", "telescope", "spyder", "atmospheric")):
        return "Telescopes / Instruments"
    if any(token in haystack for token in ("optimization", "commands", "pickle", "catalog", "zemax", "spruce")):
        return "Optimization / System / Data"
    if any(token in haystack for token in ("doublet", "perfect_lens", "perfect lens", "axicon", "sphere", "ray")):
        return "Starter Lens Examples"
    return "Other Examples"


def example_file_has_import_side_effects(code: str) -> bool:
    for line in code.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.search(r"\bopen\s*\([^)]*,\s*['\"][^'\"]*[wax+][^'\"]*['\"]", stripped):
            return True
        if ".write_text(" in stripped or ".write_bytes(" in stripped:
            return True
    return False


def python_code_defines_layout_data(code: str) -> bool:
    """Return True when code assigns top-level SURFACES and SETTINGS names."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    assigned: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)
    return {"SURFACES", "SETTINGS"}.issubset(assigned)


def python_code_imports_common_layout(code: str) -> bool:
    """Return True when an example is a wrapper around ``common_optical_layouts``."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            if module == "KrakenOS.common_optical_layouts" or module.startswith("KrakenOS.common_optical_layouts."):
                return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = str(alias.name or "")
                if name == "KrakenOS.common_optical_layouts" or name.startswith("KrakenOS.common_optical_layouts."):
                    return True
    return False


def example_file_is_menu_loadable(path: Path) -> bool:
    try:
        code = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    if example_file_has_import_side_effects(code):
        return False
    if python_code_imports_common_layout(code):
        return False
    if python_code_defines_layout_data(code):
        return True
    return bool(re.search(r"\bKos\s*\.\s*system\s*\(", code))


def discover_zemax_prescriptions(
    root: Path,
    *,
    suffixes: set[str] | frozenset[str] = ZEMAX_PRESCRIPTION_SUFFIXES,
) -> dict[str, Path]:
    if not root.exists():
        return {}
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix().lower()):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        try:
            label = path.relative_to(root).as_posix()
        except ValueError:
            label = path.name
        files[label] = path
    return files


def discover_layouts(
    layouts_dir: Path,
    *,
    default_layout_title: str = "Doublet Lens",
) -> LayoutDiscovery:
    layout_files: dict[str, Path] = {}
    machine_vision_files: dict[str, Path] = {}
    for path in sorted(layouts_dir.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            title = load_python_title(path)
        except Exception:
            continue
        layout_files[title] = path
        if path.stem.startswith("machine_vision_"):
            machine_vision_files[title] = path

    layout_names = sorted(
        (name for name in layout_files if name not in machine_vision_files),
        key=lambda name: (0 if name == default_layout_title else 1, name.lower()),
    )
    return LayoutDiscovery(
        layout_files=layout_files,
        layout_names=layout_names,
        machine_vision_files=machine_vision_files,
        machine_vision_names=sorted(machine_vision_files, key=str.lower),
    )


def discover_examples(examples_dir: Path, zemax_root: Path) -> ExampleDiscovery:
    example_files: dict[str, Path] = {}
    for path in sorted(examples_dir.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        if example_file_is_menu_loadable(path):
            example_files[path.stem] = path
    return ExampleDiscovery(
        example_files=example_files,
        example_names=sorted(example_files),
        zemax_example_files=discover_zemax_prescriptions(zemax_root),
    )
