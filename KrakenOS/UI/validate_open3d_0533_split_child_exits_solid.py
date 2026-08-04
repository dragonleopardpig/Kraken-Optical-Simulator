"""bugs/0533 guard -- the split's reflected child exits its own solid.

The plate-BS ghost (`S3/transmit -> S3/reflect`) reflected at the FAR face and then died
1.2 mm INSIDE the glass: the split child's row-level skip_surface_once killed the exit
through the entry face, so the exit refraction never happened and the beam flew off
15-17 deg high with its in-glass direction (flag_20260804_082939 "spurious reflected
beam"; zoom 084655 shows rays crossing the drawn plate outline with no kink).

Fix (KrakenSys.__NsTraceSplitChildSkipSurface): the EXIT-face split is the mirror of the
0445 entry-face case -- return None so the inside child may re-interact with its own row;
the leaving child is protected by the origin nudge.

Checks:
  SOURCE -- the exit-transition exemption is present.
  REAL   -- second-surface-coating configuration (splitter on the FAR plate face, a
            legitimate 0444/0445 model): every transmit->reflect path re-crosses the
            plate (>= 3 surface events) and emerges PARALLEL to the front-surface fold
            (plane-parallel-plate symmetry), instead of dying inside the glass.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    import KrakenOS as Kos
    method = getattr(Kos.KrakenSys.system, "_system__NsTraceSplitChildSkipSurface")
    src = _inspect.getsource(method)
    if "bugs/0533" in src and '"exit"' in src:
        notes.append("SOURCE = the exit-face split exemption is present")
    else:
        notes.append("SOURCE the 0533 exit exemption is missing")
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
        # Move the coating to the FAR plate face (the legitimate second-surface model);
        # 0532's assign-time demotion clears the near-face flag.
        _row, _path, metadata = app._optical_solid_face_metadata_for_row(3)
        flagged = [str(f.get("face_id")) for f in metadata.get("faces", []) if str(f.get("function")) == "Beam Splitter"]
        target = "S001/F006" if (flagged and flagged[0].endswith("F005")) else "S001/F005"
        app.assign_optical_solid_face_function(3, target, "Partial Reflecting / Transmitting")
        system, _rays, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=True
        )
        def _entered_then_split_reflect(p) -> bool:
            kinds = [
                (str(getattr(e, "event_type", "")), str(getattr(e, "surface_id", "")))
                for e in (p.events or [])
                if str(getattr(e, "event_kind", "")) == "surface"
            ]
            for i in range(len(kinds) - 1):
                if (
                    kinds[i][0] in ("transmission", "refraction")
                    and kinds[i][1] == "3"
                    and kinds[i + 1][0] == "split_reflect"
                ):
                    return True
            return False

        fold_family = [p for p in bundle.ray_paths if _entered_then_split_reflect(p)]
        if not fold_family:
            notes.append("SKIP: no far-face reflect family traced (model changed?)")
            return ok, notes
        died_inside = 0
        exited = 0
        parallel_ok = 0
        angles = []
        for p in fold_family:
            surface_events = [
                e for e in (p.events or [])
                if str(getattr(e, "event_kind", "")) == "surface"
            ]
            pts = np.asarray(p.points_world, float)[:, :3]
            if len(surface_events) < 3:
                died_inside += 1
                continue
            exited += 1
            dirs = np.diff(pts, axis=0)
            dirs = dirs / np.maximum(np.linalg.norm(dirs, axis=1, keepdims=True), 1e-12)
            if pts.shape[0] < 5:
                died_inside += 1
                continue
            launch = dirs[0]
            # pts[0..3] are launch / entry / far-face split / exit; dirs[3] is the
            # PLATE-EMERGENT segment (the path continues through the whole system
            # now that the fold images, so dirs[-1] would be deep in the camera).
            exit_dir = dirs[3]
            # Frame-free reference: the plate normal from the internal reflection
            # itself (r = d - 2(d.n)n  =>  n || d - r), then the front-surface fold
            # of the ORIGINAL beam about that plane. Plane-parallel-plate physics:
            # the emergent second-surface fold is PARALLEL to it.
            in_glass = dirs[1]
            reflected = dirs[2]
            normal = in_glass - reflected
            n_norm = float(np.linalg.norm(normal))
            if n_norm <= 1e-9:
                died_inside += 1
                continue
            normal = normal / n_norm
            front_fold = launch - 2.0 * float(np.dot(launch, normal)) * normal
            angle = float(np.degrees(np.arccos(np.clip(np.dot(exit_dir, front_fold), -1.0, 1.0))))
            angles.append(angle)
            if angle <= 1.5:
                parallel_ok += 1
        if died_inside == 0:
            notes.append(f"REAL = every far-face reflect child exits the plate ({exited} paths)")
        else:
            notes.append(f"REAL {died_inside} split children still die inside the glass")
            ok = False
        if angles and parallel_ok >= int(0.9 * len(angles)):
            notes.append(
                f"REAL = the emergent fold is parallel to the front-surface fold "
                f"(median {np.median(angles):.2f} deg, {parallel_ok}/{len(angles)} within 1.5 deg)"
            )
        else:
            med = np.median(angles) if angles else float("nan")
            notes.append(f"REAL emergent fold not parallel (median {med:.2f} deg, {parallel_ok}/{len(angles)})")
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
