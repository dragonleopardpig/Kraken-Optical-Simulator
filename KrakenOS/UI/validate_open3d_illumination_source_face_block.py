"""Display-free guard for bugs/0357 -- a free illumination source covering a promoted
face blocks the imaging trace there (kills the BS reflect arm + its branch axis).

PURE: the coverage detector on a stub editor -- a panel seated on a face collects its
face_id; non-parallel, off-plane, off-board panels and face-bound markers collect
nothing. WIRING: the marker path still feeds the same map; the per-bundle suppression
scopes the 0273 flag to illumination-source bundles in the non-seq trace loop; the
KrakenSys matcher still absorbs on the blocked ids.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_illumination_source_face_block
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor


class _Fake:
    _coverage_illumination_block_face_ids = KrakenLayoutEditor._coverage_illumination_block_face_ids
    _illumination_block_face_ids_by_row = KrakenLayoutEditor._illumination_block_face_ids_by_row

    @staticmethod
    def _is_open3d_promoted_optical_solid_row(row):
        return bool(getattr(row, "promoted", False))

    def __init__(self, sources, faces_by_row, rows):
        self._sources = list(sources)
        self._faces_by_row = dict(faces_by_row)
        self.rows = list(rows)
        self.layout_scene_source_specs = []

    def _drawable_scene_source_descriptors(self):
        return self._sources

    def _scene_source_face_anchor_records(self, row_index):
        return self._faces_by_row.get(int(row_index), [])


def _source(origin, direction, rx, ry, *, marker=False):
    settings = {"radius_x": rx, "radius_y": ry}
    if marker:
        settings["face_anchor_row"] = 1
        settings["face_anchor_face_id"] = "F001"
    return SimpleNamespace(origin=tuple(origin), direction=tuple(direction), settings=settings)


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # MV-150-like: the BS cube (row 1) side face at x=+27.5 facing +X; the LED panel
    # seated ON it at x=+27.6 emitting -X into the cube.
    faces = [
        {"face_id": "F003", "centroid_world": (27.5, 0.0, 229.6), "normal_world": (1.0, 0.0, 0.0)},
        {"face_id": "F004", "centroid_world": (0.0, 0.0, 257.1), "normal_world": (0.0, 0.0, 1.0)},
        {"face_id": "F005", "centroid_world": (-27.5, 0.0, 229.6), "normal_world": (-1.0, 0.0, 0.0)},
    ]
    rows = [SimpleNamespace(promoted=False), SimpleNamespace(promoted=True)]
    led = _source((27.6, 0.0, 229.6), (-1.0, 0.0, 0.0), 27.5, 37.0)

    fake = _Fake([led], {1: faces}, rows)
    out = fake._coverage_illumination_block_face_ids()
    if out.get(1) != {"F003"}:
        failures.append(f"panel seated on the +X face must collect exactly F003, got {out!r}")
    merged = fake._illumination_block_face_ids_by_row()
    if merged.get(1) != {"F003"}:
        failures.append("the coverage ids must merge into the 0273 block map")

    # Negative controls: far panel / non-parallel face / marker source collect nothing.
    far = _Fake([_source((80.0, 0.0, 229.6), (-1.0, 0.0, 0.0), 27.5, 37.0)], {1: faces}, rows)
    if far._coverage_illumination_block_face_ids():
        failures.append("a panel 50 mm off the face plane must NOT block it")
    marker = _Fake([_source((27.6, 0.0, 229.6), (-1.0, 0.0, 0.0), 27.5, 37.0, marker=True)], {1: faces}, rows)
    if marker._coverage_illumination_block_face_ids():
        failures.append("a face-bound MARKER source is the 0273 path, not coverage")
    off_board = _Fake([_source((27.6, 0.0, 100.0), (-1.0, 0.0, 0.0), 27.5, 37.0)], {1: faces}, rows)
    if off_board._coverage_illumination_block_face_ids():
        failures.append("a panel far outside the face board must NOT block it")

    # WIRING: the per-bundle suppression in the non-seq trace loop + the matcher.
    from KrakenOS.UI.services.trace_preview import TracePreviewService

    trace_src = inspect.getsource(TracePreviewService._trace_preview_bundles)
    for needle in ("_suppress_illumination_face_absorption", '"illumination"', "prior_suppress"):
        if needle not in trace_src:
            failures.append(f"the bundle trace loop lost its {needle} scoping")
    block_src = inspect.getsource(KrakenLayoutEditor._illumination_block_face_ids_by_row)
    if "_coverage_illumination_block_face_ids" not in block_src:
        failures.append("the block map no longer merges coverage-derived faces")
    import KrakenOS.KrakenSys as kraken_sys

    sys_src = inspect.getsource(kraken_sys)
    if "OpticalSolidFaceIlluminationBlock" not in sys_src or "force_absorption" not in sys_src:
        failures.append("the KrakenSys illumination-block matcher went missing")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Illumination-source face-block validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Illumination-source face-block validation passed: a free LED panel seated on "
        "a promoted face collects that face into the 0273 absorb map (killing the BS "
        "reflect arm + its branch axis), negatives stay clear, and the illumination "
        "bundles themselves trace with the suppression flag scoped per-bundle."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
