"""Display-free guard for the genuine 3D navigation cube's orientation math.

The Open 3D inspector's old upper-right "cube" was VTK's ``vtkCameraOrientationWidget``,
which renders as three axis balls -- not a clickable CAD cube. The replacement is a real
FreeCAD-style annotated cube: 6 faces + 12 edges + 8 corners = 26 clickable orientations,
plus discrete rotation-step arrows. All of the pose/pick/roll math lives, VTK-free, in
``KrakenOS.UI.services.nav_cube_orientation`` so it can be pinned here headless (the VTK
widget itself needs a human eyeball).

This guard pins four contracts:

  (A) ALL 26 ORIENTATIONS CLASSIFY: a left-click on the cube surface picks a LOCAL hit
      point in ``[-0.5, 0.5]^3``; ``classify_pick`` must turn each of the 26 representative
      surface points into its own sign triple, partitioning cleanly into 6 faces / 12 edges
      / 8 corners, and reject a stray (interior) pick with ``None``.
  (B) FACES ARE THE CARDINAL PRESETS: clicking a cube FACE must be byte-identical to
      pressing the matching ``+yz``/``-yz``/``+xy``/``-xy``/``+xz``/``-xz`` toolbar button.
      This runs the REAL ``Kraken3DInspector.set_camera_preset`` against a fake camera and
      checks the resulting (offset, view_up) equals ``orientation_pose(face)`` -- so any
      drift between the preset table and the cube faces trips the guard.
  (C) EDGES & CORNERS STAY UPRIGHT: every edge/corner pose points outward along its sign
      triple with a unit ``view_up`` that is perpendicular to the sight line and keeps a
      positive world-+Y component (the projected-up rule that keeps oblique views upright).
  (D) DISCRETE ROLL STEP == vtkCamera.Roll: the rotation-step arrows roll ``view_up`` about
      the sight line; ``roll_view_up`` must match ``vtkCamera.Roll`` (when VTK is importable)
      and always preserve norm + perpendicularity, with a 90 deg step of +Y about +Z landing
      on -X and a 360 deg step returning to start.

Run: PYTHONPATH=. .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_nav_cube_orientation
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np

from KrakenOS.UI.services.nav_cube_orientation import (
    FACE_LABELS,
    ORIENTATION_KEYS,
    classify_pick,
    iso_corner_pose,
    orientation_kind,
    orientation_pose,
    roll_view_up,
)

# Which cardinal-preset button each cube face reproduces (see set_camera_preset).
FACE_TO_PRESET: dict[tuple[int, int, int], str] = {
    (1, 0, 0): "+yz",
    (-1, 0, 0): "-yz",
    (0, 0, 1): "+xy",
    (0, 0, -1): "-xy",
    (0, 1, 0): "+xz",
    (0, -1, 0): "-xz",
}


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _surface_point(sign: tuple[int, int, int]) -> list[float]:
    """A representative LOCAL hit point for a sign triple: on the +/-0.5 face for each
    extreme axis, dead-centre (0.0) for each mid axis."""
    return [0.5 * s if s else 0.0 for s in sign]


# --- (A) all 26 orientations classify + partition ---------------------------------------- #

def _check_classification() -> Check:
    kinds = {"face": 0, "edge": 0, "corner": 0}
    misses: list[str] = []
    seen: set[tuple[int, int, int]] = set()
    for sign in ORIENTATION_KEYS:
        got = classify_pick(_surface_point(sign))
        if got != sign:
            misses.append(f"{sign}->{got}")
            continue
        seen.add(sign)
        kinds[orientation_kind(sign)] += 1
    expected = set(triple for triple in product((-1, 0, 1), repeat=3) if any(triple))
    stray = classify_pick([0.0, 0.0, 0.0])  # interior pick -> ignored
    near_stray = classify_pick([0.30, 0.10, -0.20])  # all sub-threshold -> ignored
    ok = (
        not misses
        and seen == expected
        and kinds == {"face": 6, "edge": 12, "corner": 8}
        and stray is None
        and near_stray is None
    )
    return Check(
        "ALL 26 ORIENTATIONS CLASSIFY: each cube-surface pick round-trips to its own sign "
        "triple (6 faces / 12 edges / 8 corners) and an interior pick is rejected as None",
        ok,
        f"count={len(seen)} partition={kinds} stray={stray} near_stray={near_stray} "
        f"misses={misses or 'none'}",
    )


# --- (B) faces reproduce the cardinal presets (runs the REAL set_camera_preset) ---------- #

class _FakeCamera:
    def __init__(self) -> None:
        self.position = None
        self.focal = None
        self.view_up = None
        self.parallel = 0
        self.parallel_scale = None

    def SetPosition(self, x, y, z):
        self.position = np.array([x, y, z], dtype=float)

    def SetFocalPoint(self, x, y, z):
        self.focal = np.array([x, y, z], dtype=float)

    def SetViewUp(self, x, y, z):
        self.view_up = np.array([x, y, z], dtype=float)

    def SetParallelProjection(self, flag):
        self.parallel = int(flag)

    def SetParallelScale(self, scale):
        self.parallel_scale = float(scale)


class _FakeRenderer:
    def __init__(self, camera) -> None:
        self._camera = camera

    def GetActiveCamera(self):
        return self._camera


def _preset_pose(preset: str, bounds: np.ndarray):
    """Run the production ``set_camera_preset`` against a fake camera and return the
    resulting (normalised offset, view_up) about the scene centre."""
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    camera = _FakeCamera()
    inspector = object.__new__(Kraken3DInspector)
    inspector._renderer = _FakeRenderer(camera)
    inspector._camera_preset = None
    inspector._iso_up_axis = "y"
    # Shadow the heavy scene-dependent helpers (instance attrs win over the class methods).
    inspector._camera_fit_bounds = lambda: bounds
    inspector._render_aspect = lambda: 1.0
    inspector._reset_camera_clipping_range_for_scene = lambda: None
    inspector._reorient_thickness_labels_for_camera = lambda: True
    inspector.render = lambda: None

    Kraken3DInspector.set_camera_preset(inspector, preset)
    center = np.array(
        [0.5 * (bounds[0] + bounds[1]), 0.5 * (bounds[2] + bounds[3]), 0.5 * (bounds[4] + bounds[5])],
        dtype=float,
    )
    offset = camera.position - center
    norm = float(np.linalg.norm(offset))
    return (offset / norm if norm > 1e-12 else offset), camera.view_up


def _check_face_preset_parity() -> Check:
    # Asymmetric, off-origin bounds so a centre-handling bug can't hide.
    bounds = np.array([0.0, 20.0, 10.0, 50.0, -30.0, 30.0], dtype=float)
    worst = 0.0
    bad: list[str] = []
    for face, preset in FACE_TO_PRESET.items():
        try:
            real_offset, real_up = _preset_pose(preset, bounds)
        except Exception as exc:  # pragma: no cover - would signal an API shift
            bad.append(f"{FACE_LABELS[face]}({preset}) raised {exc!r}")
            continue
        want_offset, want_up = orientation_pose(face)
        d_off = float(np.linalg.norm(real_offset - np.asarray(want_offset, dtype=float)))
        d_up = float(np.linalg.norm(real_up - np.asarray(want_up, dtype=float)))
        worst = max(worst, d_off, d_up)
        if d_off > 1e-6 or d_up > 1e-6:
            bad.append(
                f"{FACE_LABELS[face]}({preset}) preset offset {np.round(real_offset,4)}/up "
                f"{np.round(real_up,4)} != cube {want_offset}/{want_up}"
            )
    return Check(
        "FACES ARE THE CARDINAL PRESETS: each cube face's pose equals the real "
        "set_camera_preset camera for the matching toolbar button (no preset/cube drift)",
        not bad,
        f"max deviation={worst:.2e} " + ("; ".join(bad) if bad else "all 6 faces match"),
    )


# --- (C) edges & corners stay upright and point outward ---------------------------------- #

def _check_edges_corners_upright() -> Check:
    bad: list[str] = []
    n_edge = n_corner = 0
    iso_octant = (-1, 1, 1)
    iso_dir = np.array([-0.95, 0.55, 0.8], dtype=float)
    iso_dir = iso_dir / float(np.linalg.norm(iso_dir))
    for sign in ORIENTATION_KEYS:
        kind = orientation_kind(sign)
        if kind == "face":
            continue
        offset, view_up = orientation_pose(sign)
        offset = np.asarray(offset, dtype=float)
        view_up = np.asarray(view_up, dtype=float)
        off_unit = abs(float(np.linalg.norm(offset)) - 1.0)
        up_unit = abs(float(np.linalg.norm(view_up)) - 1.0)
        upright = float(view_up[1])                       # positive world-+Y => upright
        if kind == "edge":
            n_edge += 1
            triple = np.asarray(sign, dtype=float)
            triple /= float(np.linalg.norm(triple))
            outward = float(np.dot(offset, triple))       # points along the sign triple
            perp = abs(float(np.dot(offset, view_up)))    # up perpendicular to sight line
            if outward < 1.0 - 1e-6 or off_unit > 1e-6 or up_unit > 1e-6 or perp > 1e-6 or upright <= 1e-6:
                bad.append(
                    f"edge {sign}: outward={outward:.4f} off_unit_err={off_unit:.1e} "
                    f"up_unit_err={up_unit:.1e} perp={perp:.1e} up.Y={upright:.4f}"
                )
        else:  # corner -- bugs/0252 ISO-style per-octant pose (world-+Y up, sign-consistent)
            n_corner += 1
            want_off, want_up = iso_corner_pose(sign)
            matches_iso = np.allclose(offset, want_off, atol=1e-9) and np.allclose(view_up, want_up, atol=1e-9)
            octant_ok = bool(np.all(np.sign(offset).astype(int) == np.asarray(sign, dtype=int)))
            up_world_y = abs(view_up[0]) < 1e-9 and abs(view_up[2]) < 1e-9 and upright > 1.0 - 1e-9
            if not (matches_iso and octant_ok and up_world_y and off_unit <= 1e-6 and up_unit <= 1e-6):
                bad.append(
                    f"corner {sign}: iso_match={matches_iso} octant_ok={octant_ok} "
                    f"up={np.round(view_up, 3).tolist()} off_unit_err={off_unit:.1e}"
                )
    # The ISO octant corner reproduces the ISO toolbar direction exactly (cube corner == ISO button).
    iso_off, iso_up = orientation_pose(iso_octant)
    if not (np.allclose(iso_off, iso_dir, atol=1e-9) and np.allclose(iso_up, [0.0, 1.0, 0.0], atol=1e-9)):
        bad.append(
            f"ISO octant {iso_octant}: offset {np.round(iso_off, 4).tolist()} != ISO dir "
            f"{np.round(iso_dir, 4).tolist()} / up {np.round(iso_up, 3).tolist()}"
        )
    ok = not bad and n_edge == 12 and n_corner == 8
    return Check(
        "EDGES PROJECTED-UP + CORNERS ISO (bugs/0252): the 12 edges point outward with a "
        "unit view_up perpendicular to the sight line (projected-up); the 8 corners reproduce "
        "the ISO toolbar view for their octant (world-+Y up, sign-consistent), and the ISO "
        "octant (-1,+1,+1) equals the ISO button direction (-0.95,0.55,0.8)",
        ok,
        f"edges={n_edge} corners={n_corner} " + ("; ".join(bad) if bad else "edges upright/outward, corners ISO-matched"),
    )


# --- (D) discrete roll step matches vtkCamera.Roll --------------------------------------- #

def _check_roll_step() -> Check:
    view_dir = np.array([0.0, 0.0, 1.0])
    up0 = [0.0, 1.0, 0.0]
    notes: list[str] = []
    ok = True

    # structural: 90 deg about +Z takes +Y -> -X; +/-angle cancels; 360 returns; norm kept.
    r90 = np.asarray(roll_view_up(view_dir, up0, 90.0))
    if not (np.allclose(r90, [-1.0, 0.0, 0.0], atol=1e-6)):
        ok = False
        notes.append(f"90deg roll -> {np.round(r90,4)} (want [-1,0,0])")
    r360 = np.asarray(roll_view_up(view_dir, up0, 360.0))
    if not np.allclose(r360, up0, atol=1e-6):
        ok = False
        notes.append(f"360deg roll -> {np.round(r360,4)} (want start)")
    fwd = roll_view_up(view_dir, up0, 37.0)
    back = np.asarray(roll_view_up(view_dir, fwd, -37.0))
    if not np.allclose(back, up0, atol=1e-6):
        ok = False
        notes.append(f"+37/-37 roll -> {np.round(back,4)} (want start)")
    for ang in (15.0, 45.0, 90.0, -30.0):
        r = np.asarray(roll_view_up(view_dir, up0, ang))
        if abs(float(np.linalg.norm(r)) - 1.0) > 1e-9 or abs(float(np.dot(r, view_dir))) > 1e-9:
            ok = False
            notes.append(f"roll {ang} not unit/perp: {np.round(r,4)}")

    # parity with the real vtkCamera.Roll it stands in for (skip only if VTK is absent).
    try:
        import vtk

        cam = vtk.vtkCamera()
        cam.SetPosition(0.0, 0.0, -10.0)
        cam.SetFocalPoint(0.0, 0.0, 0.0)
        for ang in (15.0, 45.0, 90.0, -30.0):
            cam.SetViewUp(*up0)
            cam.Roll(ang)
            vtk_up = np.asarray(cam.GetViewUp(), dtype=float)
            mine = np.asarray(roll_view_up(view_dir, up0, ang))
            if not np.allclose(vtk_up, mine, atol=1e-6):
                ok = False
                notes.append(f"vtk mismatch @ {ang}: vtk {np.round(vtk_up,4)} != {np.round(mine,4)}")
        notes.append("matches vtkCamera.Roll")
    except Exception as exc:  # pragma: no cover - headless without VTK
        notes.append(f"vtk unavailable ({exc!r}); structural roll checks only")

    return Check(
        "DISCRETE ROLL STEP == vtkCamera.Roll: the rotation-step arrows roll view_up about "
        "the sight line, matching vtkCamera.Roll and preserving norm + perpendicularity",
        ok,
        "; ".join(notes),
    )


def validate_nav_cube_orientation() -> list[Check]:
    return [
        _check_classification(),
        _check_face_preset_parity(),
        _check_edges_corners_upright(),
        _check_roll_step(),
    ]


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_nav_cube_orientation()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_nav_cube_orientation()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Nav-cube orientation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
