#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Cylinder
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods

from cad_inspect_step import face_area, face_centroid, shape_bounds


def load_solids(step_path: Path):
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(step_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to read STEP: status={status}")
    if reader.TransferRoots() == 0:
        raise RuntimeError("STEP transfer produced no roots")
    shape = reader.OneShape()
    solids = []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        solids.append(topods.Solid(explorer.Current()))
        explorer.Next()
    return solids


def iter_faces(shape):
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        yield topods.Face(explorer.Current())
        explorer.Next()


def detect_reference(step_path: Path, solid_indices: list[int]) -> dict[str, object]:
    solids = load_solids(step_path)
    chosen = [solids[index] for index in solid_indices if 0 <= index < len(solids)]
    if not chosen:
        raise RuntimeError("No valid solids selected")

    weighted_x = 0.0
    weighted_y = 0.0
    weight_sum = 0.0
    cylinders = []
    for solid_index in solid_indices:
        if not (0 <= solid_index < len(solids)):
            continue
        for face_index, face in enumerate(iter_faces(solids[solid_index])):
            surf = BRepAdaptor_Surface(face, True)
            if surf.GetType() != GeomAbs_Cylinder:
                continue
            axis = surf.Cylinder().Axis().Direction()
            axis_vec = (float(axis.X()), float(axis.Y()), float(axis.Z()))
            if abs(axis_vec[2]) < 0.98:
                continue
            centroid = face_centroid(face)
            area = face_area(face)
            cylinders.append(
                {
                    "solid_index": solid_index,
                    "face_index": face_index,
                    "area": area,
                    "centroid": centroid,
                    "axis": axis_vec,
                }
            )
            weighted_x += area * centroid[0]
            weighted_y += area * centroid[1]
            weight_sum += area

    bounds = shape_bounds(chosen[0])
    for solid in chosen[1:]:
        sb = shape_bounds(solid)
        bounds = [
            min(bounds[0], sb[0]),
            max(bounds[1], sb[1]),
            min(bounds[2], sb[2]),
            max(bounds[3], sb[3]),
            min(bounds[4], sb[4]),
            max(bounds[5], sb[5]),
        ]

    if weight_sum > 0.0:
        ref_x = weighted_x / weight_sum
        ref_y = weighted_y / weight_sum
        method = "z_cylinder_area_weighted"
    else:
        ref_x = 0.5 * (bounds[0] + bounds[1])
        ref_y = 0.5 * (bounds[2] + bounds[3])
        method = "bounds_center"

    return {
        "reference_xy": [ref_x, ref_y],
        "bounds": bounds,
        "method": method,
        "cylinders_used": cylinders[:24],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect a mechanical reference center for STEP alignment.")
    parser.add_argument("step_path", type=Path)
    parser.add_argument("--solids", required=True)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    indices = [int(part.strip()) for part in args.solids.split(",") if part.strip()]
    result = detect_reference(args.step_path.expanduser().resolve(), indices)
    text = json.dumps(result, indent=2)
    if args.json_out is not None:
        args.json_out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
