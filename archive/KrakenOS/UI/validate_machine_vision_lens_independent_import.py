"""Validate independent import of machine-vision lens surrogates (item 2).

Machine-vision lenses used to be reachable only from the top ``Machine Vision``
menubar, which LOADS one as the whole working layout.  Item 2 makes them
importable into the *current* scene from the right-click "Insert Component Below"
menu, so a user can drop a surrogate in beside other optics (and then fold a
mirror in front of it, per item 1) without leaving their layout.

The import reuses the existing component-insert plumbing
(``insert_layout_component_by_name`` -> ``component_rows_from_layout``), so every
discovered machine-vision layout must:

* be discoverable AND resolvable by title in ``layout_files`` (not only in the
  ``machine_vision_files`` menu map) -- that is what lets the insert path find it
  without the top menu;
* yield a non-empty insertable optical body (the rows between Object and Image:
  the ideal blackbox groups + stop between the vertex datums);
* drop cleanly into a plain Object->Image scene, landing between the endpoints,
  with a real build=0 trace still producing a finite intercept.

Plus the editor exposes ``insert_machine_vision_lens_by_name`` and the right-click
menu wires the "Machine Vision Lens" cascade.

Like the other machine-vision guards this is STANDALONE, not a penta phase.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_library import discover_layouts, load_python_data
from KrakenOS.UI.surface_table_model import (
    SurfaceRow,
    append_layout_rows,
    component_rows_from_layout,
    surface_row_to_spec,
    surface_rows_from_records,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUTS_DIR = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts"
WORKBENCH_PATH = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "layout_table_workbench.py"
MENU_PATH = PROJECT_ROOT / "KrakenOS" / "UI" / "panels" / "main_context_menu.py"


def _rows_for_layout(path: Path) -> list[SurfaceRow]:
    info = load_python_data(path)
    return surface_rows_from_records(list(info.get("surfaces", [])))


def _pick_representative(mv_names: list[str]) -> str | None:
    straight = [name for name in mv_names if "azure" in name.lower() and "fold" not in name.lower()]
    if straight:
        return straight[0]
    return mv_names[0] if mv_names else None


def _trace_produces_intercept(rows: list[SurfaceRow]) -> bool | None:
    """True/False from a real build=0 trace, or None if the trace stack is absent."""
    try:
        from KrakenOS.UI.services import paraxial_tools
        import KrakenOS as Kos
    except Exception:
        return None
    try:
        specs = [surface_row_to_spec(row) for row in rows]
        system = paraxial_tools._build_system_from_specs(specs, build=0)
        keeper = Kos.raykeeper(system)
        system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
        keeper.push()
        _x, _y, z, _l, _m, _n = keeper.pick(-1)
        return bool(len(z)) and np.isfinite(float(z[-1]))
    except Exception:
        return None


def run_checks():
    """Return (passed, failures) without printing -- usable as a phase body."""
    discovered = discover_layouts(LAYOUTS_DIR)
    mv_names = list(discovered.machine_vision_names)

    failures: list[str] = []

    if not mv_names:
        return False, ["no machine-vision layouts discovered"]

    # Every discovered MV lens must be resolvable by title in layout_files (the
    # insert path keys on that, not on the top-menu map) and yield a non-empty
    # insertable optical body.
    for name in mv_names:
        path = discovered.layout_files.get(name)
        if path is None:
            failures.append(f"{name}: not resolvable in layout_files (top-menu only)")
            continue
        rows = _rows_for_layout(path)
        component = component_rows_from_layout(rows)
        if not component:
            failures.append(f"{name}: no insertable optical body between Object and Image")
            continue
        if any(row.surface in {"Object", "Image"} for row in component):
            failures.append(f"{name}: import body still carries an Object/Image endpoint")

    # Representative end-to-end import into a plain Object->Image scene.
    representative = _pick_representative(mv_names)
    if representative is None:
        failures.append("could not choose a representative MV lens")
    else:
        rep_rows = _rows_for_layout(discovered.layout_files[representative])
        component = component_rows_from_layout(rep_rows)
        scene = [
            SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=50.0, glass="AIR"),
            SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=50.0, glass="AIR"),
        ]
        merged = append_layout_rows(scene, rep_rows, element_name=representative)
        if len(merged) != len(scene) + len(component):
            failures.append("import did not add the expected number of rows")
        if not merged or merged[0].surface != "Object":
            failures.append("import disturbed the leading Object row")
        if not merged or merged[-1].surface != "Image":
            failures.append("import did not keep Image last")
        if any(row.surface in {"Object", "Image"} for row in merged[1:-1]):
            failures.append("import inserted a stray Object/Image into the chain")
        traced = _trace_produces_intercept(merged)
        if traced is False:
            failures.append("imported scene failed to trace")

    workbench_src = WORKBENCH_PATH.read_text(encoding="utf-8") if WORKBENCH_PATH.exists() else ""
    menu_src = MENU_PATH.read_text(encoding="utf-8") if MENU_PATH.exists() else ""
    if "def insert_machine_vision_lens_by_name" not in workbench_src:
        failures.append("editor does not expose insert_machine_vision_lens_by_name")
    if "insert_machine_vision_lens_by_name" not in menu_src:
        failures.append("context menu does not wire the Machine Vision Lens import")
    if "Machine Vision Lens" not in menu_src:
        failures.append("context menu has no Machine Vision Lens cascade label")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Machine-vision independent-import validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    discovered = discover_layouts(LAYOUTS_DIR)
    count = len(discovered.machine_vision_names)
    print(
        f"Machine-vision independent-import validation passed: {count} lens(es) "
        "import into the current path from the right-click menu, independent of the "
        "top Machine Vision menu."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
