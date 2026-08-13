#!/usr/bin/env python3
"""Display-free guard: a promoted-solid face's coating uses the shared library AND applies in
the non-sequential trace (the Face-Editor coating merged with the 2D "Coating..." library).

A promoted CAD solid's Face Editor lets each face pick a coating; this guard pins that the pick
comes from the SAME ``COATING_PRESETS`` library the 2D surface-coating editor uses, and that the
chosen coating actually reaches ``CoatingFun`` during the trace (the per-face reflectance changes
to the coating's value), while a clear/uncoated face leaves the trace unchanged (additive).

Checks (display-free; the trace is numpy, no display needed):
  A. RESOLVER: ``resolve_optical_solid_face_coating`` maps a shared preset name -> (table, met);
     clear / empty / free-text -> None (no per-face coating -> trace unchanged).
  B. BUILD MAP: a promoted-solid scene (penta.py) with a face coated "Protected mirror 94%"
     builds ``surface.OpticalSolidFaceCoatingTables = {face_id: (table, met)}`` carrying that
     table.
  C. PHYSICS (differential): tracing the same ray with the solid's faces coated vs cleared, the
     per-hit energy (system.RP) MUST change with the coating present -- proving the per-face
     table reached CoatingFun -- and the coated reflectance lands near the table's ~0.94..0.96
     (vs ~0.04 bare). This is the merge's whole point.
  D. ADDITIVE: the uncoated trace is the baseline; the coating changes the energy ONLY when set.
  E. CUSTOM TABLE: a face's own ``coating_table`` (the advanced "Edit table..." editor) round-trips
     the face-record schema and WINS over the preset name; an empty table is not persisted.
  F. UI WIRING (source check): the face dialog exposes the per-face table editor and persists
     ``coating_table``/``coating_met`` into the face record.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_optical_solid_face_coating

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
_SCENE = _REPO / "attachment" / "penta.py"
_COATING = "Protected mirror 94%"


def _trace_penta_rp(coat: bool):
    """Build penta.py (optionally coating every promoted-solid face with the mirror preset),
    trace one on-axis ray, return the per-hit reflectance array system.RP (or None on failure).

    bugs/0618: rows come from a REAL editor load, not the raw file parse -- the load heals
    dangling ``Solid_3d_stl`` caches from their source STEPs (the bugs/0021 pass, now also
    on the by-name loader). The raw parse kept the dangling legacy paths, the system build
    silently substituted the analytic fallback, and this guard measured a machine with NO
    promoted solids at all (its C check then hinged on whether the fallback produced hits)."""
    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import (
        KrakenLayoutEditor,
        _build_system_from_specs,
        surface_rows_to_specs,
    )

    cap = io.StringIO()
    with redirect_stdout(cap), redirect_stderr(cap):
        app = KrakenLayoutEditor()
        try:
            app.layout_files["_172"] = _SCENE
            app.load_layout_by_name("_172", refresh=False)
            rows = [row for row in app.rows]
        finally:
            try:
                app.destroy()
            except Exception:
                pass
    if coat:
        for row in rows:
            osf = (getattr(row, "advanced", {}) or {}).get("OpticalSolidFaces")
            if osf:
                faces = osf["faces"] if isinstance(osf, dict) else osf
                for face in faces:
                    face["coating"] = _COATING
    cap = io.StringIO()
    with redirect_stdout(cap), redirect_stderr(cap):
        system = _build_system_from_specs(surface_rows_to_specs(rows))
        rays = Kos.raykeeper(system)
        zero = np.array([0.0])
        Kos.NsTraceLoop(zero, zero, zero, zero, zero, np.array([1.0]), 0.55, rays, clean=1)
    rp = np.asarray(list(getattr(system, "RP", []) or []), dtype=float)
    return rp


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []

    # A) resolver maps the shared library; clear/empty/free-text -> None.
    from KrakenOS.UI.layout_editor import COATING_PRESETS, resolve_optical_solid_face_coating
    if resolve_optical_solid_face_coating(_COATING) != (COATING_PRESETS[_COATING], 0):
        failures.append("A: resolver does not map the shared preset name to its (table, met=0)")
    if any(resolve_optical_solid_face_coating(x) is not None for x in ("", "Clear / no coating", "a free note")):
        failures.append("A: resolver returns a table for clear/empty/free-text (should be None -> additive)")

    if not _SCENE.exists():
        notes.append("SKIP build/physics: attachment/penta.py unavailable")
        return (not failures), (failures + notes)

    # B) build populates the per-face coating map from the shared library.
    try:
        from KrakenOS.UI.layout_editor import (
            KrakenLayoutEditor,
            _build_system_from_specs,
            _load_python_data,
            surface_rows_to_specs,
        )
        info = _load_python_data(_SCENE)
        rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
        coated_any = False
        for row in rows:
            osf = (getattr(row, "advanced", {}) or {}).get("OpticalSolidFaces")
            if osf:
                faces = osf["faces"] if isinstance(osf, dict) else osf
                if faces:
                    faces[0]["coating"] = _COATING
                    coated_any = True
        if not coated_any:
            notes.append("SKIP build/physics: penta.py has no promoted-solid faces")
            return (not failures), (failures + notes)
        cap = io.StringIO()
        with redirect_stdout(cap), redirect_stderr(cap):
            system = _build_system_from_specs(surface_rows_to_specs(rows))
        maps = [getattr(s, "OpticalSolidFaceCoatingTables", None) for s in system.SDT]
        tables = [t for m in maps if isinstance(m, dict) for (t, _met) in m.values()]
        if not any(t == COATING_PRESETS[_COATING] for t in tables):
            failures.append("B: surface.OpticalSolidFaceCoatingTables does not carry the resolved preset table")
    except Exception as exc:
        failures.append(f"B: build raised {exc!r}")
        return (not failures), (failures + notes)

    # C/D) differential physics: coated faces change the per-hit reflectance toward the coating,
    #      uncoated is the baseline.
    try:
        rp_bare = _trace_penta_rp(coat=False)
        rp_coat = _trace_penta_rp(coat=True)
    except Exception as exc:
        failures.append(f"C: trace raised {exc!r}")
        return (not failures), (failures + notes)
    if rp_bare is None or rp_coat is None or rp_bare.size == 0 or rp_bare.size != rp_coat.size:
        # bugs/0618: this used to SKIP (reading as PASS) -- which is how a scene whose
        # promoted solids silently degraded to the analytic fallback hid for weeks. A
        # coating guard with no energy data has verified nothing: fail loudly.
        failures.append(
            f"C: trace produced no comparable energy (bare={rp_bare.size if rp_bare is not None else 'None'}, "
            f"coat={rp_coat.size if rp_coat is not None else 'None'}) -- the penta solids did not build/trace"
        )
        return (not failures), (failures + notes)
    changed = not np.allclose(rp_bare, rp_coat, atol=1e-4)
    coated_near_table = bool(np.any(np.abs(rp_coat - 0.95) < 0.06))
    if not changed:
        failures.append(
            "C: per-face coating did NOT reach CoatingFun -- the coated trace energy is identical "
            f"to bare (RP={[round(float(v), 3) for v in rp_coat]}). The override carries coating_table "
            "but __CollectData reads _collect_interaction_override, which the subset builders drop it from."
        )
    if changed and not coated_near_table:
        failures.append(
            f"C: coating changed the energy but not toward the table's ~0.94..0.96 (RP={[round(float(v), 3) for v in rp_coat]})"
        )
    notes.append(
        f"physics: bare RP max {float(np.max(rp_bare)):.3f} -> coated max {float(np.max(rp_coat)):.3f} "
        f"(changed={changed}, near-table={coated_near_table})"
    )

    # E) CUSTOM per-face table (advanced "Edit table..." editor): it round-trips the face-record
    #    schema, WINS over the preset name in the resolver, and an empty table is not persisted
    #    (falls back to the name). The build map + engine then apply it via the same path as B/C.
    try:
        from KrakenOS.UI.layout_editor import resolve_optical_solid_face_coating_for_face
        from KrakenOS.UI.optical_solid_metadata import (
            normalize_optical_solid_face_coating_table,
            normalize_optical_solid_face_record,
        )
        custom = [[[0.5, 0.5, 0.5]], [[0.0, 0.0, 0.0]], [0.45, 0.55, 0.65], [0.0]]
        norm_custom = normalize_optical_solid_face_coating_table(custom)
        rec = normalize_optical_solid_face_record(
            {"face_id": "F1", "coating": _COATING, "coating_table": custom, "coating_met": 2}
        )
        if rec.get("coating_table") != norm_custom:
            failures.append("E: a custom coating_table does not round-trip the face-record schema")
        if resolve_optical_solid_face_coating_for_face(rec) != (norm_custom, 2):
            failures.append("E: a custom coating_table does not win over the preset name in the resolver")
        rec_clear = normalize_optical_solid_face_record(
            {"face_id": "F2", "coating": _COATING, "coating_table": [[], [], [], []]}
        )
        if "coating_table" in rec_clear:
            failures.append("E: an empty custom table is wrongly persisted on the face record")
        if resolve_optical_solid_face_coating_for_face(rec_clear) != (COATING_PRESETS[_COATING], 0):
            failures.append("E: with an empty custom table the resolver does not fall back to the preset name")
        notes.append("custom: a per-face coating_table round-trips + wins over the preset name")
    except Exception as exc:
        failures.append(f"E: custom-table check raised {exc!r}")

    # F) UI wiring (source-structure -- the harness has no display to drive the Tk dialog): the
    #    face dialog exposes the custom-table editor and persists coating_table/coating_met.
    try:
        import inspect

        from KrakenOS.UI.panels import main_optical_solid_face_roles_dialog as face_dialog
        dialog_src = inspect.getsource(face_dialog)
        if "_open_face_coating_table_editor" not in dialog_src or "Edit table" not in dialog_src:
            failures.append("F: the face dialog exposes no per-face coating-table editor / 'Edit table' button")
        if "'coating_table'" not in dialog_src or "'coating_met'" not in dialog_src:
            failures.append("F: the face dialog does not persist coating_table/coating_met into the face record")
    except Exception as exc:
        failures.append(f"F: UI-wiring check raised {exc!r}")

    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] promoted-solid per-face coating (shared library + applied in the non-seq trace)")
        return 1
    print("[PASS] promoted-solid face coating uses the shared library and applies in the non-seq trace")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
