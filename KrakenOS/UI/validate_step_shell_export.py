from __future__ import annotations

from pathlib import Path


def _topology_counts(path: Path) -> dict[str, int]:
    try:
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.TopAbs import TopAbs_FACE
        from OCC.Core.TopExp import TopExp_Explorer

        reader = STEPControl_Reader()
        status = reader.ReadFile(str(path))
        transferred = reader.TransferRoots() if status == 1 else 0
        shape = reader.OneShape() if transferred else None
        face_count = 0
        if shape is not None and not shape.IsNull():
            explorer = TopExp_Explorer(shape, TopAbs_FACE)
            while explorer.More():
                face_count += 1
                explorer.Next()
        return {"status": int(status), "transferred": int(transferred), "faces": int(face_count)}
    except Exception as exc:
        return {"status": -1, "transferred": 0, "faces": 0, "error": str(exc)}


def main() -> int:
    try:
        import pyvista as pv
    except Exception as exc:
        print(f"pyvista unavailable: {exc}")
        return 1

    from KrakenOS.UI.layout_editor import _write_meshes_to_faceted_step

    output_path = Path("/tmp/kraken_step_shell_export_validate.step")
    mesh = pv.Cube().triangulate().clean()
    mesh_count, triangle_count = _write_meshes_to_faceted_step(
        [("validation_cube", mesh)],
        output_path,
        max_facets_per_mesh=1000,
    )
    text = output_path.read_text(encoding="utf-8", errors="ignore")
    topology = _topology_counts(output_path)

    checks = [
        ("mesh count", mesh_count == 1, str(mesh_count)),
        ("facet count", triangle_count >= 12, str(triangle_count)),
        ("uses shell-based surface model", "SHELL_BASED_SURFACE_MODEL" in text, ""),
        ("uses one open shell for cube mesh", text.count("OPEN_SHELL") == 1, str(text.count("OPEN_SHELL"))),
        ("no AP242 tessellation-only entity", "TRIANGULATED_FACE_SET" not in text, ""),
        ("STEPControl reader transfers shape", topology.get("status") == 1 and topology.get("transferred", 0) >= 1, str(topology)),
        ("reader sees faces", topology.get("faces", 0) >= 12, str(topology)),
        ("compact validation file", output_path.stat().st_size < 200_000, str(output_path.stat().st_size)),
    ]

    print("KrakenOS shell STEP export validation")
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
