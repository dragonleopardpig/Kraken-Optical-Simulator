#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Load a CAD file in FreeCAD and expose a compound edge object.")
    parser.add_argument("cad_path", nargs="?", type=Path, help="Input STEP/BREP file")
    parser.add_argument("--doc-name", default=os.environ.get("KRAKEN_FC_DOC_NAME", "KrakenCAD"), help="FreeCAD document name")
    parser.add_argument("--object-name", default=os.environ.get("KRAKEN_FC_OBJECT_NAME", "compound_edges"), help="Output object label")
    parser.add_argument("--save-fcstd", type=Path, default=Path(os.environ["KRAKEN_FC_SAVE_AS"]) if os.environ.get("KRAKEN_FC_SAVE_AS") else None, help="Optional .FCStd output path")
    args = parser.parse_args()

    cad_arg = args.cad_path or (Path(os.environ["KRAKEN_FC_CAD_PATH"]) if os.environ.get("KRAKEN_FC_CAD_PATH") else None)
    if cad_arg is None:
        raise SystemExit("No CAD path provided. Use positional argument or KRAKEN_FC_CAD_PATH.")

    cad_path = cad_arg.expanduser().resolve()
    if not cad_path.exists():
        raise SystemExit(f"CAD file not found: {cad_path}")

    import FreeCAD as App  # type: ignore
    import Import  # type: ignore
    import Part  # type: ignore

    doc = App.newDocument(args.doc_name)
    Import.insert(str(cad_path), doc.Name)
    doc.recompute()

    imported = [obj for obj in doc.Objects if getattr(obj, "Shape", None)]
    if not imported:
        raise SystemExit("No shape objects were imported into FreeCAD")

    if len(imported) == 1:
        shape = imported[0].Shape
    else:
        shape = Part.makeCompound([obj.Shape for obj in imported])

    edge_compound = Part.makeCompound(shape.Edges)
    Part.show(edge_compound, args.object_name)
    doc.recompute()

    if args.save_fcstd is not None:
        save_path = args.save_fcstd.expanduser().resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveAs(str(save_path))
        print(save_path)
    else:
        print(f"{doc.Name}:{args.object_name}")


if __name__ == "__main__":
    main()
