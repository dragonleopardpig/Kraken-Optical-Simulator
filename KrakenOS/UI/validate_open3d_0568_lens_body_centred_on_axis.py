"""Display-free guard for bugs/0568 -- after a lens SWAP the lens STEP body must still sit
ON the optical axis (flag_20260805_203837_379, machine_vision_AZ85_RA_Mirror_BS).

Reported: *"swap a lens, Lens STEP is not centered to optical axis, I think because of the
screw."*  Measured on the user's own scene (ELS-85 / 0703 -> PYRITE 45-85), the swapped
barrel's optical axis landed **7.255 mm** off the BS-reflect leg the surrogate sits on.

Root cause -- the swap preserves the overlay's placement NUMBERS (bugs/0381: "a swap changes
the lens, not where the user put it"), but those numbers only mean what they meant for the
body they were set for:

* ``_cad_mesh_aligned_to_optical_axis`` pivots its x/y rotations about the MESH's own bounding
  box, so on a rotated overlay (this scene is 0433-frozen: the lens is turned onto the leg with
  ``lens_step_rotation_y_deg = 270``) the transverse seat is a function of the body's axial
  half-extent and of its transverse bbox midpoint -- which the one-sided screw boss shifts.
  ELS-85 -> PYRITE moves that constant by 5.111 mm.
* the axial datum pin ``target_front_z`` is added to the aligned +Z AFTER those rotations, so a
  270 deg rotation redirects it SIDEWAYS; the swapped block's front-datum station moved the
  body a further 3.220 mm.

Fix: preserve the SEAT, not the numbers.  ``center_lens_body_on_surrogate_axis`` measures where
the body's CAD BARREL axis actually is (probe points on the cylinder axis pushed through the
very same alignment the display uses) and corrects the placement offset by the TRANSVERSE
component only, so the axial registration the swap just settled is untouched.  The same command
backs the right-click item the user asked for -- "Center Lens Body -> Surrogate Axis (no axial
shift)" -- because "Center Picked Face -> Optical Axis" moves all three axes and so slides the
barrel off the surrogate along the axis.

Checks (headless, no VTK window, no Tk):
- A  SYNTHETIC (always runs): two barrels of different length, each with a one-sided screw
  boss, on a rotated frozen scene.
  * FAIL-BEFORE: with the numbers preserved verbatim the replacement lands > 1 mm off-axis.
  * FIX: the centring brings it to ~0, and does NOT move it along the axis.
  * The screw boss is irrelevant to the result: bbox centring would still leave it off by half
    the boss, the CAD-axis centring does not.
  * NO-OP on a straight (unrotated) scene -- the correction must be exactly zero there, so this
    can never disturb a scene that was already right.
  * The glue REFERENCE follows the correction (else one "Glue STEP to Surrogate" click undoes
    it), and an undecidable body (no cylinder axis) moves NOTHING.
- B  REAL fixtures (skip-if-absent): the flagged scene's own numbers, ELS-85 -> PYRITE 45-85.
  The replay first reproduces the flag's RECORDED lens actor bounds, so the 7.255 mm is the
  user's geometry and not a model of it.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0568_lens_body_centred_on_axis
Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_REAL_OLD_LENS = PROJECT_ROOT / "attachment" / "Lens" / "0703-005-000-40-EXC" / "0703-005-000-40_PA_a_STEP.stp"
_REAL_NEW_LENS = (
    PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517" / "1072517_00165969_001.stp"
)

# The flagged scene as the recorder captured it (attachment/recorded_bug_repros/
# flag_20260805_203837_379/state.json + the layout it names):
#   the lens surrogate's datums sit on the BS-reflect leg  y = 0, z = 55.359, along +x
#   front datum world x 78.085 (station 118.970) / rear datum world x 117.604
#   lens overlay pose: reverse, rot_y 270, roll 180, placement (103.8313, 0, -93.2068)
FLAG_LEG_Z = 55.3585
FLAG_FRONT_DATUM_X = 78.085
FLAG_REAR_DATUM_X = 117.604
FLAG_FRONT_DATUM_STATION = 118.970
FLAG_LENS_PLACEMENT = (103.8313, -0.0, -93.2068)
FLAG_LENS_BOUNDS = (76.574, 124.374, -24.248, 24.250, 23.855, 75.471)


def _synthetic_barrel(*, length: float, radius: float = 12.0, boss: float = 3.0):
    """A lens barrel about the axis (0, 0, z), z in [0, length], PLUS a one-sided screw boss
    that protrudes ``boss`` mm in +x -- the asymmetry that skews a bounding box (and the
    feature the user blamed: "I think because of the screw")."""
    thetas = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    rings = []
    for z in np.linspace(0.0, float(length), 12):
        rings.append(
            np.column_stack(
                [radius * np.cos(thetas), radius * np.sin(thetas), np.full(thetas.shape, float(z))]
            )
        )
    body = np.vstack(rings)
    mid = 0.5 * float(length)
    screw = np.array(
        [
            [radius + boss, 0.0, mid - 1.0],
            [radius + boss, 0.0, mid + 1.0],
            [radius + boss, 1.5, mid],
            [radius + boss, -1.5, mid],
        ],
        dtype=float,
    )
    return np.vstack([body, screw])


def _frozen_rows(*, block_length: float, rotated: bool):
    """The flagged scene's shape: Object -> lens block (front/rear optical vertex datums) ->
    Image.  ``rotated`` bakes the 0433-frozen placement that turns the block onto the +X leg;
    otherwise the rows stay on the straight +Z axis."""
    from KrakenOS.UI.surface_table_model import SurfaceRow

    station_front = FLAG_FRONT_DATUM_STATION
    spec = [
        ("Object at 1X", station_front),
        ("Front Optical Vertex Datum", float(block_length)),
        ("Rear Optical Vertex Datum", 60.0),
        ("Image / Sensor at 1X", 0.0),
    ]
    rows = []
    station = 0.0
    for index, (name, thickness) in enumerate(spec):
        row = SurfaceRow(name=name, thickness=float(thickness), diameter=29.0, glass="AIR")
        if rotated and index in (1, 2):
            # WORLD placement (bugs/0433 freeze): desp + tilt ARE the final pose.
            row.desp_x = FLAG_FRONT_DATUM_X + (0.0 if index == 1 else float(block_length))
            row.desp_y = 0.0
            row.desp_z = FLAG_LEG_Z - station
            row.tilt_x, row.tilt_y, row.tilt_z = 0.0, -90.0, -180.0
            row.axis_move = 0.0
            row.advanced = {"ScenePlacement": {"stay_put_freeze": {"reason": "fold_removed"}}}
        station += float(thickness)
        rows.append(row)
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    return rows


def _editor(rows, *, pose, meshes=None, path_key="A", step_path=None):
    """A real ``KrakenLayoutEditor`` with only the state these paths read set on it -- every
    decision below is the shipped code's.  (Tk's ``__getattr__`` delegates to ``self.tk`` and
    RECURSES on a missing attribute, so nothing may be left to a getattr default.)

    ``meshes`` stands a synthetic point cloud + its known cylinder axis in for the OCC read;
    without it the real loader and the real OCC extraction run on ``step_path``.
    """
    import pyvista as pv

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = object.__new__(KrakenLayoutEditor)
    editor.rows = rows
    editor.append_debug = lambda *args, **kwargs: None
    editor._external_cad_mesh_cache = {}
    editor.imported_lens_step_path = Path(step_path) if step_path is not None else Path(
        f"synthetic-{path_key}.step"
    )
    editor.imported_optical_step_path = None
    editor.imported_led_step_path = None
    editor.imported_camera_step_path = None
    editor.lens_step_largest_component_only = True
    editor.lens_step_reverse_direction = bool(pose.get("reverse", False))
    editor.lens_step_rotation_x_deg = float(pose.get("rot_x", 0.0))
    editor.lens_step_rotation_y_deg = float(pose.get("rot_y", 0.0))
    editor.lens_step_rotation_z_deg = float(pose.get("rot_z", 0.0))
    editor.lens_step_axis_offset_xy = (0.0, 0.0)
    editor.lens_step_placement_offset_xyz = tuple(float(v) for v in pose.get("placement", (0.0, 0.0, 0.0)))
    editor.lens_step_resize = None
    editor._step_glue_reference_offsets = {}
    editor._step_glue_reference_datum_mids = {}
    editor._step_overlay_axis_anchor_by_label = {}
    editor._live_step_overlay_trace_plan_cache = {}
    editor._open3d_step_cache_warmup_pending = False
    editor._open3d_step_cache_warmup_process = None
    # The display fold is None on every 0433-frozen scene (the durable frozen-fold gate the
    # 0547 swap fix names) -- which is exactly the regime this bug lives in.
    editor._optical_axis_fold_world_transform_for_row = lambda row_index: None
    if meshes is not None:
        clouds = {
            str(key): pv.PolyData(np.asarray(points, dtype=float)) for key, points in meshes.items()
        }
        editor._load_step_mesh = lambda path, **kwargs: clouds[str(path)]
        editor._step_primary_cylinder_axis = lambda path: np.array([0.0, 0.0, 1.0], dtype=float)
        editor._step_primary_cylinder_axis_point = lambda path: np.array([0.0, 0.0, 0.0], dtype=float)
        # A synthetic point cloud carries no glass block, so the datum pin is the plain
        # front-datum one -- the same branch a rotated overlay takes on the real scene.
        editor._step_optical_glass_axial_metrics = lambda path: None
    # Placement-setter side effects (cache invalidation) are not what this guard is about.
    editor._invalidate_step_overlay_face_metadata_cache = lambda label: None
    editor._invalidate_preview_scene_trace = lambda: None
    editor._step_overlay_mutation_signature = lambda label: ()
    return editor


def _off_axis_mm(editor):
    """Transverse distance from the lens body's optical axis to the surrogate's, plus the
    body's position ALONG that axis (which a centring must never change)."""
    body = editor._lens_step_overlay_axis_world_line()
    axis = editor._lens_surrogate_optical_axis_line()
    if body is None or axis is None:
        return None, None
    gap = np.asarray(axis[0], dtype=float) - np.asarray(body[0], dtype=float)
    along = float(np.dot(gap, axis[1]))
    transverse = gap - along * np.asarray(axis[1], dtype=float)
    return float(np.linalg.norm(transverse)), along


def _check_synthetic(ok, notes) -> None:
    old_body = _synthetic_barrel(length=52.9)
    new_body = _synthetic_barrel(length=47.8, boss=5.0)
    meshes = {"synthetic-A.step": old_body, "synthetic-B.step": new_body}
    pose = {"rot_x": 0.0, "rot_y": 270.0, "rot_z": 180.0, "placement": (100.0, 0.0, -90.0)}

    # The scene as it stands with the OLD lens: whatever seat it has is the reference.
    before_editor = _editor(_frozen_rows(block_length=52.9, rotated=True), pose=pose, meshes=meshes)
    old_off, _old_along = _off_axis_mm(before_editor)
    ok(old_off is not None, "A0: the CAD barrel axis of a placed lens body is measurable")

    # ... and after the swap, with the SAME preserved numbers and the replacement body.
    after = _editor(
        _frozen_rows(block_length=47.8, rotated=True), meshes=meshes, pose=pose, path_key="B"
    )
    swapped_off, swapped_along = _off_axis_mm(after)
    if swapped_off is None:
        notes.append("FAIL: A1 could not measure the swapped body's optical axis")
        return
    ok(
        swapped_off > 1.0,
        f"A1 (the bug, fail-before): preserving the placement numbers verbatim leaves the "
        f"replacement body {swapped_off:.3f} mm off the surrogate axis",
    )

    result = after.center_lens_body_on_surrogate_axis(context="test")
    fixed_off, fixed_along = _off_axis_mm(after)
    ok(
        result is not None and bool(result.get("moved")),
        "A2a: the centring reports that it moved the body",
    )
    ok(
        fixed_off is not None and fixed_off < 1.0e-6,
        f"A2b (the fix): the body's optical axis lands ON the surrogate axis "
        f"({swapped_off:.3f} -> {(fixed_off if fixed_off is not None else float('nan')):.2e} mm)",
    )
    ok(
        result is not None and str(result.get("source")) == "cad_barrel_axis",
        "A2c: the seat is measured from the CAD barrel axis, not from a bounding box",
    )
    ok(
        fixed_along is not None and abs(float(fixed_along) - float(swapped_along)) < 1.0e-9,
        f"A3 (the user's requirement): the correction does NOT shift the body along the "
        f"optical axis (along-axis {swapped_along:.6f} -> "
        f"{(fixed_along if fixed_along is not None else float('nan')):.6f} mm)",
    )

    # The screw boss: had the centring used the bounding box, the barrel would still be off by
    # half the boss. Prove the shipped result is NOT that.
    mesh_points = np.asarray(new_body, dtype=float)
    boss_bias = 0.5 * (float(mesh_points[:, 0].max()) + float(mesh_points[:, 0].min()))
    ok(
        abs(boss_bias) > 1.0 and (fixed_off is not None and fixed_off < 0.5 * abs(boss_bias)),
        f"A4: the one-sided screw boss offsets the body's bbox midpoint by {boss_bias:.3f} mm "
        f"and the centred body is still on-axis -- the boss cannot pull it off",
    )

    # The glue reference must follow, or one "Glue STEP to Surrogate" click restores the
    # off-axis placement this just corrected (bugs/0497 / bugs/0503).
    reference = after._step_glue_reference_offset_xyz("lens")
    live = np.asarray(after._step_placement_offset_xyz("lens"), dtype=float)
    ok(
        reference is not None and float(np.linalg.norm(np.asarray(reference) - live)) < 1.0e-9,
        "A5: the glue REFERENCE is re-recorded at the corrected placement",
    )

    # A straight, unrotated scene is already right: the correction must be exactly zero, so
    # this can never disturb one.
    straight_pose = {"rot_x": 0.0, "rot_y": 0.0, "rot_z": 0.0, "placement": (0.0, 0.0, 0.0)}
    straight = _editor(
        _frozen_rows(block_length=47.8, rotated=False), meshes=meshes, pose=straight_pose, path_key="B"
    )
    straight_off, straight_along = _off_axis_mm(straight)
    straight_result = straight.center_lens_body_on_surrogate_axis(context="test")
    straight_after, _ = _off_axis_mm(straight)
    ok(
        straight_off is not None and straight_off < 1.0e-9,
        f"A6a: an unrotated overlay is already centred by the bugs/0077 CAD-axis anchor "
        f"({(straight_off if straight_off is not None else float('nan')):.2e} mm off)",
    )
    ok(
        straight_result is not None and not bool(straight_result.get("moved")),
        "A6b: so the centring is a NO-OP there -- it reports no move",
    )
    ok(
        straight_after is not None and straight_after < 1.0e-9,
        "A6c: ... and the body has not moved",
    )

    # An undecidable body moves NOTHING (a guess here flings it off the scene).
    blind = _editor(
        _frozen_rows(block_length=47.8, rotated=True), meshes=meshes, pose=pose, path_key="B"
    )
    blind._step_primary_cylinder_axis = lambda path: None
    blind._step_primary_cylinder_axis_point = lambda path: None
    placement_before = tuple(blind._step_placement_offset_xyz("lens"))
    blind_result = blind.center_lens_body_on_surrogate_axis(context="test")
    ok(
        blind_result is None
        and tuple(blind._step_placement_offset_xyz("lens")) == placement_before,
        "A7: a body with no derivable optical axis is refused, not guessed at",
    )

    # The picked-feature fallback (the right-click path) centres transversely too.
    picked = _editor(
        _frozen_rows(block_length=47.8, rotated=True), meshes=meshes, pose=pose, path_key="B"
    )
    line = picked._lens_step_overlay_axis_world_line()
    picked_result = picked.center_lens_body_on_surrogate_axis(
        feature_center_xyz=line[0], context="test"
    )
    picked_off, picked_along = _off_axis_mm(picked)
    ok(
        picked_result is not None
        and str(picked_result.get("source")) == "picked_feature"
        and picked_off is not None
        and picked_off < 1.0e-6,
        "A8: the picked-feature fallback centres the body on the axis as well",
    )
    ok(
        picked_along is not None and abs(float(picked_along) - float(swapped_along)) < 1.0e-9,
        "A9: ... and it, too, never shifts the body along the axis",
    )


def _check_real_swap_wiring(ok, notes) -> None:
    """The SWAP itself must do this -- a command nobody calls fixes nothing.  Drives the real
    ``swap_imaging_lens_from_folder`` (only the file I/O is stubbed) on a frozen scene carrying
    a lens overlay, and checks the body comes out on the axis."""
    from types import SimpleNamespace

    from KrakenOS.UI.validate_open3d_0546_swap_keeps_inblock_solid import _run_real_swap

    meshes = {
        "synthetic-A.step": _synthetic_barrel(length=52.9),
        "synthetic-B.step": _synthetic_barrel(length=47.8, boss=5.0),
    }
    pose = {"rot_x": 0.0, "rot_y": 270.0, "rot_z": 180.0, "placement": (100.0, 0.0, -90.0)}
    editor = _editor(_frozen_rows(block_length=52.9, rotated=True), pose=pose, meshes=meshes)
    editor.status_var = SimpleNamespace(set=lambda value: None)
    editor.append_progress = lambda *args, **kwargs: None
    before, _along_before = _off_axis_mm(editor)

    swapped, result, errors = _run_real_swap(
        [
            ("Front Optical Vertex Datum", 4.0),
            ("Blackbox Group 1", 19.9),
            ("Aperture Stop F/2.8", 19.9),
            ("Blackbox Group 2", 4.0),
            ("Rear Optical Vertex Datum", 60.0),
        ],
        editor=editor,
        # The replacement lens's own settings block -- what rewires the overlay to the new body.
        settings={"lens_step_path": "synthetic-B.step", "lens_step_largest_component_only": True},
    )
    if errors or result is None:
        notes.append(f"FAIL: C0 the swap refused ({errors[0] if errors else 'no model'!r})")
        return
    ok(
        str(swapped.imported_lens_step_path) == "synthetic-B.step",
        "C0: the swap rewired the overlay to the replacement body",
    )
    after, _along_after = _off_axis_mm(swapped)
    ok(
        after is not None and after < 1.0e-6,
        f"C1 (the wiring): the REAL swap leaves the new body on the optical axis "
        f"({(before if before is not None else float('nan')):.3f} mm -> "
        f"{(after if after is not None else float('nan')):.2e} mm)",
    )
    centring = swapped.__dict__.get("_swap_lens_axis_centring")
    ok(
        isinstance(centring, dict) and bool(centring.get("moved")),
        "C2: ... and it reports the correction it made, so a swap that moved the overlay "
        "sideways is visible rather than silent",
    )


def _check_menu_wiring(ok, notes) -> None:
    """The user asked for a MENU option, so the menu is part of the deliverable."""
    import inspect

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.panels import open3d_top_controls
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    ok(
        callable(getattr(ScenePlacementMixin, "center_lens_body_on_surrogate_axis", None)),
        "D0: the editor exposes center_lens_body_on_surrogate_axis",
    )
    ok(
        callable(getattr(Kraken3DInspector, "center_lens_body_on_surrogate_axis", None))
        and "center_lens_body_on_surrogate_axis" in inspect.getsource(open3d_top_controls),
        "D1: the CAD / target menu offers it (and the inspector command it names exists)",
    )
    handler = getattr(Open3DFaceAssignmentService, "_center_lens_body_on_surrogate_axis_from_context", None)
    menu_source = inspect.getsource(Open3DFaceAssignmentService)
    ok(
        callable(handler) and "_center_lens_body_on_surrogate_axis_from_context" in menu_source,
        "D2: the lens STEP right-click menu offers it too",
    )


def _check_real_fixtures(ok, notes) -> None:
    if not (_REAL_OLD_LENS.exists() and _REAL_NEW_LENS.exists()):
        notes.append(
            "SKIP: the flagged vendor lens STEPs are not in this checkout "
            "(attachment/ is gitignored) -- section B not run"
        )
        return
    rows = _frozen_rows(block_length=(FLAG_REAR_DATUM_X - FLAG_FRONT_DATUM_X), rotated=True)
    editor = _editor(
        rows,
        pose={
            "reverse": True,
            "rot_x": 0.0,
            "rot_y": 270.0,
            "rot_z": 180.0,
            "placement": FLAG_LENS_PLACEMENT,
        },
        step_path=_REAL_NEW_LENS,
    )

    # The station the datum pin reads must be the flagged scene's, or this is a different case.
    station = float(editor._lens_front_datum_z())
    ok(
        abs(station - FLAG_FRONT_DATUM_STATION) < 1.0e-6,
        f"B0: the reconstructed scene's front-datum station is the flag's "
        f"({station:.3f} == {FLAG_FRONT_DATUM_STATION})",
    )

    mesh = editor._transformed_imported_lens_step_mesh()
    if mesh is None:
        notes.append("SKIP: the lens overlay mesh could not be built (no pyvista/OCC?)")
        return
    bounds = tuple(float(v) for v in mesh.bounds)
    delta = max(abs(a - b) for a, b in zip(bounds, FLAG_LENS_BOUNDS))
    ok(
        delta < 0.05,
        f"B1: the shipped alignment reproduces the FLAG's recorded lens actor bounds to "
        f"{delta:.4f} mm -- the numbers below are the user's geometry, not a model of it",
    )

    before, along_before = _off_axis_mm(editor)
    ok(
        before is not None and 7.0 < before < 7.5,
        f"B2 (the report): the swapped PYRITE barrel sits "
        f"{(before if before is not None else float('nan')):.3f} mm off the surrogate axis "
        f"(the user: \"Lens STEP is not centered to optical axis\")",
    )
    result = editor.center_lens_body_on_surrogate_axis(context="test")
    after, along_after = _off_axis_mm(editor)
    ok(
        result is not None and bool(result.get("moved")) and after is not None and after < 1.0e-6,
        f"B3 (the fix): centring puts it on the axis "
        f"({(before if before is not None else float('nan')):.3f} -> "
        f"{(after if after is not None else float('nan')):.2e} mm)",
    )
    ok(
        along_before is not None
        and along_after is not None
        and abs(float(along_after) - float(along_before)) < 1.0e-9,
        "B4: on the real body too, nothing moves along the optical axis",
    )


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    try:
        _check_synthetic(ok, notes)
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"FAIL: section A raised ({type(exc).__name__}: {exc})")
    try:
        _check_real_swap_wiring(ok, notes)
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"FAIL: section C raised ({type(exc).__name__}: {exc})")
    try:
        _check_menu_wiring(ok, notes)
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"FAIL: section D raised ({type(exc).__name__}: {exc})")
    try:
        _check_real_fixtures(ok, notes)
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"FAIL: section B raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Lens-body optical-axis centring validation passed.")
        return 0
    print("Lens-body optical-axis centring validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
