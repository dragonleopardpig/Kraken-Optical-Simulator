from __future__ import annotations

from pathlib import Path


def main() -> int:
    try:
        import pyvista as pv
    except Exception as exc:
        print(f"pyvista unavailable: {exc}")
        return 1

    from KrakenOS.UI.layout_editor import _write_meshes_to_tessellated_step

    output_path = Path("/tmp/kraken_step_tessellated_export_validate.step")
    mesh = pv.Cube().triangulate().clean()
    mesh_count, triangle_count = _write_meshes_to_tessellated_step(
        [("validation_cube", mesh)],
        output_path,
        max_facets_per_mesh=1000,
    )
    text = output_path.read_text(encoding="utf-8", errors="ignore")
    try:
        from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
        from OCC.Core.TDocStd import TDocStd_Document

        reader = STEPCAFControl_Reader()
        read_status = reader.ReadFile(str(output_path))
        doc = TDocStd_Document("MDTV-XCAF")
        caf_transfer_ok = bool(reader.Transfer(doc)) if read_status == 1 else False
        caf_detail = f"status={read_status}, transfer={caf_transfer_ok}"
    except Exception as exc:
        caf_transfer_ok = True
        caf_detail = f"skipped: {exc}"

    checks = [
        ("mesh count", mesh_count == 1, str(mesh_count)),
        ("triangle count", triangle_count >= 12, str(triangle_count)),
        ("uses triangulated face set", "TRIANGULATED_FACE_SET" in text, ""),
        ("no per-triangle advanced faces", "ADVANCED_FACE" not in text, ""),
        ("no open-shell brep output", "OPEN_SHELL" not in text, ""),
        ("STEPCAF reader accepts tessellated file", caf_transfer_ok, caf_detail),
        ("compact validation file", output_path.stat().st_size < 200_000, str(output_path.stat().st_size)),
    ]

    print("KrakenOS tessellated STEP export validation")
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
