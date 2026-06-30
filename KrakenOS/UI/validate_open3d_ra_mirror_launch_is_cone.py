"""Display-free guard for bugs/0186: a promoted RA-mirror fold launches a CONE, not a flat fan.

bugs/0161 made a plain point source revolve into a real 3D cone and kept the flat-fan
collapse only for the bug-0126 carve-out (a scene forced non-sequential by an IN-LINE
REFRACTIVE mesh solid, whose revolved mesh traces are too slow). A promoted right-angle
MIRROR cube (``machine_vision_AZ85_RA_Mirror.py``) folds +Z -> +X, but its row is
``surface = "Standard"`` with only ``desp_z`` (the cube sits 12.5 mm along the axis) and NO
tilt / transverse decentre -- so ``_scene_breaks_rotational_symmetry`` missed it, the folded
scene was misread as the rotationally-symmetric inline-solid carve-out, and the launch
collapsed back to a flat meridional fan (the recording reported ``prefers_meridional_fan:
true``). The fold breaks rotational symmetry about the original axis, so the launch must keep
the area-filling disk and revolve a cone.

The fix teaches ``_scene_breaks_rotational_symmetry`` to recognise a promoted mirror cube via
``_optical_solid_faces_have_mirror_fold`` (an ``OpticalSolidFaces`` face whose ``function`` is
"Mirror"). This guard binds the REAL ``TracePreviewSamplingMixin`` symmetry + launch gates onto
a light fake editor (no display) and asserts the RA-mirror scene revolves a cone while an
unfolded layout still keeps the cheap flat fan.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_launch_is_cone

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np

import KrakenOS.UI.nonseq_output_ports as nop
from KrakenOS.UI.layout_library import load_python_data
from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin
from KrakenOS.UI.trace_intent import _optical_solid_faces_have_mirror_fold

_EPS = 1e-9
_LAYOUTS = Path(__file__).resolve().parent.parent / "common_optical_layouts"

# The RA-mirror scene's resolved trace mode, as the recording reported it
# (flag_20260630_142846_722 sampling_diagnostics): a promoted mesh solid forces
# non-sequential, NOT folded, no branch (beam splitter / diffuse / probabilistic).
_RA_MIRROR_TRACE_STATE = {
    "use_nonseq": True,
    "use_folded": False,
    "has_beam_splitter": False,
    "has_probabilistic_nonseq": False,
    "has_diffuse_scatter": False,
    "has_optical_stl_solid": True,
}


class _LaunchEditor:
    """Fake editor binding the REAL symmetry + launch gates (exercises production code)."""

    _scene_breaks_rotational_symmetry = TracePreviewSamplingMixin._scene_breaks_rotational_symmetry
    _launch_pupil_prefers_meridional_fan = TracePreviewSamplingMixin._launch_pupil_prefers_meridional_fan
    _launch_cone_prefers_flat_fan = TracePreviewSamplingMixin._launch_cone_prefers_flat_fan
    _sample_ray_count_cone_points = TracePreviewSamplingMixin._sample_ray_count_cone_points
    _cone_azimuth_count = TracePreviewSamplingMixin._cone_azimuth_count

    def __init__(self, rows, trace_state, *, count: int = 31) -> None:
        self.rows = rows
        self._trace_state = dict(trace_state)
        self._count = int(count)

    def _resolved_trace_mode(self, *, system=None) -> dict:
        return self._trace_state

    def _current_ray_count(self) -> int:
        return self._count

    def _current_display_slice_axis(self) -> str:
        return "y"


def _rows(fname: str) -> list:
    info = load_python_data(_LAYOUTS / fname)
    return [nop._row_like(r) for r in info["surfaces"]]


def _mirror_face_metadata(rows) -> dict | None:
    for row in rows:
        advanced = getattr(row, "advanced", None)
        if isinstance(advanced, dict) and advanced.get("OpticalSolidFaces"):
            return advanced["OpticalSolidFaces"]
    return None


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # ---- RA-mirror: the promoted fold must break symmetry -> revolve a cone -------------
    ra_rows = _rows("machine_vision_AZ85_RA_Mirror.py")
    ra = _LaunchEditor(ra_rows, _RA_MIRROR_TRACE_STATE)

    osf = _mirror_face_metadata(ra_rows)
    if osf is None:
        failures.append("FAIL: RA-mirror layout exposes no OpticalSolidFaces metadata to detect")
    elif not _optical_solid_faces_have_mirror_fold(osf):
        failures.append("FAIL: the promoted mirror cube is not recognised as a mirror fold")

    # The mirror row must carry ONLY an axial slide (desp_z) -- no tilt / transverse
    # decentre -- so the fold is invisible to the old tilt/desp test and is detected
    # purely by the new OpticalSolidFaces mirror-face check (locks in the real fix).
    mirror_row = next(
        (r for r in ra_rows if isinstance(getattr(r, "advanced", None), dict)
         and r.advanced.get("OpticalSolidFaces")),
        None,
    )
    if mirror_row is not None:
        off_axis = max(
            abs(float(getattr(mirror_row, a, 0.0) or 0.0))
            for a in ("tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y")
        )
        if off_axis > _EPS:
            failures.append(
                f"FAIL: mirror row already breaks symmetry via tilt/desp ({off_axis:.2e}); "
                "the OpticalSolidFaces check is not what folds the launch"
            )

    if not ra._scene_breaks_rotational_symmetry():
        failures.append("FAIL: RA-mirror fold does not break rotational symmetry")
    if ra._launch_pupil_prefers_meridional_fan():
        failures.append("FAIL: RA-mirror launch still prefers a flat fan (should revolve a cone)")
    if ra._launch_cone_prefers_flat_fan():
        failures.append("FAIL: RA-mirror 3D launch cone stays flat (should revolve)")

    # The revolved cone has genuine off-meridian spokes + more than N samples.
    pts = np.asarray(ra._sample_ray_count_cone_points(25.0), dtype=float)
    if pts.shape[0] <= ra._current_ray_count():
        failures.append(
            f"FAIL: RA-mirror launch drew {pts.shape[0]} samples (<= ray count "
            f"{ra._current_ray_count()}); it did not revolve into a cone"
        )
    off_meridian = np.any((np.abs(pts[:, 0]) > _EPS) & (np.abs(pts[:, 1]) > _EPS))
    if not off_meridian:
        failures.append("FAIL: RA-mirror launch is still a flat fan (no off-meridian spokes)")

    # ---- A beam-splitter face must NOT be read as a mirror fold -------------------------
    # (a promoted BS keeps its real straight-through; it branches via has_beam_splitter,
    #  not via the symmetry-breaking fold). bugs/0185 gates the fold on a FULL mirror only.
    if osf is not None:
        bs_meta = copy.deepcopy(osf)
        faces = bs_meta.get("faces") if isinstance(bs_meta, dict) else None
        if isinstance(faces, list):
            for face in faces:
                if isinstance(face, dict) and str(face.get("function", "")) == "Mirror":
                    face["function"] = "Beam Splitter"
            if _optical_solid_faces_have_mirror_fold(bs_meta):
                failures.append("FAIL: a Beam Splitter face is wrongly treated as a mirror fold")

    # ---- Regression: an unfolded layout keeps the cheap flat fan (bug-0126 carve-out) --
    mv_rows = _rows("machine_vision_85mm_azure_datasheet_05x_20x.py")
    mv = _LaunchEditor(mv_rows, dict(_RA_MIRROR_TRACE_STATE))
    if mv._scene_breaks_rotational_symmetry():
        failures.append("FAIL: an unfolded MV layout wrongly breaks rotational symmetry")
    if not mv._launch_pupil_prefers_meridional_fan():
        failures.append("FAIL: the bug-0126 inline-solid carve-out lost its flat fan")
    if not mv._launch_cone_prefers_flat_fan():
        failures.append("FAIL: the bug-0126 inline-solid carve-out no longer keeps the flat 3D fan")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0186 promoted RA-mirror fold launches a cone")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] promoted RA-mirror fold breaks symmetry -> revolves a cone; unfolded scene keeps the flat fan (bugs/0186)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
