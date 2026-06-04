#!/usr/bin/env python3
"""Display-free regression for bugs/0013 (lens rim "sub-edges"): the OCC
importer splits a lens edge into several co-axial, co-radial cylinder B-Rep
faces, and the face-roles editor used to leave native B-Rep faces ungrouped
(``_face_group_ids = [-1] * len(records)``). So a single physical lens edge
listed as several "sub-edges" and ``render_face_preview`` drew each one's edges
-> the stray rim wireframe the user reported.

``group_brep_optical_solid_faces`` now buckets the rim's cylinder faces by
``(rounded radius, canonical axis-line)`` so the whole rim -- including across a
cemented doublet's two solids -- lands in one group, while every cap stays
ungrouped. This loads the achromat STEP analytically (no display, no pyvista),
builds the B-Rep face records, and asserts exactly that.

Teeth: reverting the dialog to ``[-1] * len(records)`` (or a grouping that
keys on the solid index) splits the rim back into >1 group -> FAIL.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_brep_lens_rim_grouping

Exit: 0 = pass, 1 = regression, 2 = fixture / OCC backend unavailable.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STEP_FIXTURE = _REPO_ROOT / "attachment/Lens/Aspherized_Achromatic_Lenses/step_49665.step"


def rim_grouping_failures() -> tuple[list[str], dict]:
    from KrakenOS.UI import optical_solid_metadata as osm
    from KrakenOS.UI.services.optical_solid_geometry import group_brep_optical_solid_faces
    from KrakenOS.UI.services.step_analytic_geometry import load_step_analytic_document

    doc = load_step_analytic_document(_STEP_FIXTURE)
    metadata = doc.optical_solid_face_metadata()
    records = [osm.normalize_optical_solid_face_record(f) for f in metadata.get("faces", []) or []]

    gids = group_brep_optical_solid_faces(records)
    cyl = [i for i, r in enumerate(records) if str(r.get("surface_type")) == "cylinder"]
    caps = [i for i, r in enumerate(records) if str(r.get("surface_type")) != "cylinder"]
    rim_groups = {gids[i] for i in cyl}
    cap_groups = {gids[i] for i in caps}

    detail = {
        "face_count": len(records),
        "cylinder_faces": [records[i].get("face_id") for i in cyl],
        "cap_faces": [records[i].get("face_id") for i in caps],
        "group_ids": list(gids),
        "rim_group_ids": sorted(rim_groups),
        "group_member_counts": dict(Counter(g for g in gids if g >= 0)),
    }

    failures: list[str] = []
    if len(cyl) < 2:
        failures.append(f"fixture has <2 cylinder rim faces ({len(cyl)}); cannot exercise rim grouping")
        return failures, detail
    if rim_groups != {0}:
        failures.append(
            f"rim's {len(cyl)} cylinder faces did not consolidate into one group "
            f"(got group ids {sorted(rim_groups)}) -- bugs/0013 sub-edges"
        )
    if any(g >= 0 for g in cap_groups):
        bad = [records[i].get("face_id") for i in caps if gids[i] >= 0]
        failures.append(f"cap face(s) were grouped as a rim: {bad}")
    # the rim group must actually contain every cylinder face (no straggler)
    if rim_groups == {0} and dict(Counter(g for g in gids if g >= 0)).get(0, 0) != len(cyl):
        failures.append(
            f"rim group 0 has {Counter(g for g in gids if g >= 0).get(0)} members, expected {len(cyl)}"
        )
    return failures, detail


def main() -> int:
    if not _STEP_FIXTURE.exists():
        print(f"SKIP: STEP fixture not found: {_STEP_FIXTURE}", file=sys.stderr)
        return 2
    try:
        failures, detail = rim_grouping_failures()
    except RuntimeError as exc:
        if "pythonocc" in str(exc).lower() or "OCC" in str(exc):
            print(f"SKIP: OCC backend unavailable ({exc})", file=sys.stderr)
            return 2
        raise
    except ImportError as exc:
        print(f"SKIP: OCC backend unavailable ({exc})", file=sys.stderr)
        return 2

    print(f"  {detail}")
    if failures:
        print("\n[FAIL] bugs/0013 B-Rep lens rim grouping")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        f"\n[PASS] {len(detail['cylinder_faces'])} rim cylinder faces -> one group; "
        f"{len(detail['cap_faces'])} cap(s) ungrouped"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
