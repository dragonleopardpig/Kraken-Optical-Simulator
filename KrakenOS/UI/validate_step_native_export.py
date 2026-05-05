from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np


def _topology_counts(path: Path) -> dict[str, int]:
    try:
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID
        from OCC.Core.TopExp import TopExp_Explorer

        reader = STEPControl_Reader()
        status = reader.ReadFile(str(path))
        transferred = reader.TransferRoots() if status == 1 else 0
        shape = reader.OneShape() if transferred else None
        counts = {"status": int(status), "transferred": int(transferred), "solids": 0, "faces": 0, "edges": 0}
        if shape is not None and not shape.IsNull():
            for kind, key in ((TopAbs_SOLID, "solids"), (TopAbs_FACE, "faces"), (TopAbs_EDGE, "edges")):
                explorer = TopExp_Explorer(shape, kind)
                while explorer.More():
                    counts[key] += 1
                    explorer.Next()
        return counts
    except Exception as exc:
        return {"status": -1, "transferred": 0, "solids": 0, "faces": 0, "edges": 0, "error": str(exc)}


def main() -> int:
    try:
        from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    except Exception as exc:
        print(f"pythonocc unavailable: {exc}")
        return 1

    from KrakenOS.UI.layout_editor import _ray_bundle_envelope_polylines, _write_step_with_cad_shapes_and_rays

    output_path = Path("/tmp/kraken_step_native_export_validate.step")
    box = BRepPrimAPI_MakeBox(10.0, 6.0, 4.0).Shape()
    ray = np.asarray(
        [
            [-5.0, 0.0, 0.0],
            [0.0, 1.0, 12.0],
            [5.0, 0.0, 24.0],
        ],
        dtype=float,
    )
    analytic_count, cad_count, ray_count = _write_step_with_cad_shapes_and_rays(
        SimpleNamespace(SDT=[], TRANS_2A=[]),
        [],
        [("validation_box", box)],
        [ray],
        output_path,
    )
    text = output_path.read_text(encoding="utf-8", errors="ignore")
    topology = _topology_counts(output_path)
    fan = [
        np.asarray([[0.0, 0.0, 0.0], [0.0, float(y), 10.0]], dtype=float)
        for y in np.linspace(-5.0, 5.0, 11)
    ]
    fan_envelope = _ray_bundle_envelope_polylines(fan, 11)
    through = [
        np.asarray([[0.0, 0.0, 0.0], [0.0, float(y), 5.0], [0.0, 0.0, 10.0]], dtype=float)
        for y in np.linspace(-4.0, 4.0, 9)
    ]
    clipped = [
        np.asarray([[0.0, 0.0, 0.0], [0.0, -10.0, 5.0]], dtype=float),
        np.asarray([[0.0, 0.0, 0.0], [0.0, 10.0, 5.0]], dtype=float),
    ]
    through_envelope = _ray_bundle_envelope_polylines(through + clipped, 11)

    checks = [
        ("native CAD shape count", cad_count == 1, str(cad_count)),
        ("ray tube polyline count", ray_count == 1, str(ray_count)),
        ("analytic count", analytic_count == 0, str(analytic_count)),
        ("no AP242 tessellation-only entity", "TRIANGULATED_FACE_SET" not in text, ""),
        ("STEPControl reader transfers shape", topology.get("status") == 1 and topology.get("transferred", 0) >= 1, str(topology)),
        ("reader sees native CAD faces", topology.get("faces", 0) >= 6, str(topology)),
        ("reader sees ray tube solids", topology.get("solids", 0) >= 3, str(topology)),
        ("reader sees ray tube faces", topology.get("faces", 0) > 6, str(topology)),
        ("ray fan reduced to two marginal rays", len(fan_envelope) == 2, str(len(fan_envelope))),
        (
            "ray envelope prefers through-going rays",
            len(through_envelope) == 2 and all(float(ray[-1, 2]) == 10.0 for ray in through_envelope),
            str([ray.tolist() for ray in through_envelope]),
        ),
        ("compact validation file", output_path.stat().st_size < 200_000, str(output_path.stat().st_size)),
    ]

    print("KrakenOS native STEP export validation")
    print("check | status | detail")
    print("--- | --- | ---")
    failed = False
    for name, passed, detail in checks:
        print(f"{name} | {'PASS' if passed else 'FAIL'} | {detail}")
        failed = failed or not passed
    print(f"output | PASS | {output_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
