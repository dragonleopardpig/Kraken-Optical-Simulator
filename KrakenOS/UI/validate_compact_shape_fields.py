from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from KrakenOS.Optimization.variables import OpticalVariable
from KrakenOS.UI.layout_editor import (
    ADVANCED_ROW_SHAPE_FIELDS,
    FIELDS,
    KrakenLayoutEditor,
    SurfaceRow,
    _build_system_from_specs,
)


@dataclass
class CompactShapeFieldCheck:
    check: str
    ok: bool
    detail: str


def _row_specs(rows: list[SurfaceRow]) -> list[dict[str, object]]:
    return [asdict(row) for row in rows]


def validate_compact_shape_fields() -> list[CompactShapeFieldCheck]:
    object_row = SurfaceRow(surface="Object", name="Object", thickness=25.0, diameter=20.0, glass="AIR")
    shape_row = SurfaceRow(
        surface="Standard",
        name="Conic axicon",
        glass="BK7",
        rc=75.0,
        k=-1.25,
        axicon=2.5,
        thickness=10.0,
        diameter=20.0,
    )
    image_row = SurfaceRow(surface="Image", name="Image", diameter=20.0, glass="AIR")
    system = _build_system_from_specs(_row_specs([object_row, shape_row, image_row]))
    kraken_shape = system.SDT[1]

    variable = OpticalVariable(1, "k", -2.0, 0.0, name="Conic")
    initial_k = KrakenLayoutEditor._optimization_value_from_row(shape_row, variable)
    optimized_row = SurfaceRow(**asdict(shape_row))
    KrakenLayoutEditor._apply_optimization_value_to_row(optimized_row, variable, -0.75)

    field_names = tuple(field for field, _label, _help in ADVANCED_ROW_SHAPE_FIELDS)
    return [
        CompactShapeFieldCheck(
            "main prescription table hides uncommon row-shape fields",
            "k" not in FIELDS and "axicon" not in FIELDS,
            f"visible_fields={FIELDS}",
        ),
        CompactShapeFieldCheck(
            "advanced surface dialog exposes row-shape fields",
            field_names == ("k", "axicon"),
            f"advanced_row_shape_fields={field_names}",
        ),
        CompactShapeFieldCheck(
            "KrakenOS build still receives conic and axicon values",
            abs(float(kraken_shape.k) - shape_row.k) < 1e-12
            and abs(float(kraken_shape.Axicon) - shape_row.axicon) < 1e-12,
            f"k={kraken_shape.k}, Axicon={kraken_shape.Axicon}",
        ),
        CompactShapeFieldCheck(
            "hidden conic field remains optimizer-addressable",
            abs(initial_k - shape_row.k) < 1e-12 and abs(optimized_row.k + 0.75) < 1e-12,
            f"initial={initial_k}, applied={optimized_row.k}",
        ),
    ]


def _print_table(checks: list[CompactShapeFieldCheck]) -> None:
    print("KrakenOS compact shape-field validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate compact table handling for k/Axicon row-shape fields.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_compact_shape_fields()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
