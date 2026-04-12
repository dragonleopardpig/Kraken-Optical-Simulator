#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.TopAbs import TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Compound, topods


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a reduced outer-shell STL from selected STEP solids.")
    parser.add_argument("step_path", type=Path)
    parser.add_argument("stl_out", type=Path)
    parser.add_argument("--solids", required=True, help="Comma-separated solid indices, e.g. 0,1,2")
    parser.add_argument("--linear-deflection", type=float, default=0.5)
    args = parser.parse_args()

    indices = [int(part.strip()) for part in args.solids.split(",") if part.strip()]
    if not indices:
        raise RuntimeError("No solid indices supplied")

    solids = load_solids(args.step_path.expanduser().resolve())
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for index in indices:
        if index < 0 or index >= len(solids):
            raise RuntimeError(f"Solid index out of range: {index} (0..{len(solids)-1})")
        builder.Add(compound, solids[index])

    mesh = BRepMesh_IncrementalMesh(compound, float(args.linear_deflection))
    mesh.Perform()
    args.stl_out.parent.mkdir(parents=True, exist_ok=True)
    writer = StlAPI_Writer()
    writer.SetASCIIMode(False)
    ok = writer.Write(compound, str(args.stl_out))
    if not ok or not args.stl_out.exists():
        raise RuntimeError("Failed to write STL output")
    print(args.stl_out)


if __name__ == "__main__":
    main()
