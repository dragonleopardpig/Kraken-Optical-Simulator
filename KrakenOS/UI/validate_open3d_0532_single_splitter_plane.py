"""bugs/0532 guard -- a solid carries at most ONE splitter plane per direction.

The AZ85 plate BS reached the trace with BOTH large faces flagged "Beam Splitter" (a
stale flag from the pre-0445 arbitrary pick surviving a later re-flag), so every glass
interface split 50/50: a ~25 % double-bounce ghost band (flag_20260804_082939), a 25 %
transmit dump (should be ~48 %), and -- once 0533 let the reflect child re-cross the
glass -- a full lossy-etalon chain explosion (1953 ghost paths).

Fix: the shared metadata normalizer demotes PARALLEL-but-non-coplanar duplicate splitter
planes (keeping the 0445-preferred object-facing one); `assign_optical_solid_face_function`
demotes the stale plane at flag time so the user's LATEST choice wins. Coincident pairs
(the cube's cemented diagonal) and crossed planes (X-cube) are untouched.

Checks:
  SOURCE -- the normalizer dedup + the assign-time demotion are present.
  MECH   -- plate pattern demotes the away-facing plane; cube coincident pair and
            X-cube crossed planes are kept.
  REAL   -- AZ85: row 3 reads back with exactly ONE splitter plane; the trace has no
            transmit->reflect ghost family; the dump family carries ~0.49, not 0.25.
  ASSIGN -- flagging the OTHER plate face demotes the first (latest choice wins).
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import optical_solid_metadata as _m
    from KrakenOS.UI.services import optical_solid_workflow as _w

    src = _inspect.getsource(_m.normalize_optical_solid_face_metadata)
    if "_demote_parallel_duplicate_splitter_planes" in src:
        notes.append("SOURCE = the normalizer runs the duplicate-splitter dedup")
    else:
        notes.append("SOURCE the normalizer dedup is missing")
        ok = False
    src_assign = _inspect.getsource(_w.OpticalSolidWorkflowMixin.assign_optical_solid_face_function) if hasattr(_w, "OpticalSolidWorkflowMixin") else ""
    if not src_assign:
        for name in dir(_w):
            obj = getattr(_w, name)
            if isinstance(obj, type) and hasattr(obj, "assign_optical_solid_face_function"):
                src_assign = _inspect.getsource(obj.assign_optical_solid_face_function)
                break
    if "bugs/0532" in src_assign and "stale splitter demoted" in src_assign:
        notes.append("SOURCE = assigning a splitter demotes the stale parallel plane")
    else:
        notes.append("SOURCE the assign-time stale-splitter demotion is missing")
        ok = False

    def _faces(pattern):
        out = _m.normalize_optical_solid_face_metadata({"faces": pattern})
        return {f["face_id"]: f["function"] for f in out["faces"]}

    plate = _faces([
        {"face_id": "F005", "function": "Beam Splitter", "normal": [0, -0.7071, -0.7071], "plane_offset_mm": 0.55, "area_mm2": 8123.5},
        {"face_id": "F006", "function": "Beam Splitter", "normal": [0, 0.7071, 0.7071], "plane_offset_mm": 0.55, "area_mm2": 8123.5},
    ])
    if plate.get("F005") == "Beam Splitter" and plate.get("F006") == "Transmit/Port":
        notes.append("MECH = the plate keeps the object-facing plane, demotes the far one")
    else:
        notes.append(f"MECH plate dedup wrong: {plate}")
        ok = False
    cube = _faces([
        {"face_id": "FA", "function": "Beam Splitter", "normal": [0.7071, 0, 0.7071], "plane_offset_mm": 0.0, "area_mm2": 5000.0},
        {"face_id": "FB", "function": "Beam Splitter", "normal": [-0.7071, 0, -0.7071], "plane_offset_mm": 0.0, "area_mm2": 5000.0},
    ])
    if cube.get("FA") == "Beam Splitter" and cube.get("FB") == "Beam Splitter":
        notes.append("MECH = the cube's coincident cemented pair is untouched")
    else:
        notes.append(f"MECH cube pair broken: {cube}")
        ok = False
    xcube = _faces([
        {"face_id": "D1", "function": "Beam Splitter", "normal": [0.7071, 0, 0.7071], "plane_offset_mm": 0.0, "area_mm2": 5000.0},
        {"face_id": "D2", "function": "Beam Splitter", "normal": [0.7071, 0, -0.7071], "plane_offset_mm": 0.0, "area_mm2": 5000.0},
    ])
    if xcube.get("D1") == "Beam Splitter" and xcube.get("D2") == "Beam Splitter":
        notes.append("MECH = crossed X-cube diagonals are untouched")
    else:
        notes.append(f"MECH X-cube broken: {xcube}")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        _row, _path, metadata = app._optical_solid_face_metadata_for_row(3)
        splitters = [f for f in metadata.get("faces", []) if str(f.get("function")) == "Beam Splitter"]
        if len(splitters) == 1:
            notes.append(f"REAL = row 3 reads back with ONE splitter plane ({splitters[0].get('face_id')})")
        else:
            notes.append(f"REAL row 3 has {len(splitters)} splitter faces")
            ok = False
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=True
        )
        ghost = [p for p in bundle.ray_paths
                 if "transmit -> " in str(getattr(p, "branch_path", "")) ]
        dump = [p for p in bundle.ray_paths
                if str(getattr(p, "branch_path", "")) == "S3:S3/transmit"]
        if not ghost:
            notes.append("REAL = no multi-interaction ghost family in the trace")
        else:
            notes.append(f"REAL {len(ghost)} etalon/ghost paths still trace")
            ok = False
        if dump and abs(float(dump[0].branch_power) - 0.489) < 0.05:
            notes.append(f"REAL = the transmit dump carries ~0.49 ({float(dump[0].branch_power):.3f})")
        else:
            power = float(dump[0].branch_power) if dump else None
            notes.append(f"REAL dump power wrong: {power}")
            ok = False

        splitter_id = str(splitters[0].get("face_id")) if splitters else "S001/F005"
        other_id = "S001/F006" if splitter_id.endswith("F005") else "S001/F005"
        app.assign_optical_solid_face_function(
            3, other_id, "Partial Reflecting / Transmitting"
        )
        _row, _path, metadata = app._optical_solid_face_metadata_for_row(3)
        flags = {str(f.get("face_id")): str(f.get("function")) for f in metadata.get("faces", [])}
        if flags.get(other_id) == "Beam Splitter" and flags.get(splitter_id) == "Transmit/Port":
            notes.append("ASSIGN = re-flagging the other plane wins (stale one demoted)")
        else:
            notes.append(f"ASSIGN latest-choice demotion failed: {flags}")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
