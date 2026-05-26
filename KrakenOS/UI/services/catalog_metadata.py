"""Metal and stock-lens catalog metadata helpers."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path

import KrakenOS as Kos

KRAKEN_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = KRAKEN_DIR.parent
METAL_CATALOG_DIR = KRAKEN_DIR / "Cat"
LENSCAT_DIR = KRAKEN_DIR / "LensCat"
ATTACHMENT_DIR = PROJECT_ROOT / "attachment"
LEGACY_TESTING_DIR = PROJECT_ROOT / "testing"


def _preferred_existing_path(*candidates: Path | str) -> Path:
    paths = [Path(candidate).expanduser() for candidate in candidates]
    for path in paths:
        if path.exists():
            return path
    return paths[0]


DEFAULT_METAL_CATALOG_NAME = "Alum"
DEFAULT_METAL_CATALOG_PATH = METAL_CATALOG_DIR / "Alum.csv"
STOCK_LENS_CATALOG_SPECS = (
    (
        "Edmund Optics 2019 (attachment)",
        _preferred_existing_path(
            ATTACHMENT_DIR / "Edmund Optics 2019.ZMF",
            LEGACY_TESTING_DIR / "Edmund Optics 2019.ZMF",
        ),
    ),
    (
        "Thorlabs May 2024 (attachment)",
        _preferred_existing_path(
            ATTACHMENT_DIR / "THORLABS_MAY_2024.ZMF",
            LEGACY_TESTING_DIR / "THORLABS_MAY_2024.ZMF",
        ),
    ),
    ("Edmund Optics 2019 (bundled)", LENSCAT_DIR / "Edmund Optics 2019.ZMF"),
    ("Thorlabs legacy (bundled)", LENSCAT_DIR / "THORLABS.ZMF"),
)

_STOCK_LENS_CATALOG_CACHE: dict[str, dict[str, object]] = {}


def _metal_catalog_type_for_path(path: Path | str) -> int:
    try:
        with Path(path).expanduser().open("r", encoding="utf-8", errors="ignore") as handle:
            for _ in range(8):
                line = handle.readline()
                if not line:
                    break
                if line.strip().lower() == "wl,n":
                    return 1
    except Exception:
        pass
    return 0


def _normalize_metal_catalog_specs(value) -> list[dict[str, object]]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        if isinstance(item, dict):
            path_value = item.get("path", item.get("file", item.get("filename", "")))
            name_value = item.get("name", "")
            type_value = item.get("type", item.get("format", None))
        else:
            path_value = item
            name_value = ""
            type_value = None
        path_text = str(path_value or "").strip()
        if not path_text:
            continue
        path = Path(path_text).expanduser()
        name = str(name_value or path.stem).strip() or path.stem
        if path.name.lower() == DEFAULT_METAL_CATALOG_PATH.name.lower() and name.lower() == DEFAULT_METAL_CATALOG_NAME.lower():
            continue
        try:
            catalog_type = int(type_value) if type_value is not None else _metal_catalog_type_for_path(path)
        except Exception:
            catalog_type = _metal_catalog_type_for_path(path)
        catalog_type = 1 if catalog_type == 1 else 0
        token = (str(path), name.lower())
        if token in seen:
            continue
        seen.add(token)
        normalized.append({"name": name, "path": str(path), "type": catalog_type})
    return normalized


def _metal_catalog_entries(catalogs) -> list[dict[str, object]]:
    return [
        {
            "name": DEFAULT_METAL_CATALOG_NAME,
            "path": str(DEFAULT_METAL_CATALOG_PATH),
            "type": 0,
            "builtin": True,
        },
        *_normalize_metal_catalog_specs(catalogs),
    ]


def _metal_catalog_signature(catalogs) -> tuple[tuple[str, str, int], ...]:
    return tuple(
        (str(item["name"]), str(item["path"]), int(item["type"]))
        for item in _normalize_metal_catalog_specs(catalogs)
    )


def _metal_catalogs_from_row_specs(row_specs: list[dict]) -> list[dict[str, object]]:
    for spec in row_specs:
        catalogs = spec.get("_metal_catalogs")
        if catalogs is not None:
            return _normalize_metal_catalog_specs(catalogs)
    return []


def _load_metal_catalogs_into_setup(setup, catalogs) -> None:
    loaded_names = {str(name).strip().lower() for name in getattr(setup, "Name_met", [])}
    for catalog in _normalize_metal_catalog_specs(catalogs):
        path = Path(str(catalog["path"])).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Metal catalog not found: {path}")
        name = str(catalog["name"]).strip() or path.stem
        if name.lower() in loaded_names:
            continue
        setup.LoadMetal(str(path), name, int(catalog["type"]))
        loaded_names.add(name.lower())


def _available_stock_lens_catalogs() -> dict[str, Path]:
    catalogs: dict[str, Path] = {}
    for label, path in STOCK_LENS_CATALOG_SPECS:
        if path.exists():
            catalogs[label] = path
    return catalogs


def _load_stock_lens_catalog(path: Path | str) -> dict:
    resolved = str(Path(path).expanduser().resolve())
    cached = _STOCK_LENS_CATALOG_CACHE.get(resolved)
    if isinstance(cached, dict):
        return cached
    with io.StringIO() as stdout_buf, redirect_stdout(stdout_buf):
        catalog = Kos.zmf2dict([resolved])
    _STOCK_LENS_CATALOG_CACHE[resolved] = catalog
    return catalog


def _catalog_surface_keys(catalog_item: dict) -> list[str]:
    def _surface_number(key: str) -> int:
        try:
            return int(str(key).split()[-1])
        except Exception:
            return 0

    return sorted((key for key in catalog_item if str(key).startswith("SUFR")), key=_surface_number)


def _stock_lens_summary(part_number: str, catalog_item: dict) -> dict[str, object]:
    surface_keys = _catalog_surface_keys(catalog_item)
    diameters = []
    for key in surface_keys:
        try:
            diameter = float(catalog_item[key].get("Diameter", 0.0))
        except Exception:
            diameter = 0.0
        if diameter > 0.0:
            diameters.append(diameter)
    return {
        "part_number": str(part_number),
        "description": str(catalog_item.get("description", "") or "").strip(),
        "surface_count": len(surface_keys),
        "diameter": max(diameters) if diameters else 0.0,
    }
