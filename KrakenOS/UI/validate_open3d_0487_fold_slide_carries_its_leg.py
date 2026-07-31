"""bugs/0487 (0485 rule 3) -- slide a folder and everything snapped to its leg comes with it.

The user's rule 3: *"If the user slide the elements that introduce a fold axis, then all the
snapped elements should follow the fold axis."*

Measured on ``attachment/machine_vision_AZ85_RA_Mirror_BS.py`` before this existed -- dragging the
RA mirror 20 mm along its incoming leg:

    fold point   (229.930, 0, 53.803) -> (209.930, 0, 53.803)
    sensor       transverse 0.0000 mm -> 20.0000 mm      (left behind, OFF the beam)
    camera       did not move at all

The sanctioned leg-split writer never had this problem -- it re-seats the sensor and camera itself
(bugs/0447) -- but it is a different intent: it trades ``near`` against ``far`` holding the TOTAL,
so the sensor stays on the leg while its arc-length CHANGES (51.5 -> 71.5 mm on that same slide).
A free drag has no total to preserve; rule 3 is the rigid carry, arc-length held.

The criterion is stated in the tree's own terms, which is what makes it falsifiable: an element
follows iff its TRANSVERSE offset from the emitted leg stays ~0 while the leg's origin moves.

Note the deliberate consequence, recorded rather than hidden: a rigid carry changes the optical
path length, hence the focus. Sliding a fold mirror away from the lens with the camera bolted to
its arm genuinely lengthens lens -> sensor. The conjugate-PRESERVING slide already exists as the
leg-split constraint.

Sections A-B are display-free; C drives the real scene and SKIPs when it is not checked out.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0487_fold_slide_carries_its_leg
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


class _Row:
    def __init__(self, thickness=0.0, desp=(0.0, 0.0, 0.0), surface="Standard"):
        self.thickness = float(thickness)
        self.desp_x, self.desp_y, self.desp_z = (float(v) for v in desp)
        self.surface = surface
        self.name = surface


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        from KrakenOS.UI.services import optical_axis_tree as axis_tree
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: optical_axis_tree unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. membership: who rides on a folder's leg --------------------------------------
    # object -> BS(row 1, branching, emits +x) -> mirror(row 2 on that leg, emits -z) -> sensor(3)
    rows = [
        _Row(surface="Object"),
        _Row(desp=(0.0, 0.0, 50.0)),
        _Row(desp=(100.0, 0.0, 50.0)),
        _Row(desp=(100.0, 0.0, 10.0)),
    ]
    emissions = {
        1: {"origin": (0.0, 0.0, 50.0), "direction": (1.0, 0.0, 0.0), "kind": "reflect"},
        2: {"origin": (100.0, 0.0, 50.0), "direction": (0.0, 0.0, -1.0), "kind": "reflect"},
    }
    tree = axis_tree.build_axis_tree(rows, fold_emissions=emissions)
    snaps = axis_tree.snap_rows(rows, tree)
    carried_by_bs = axis_tree.rows_on_emitted_leg(rows, tree, snaps, 1)
    check(
        2 in carried_by_bs and 3 in carried_by_bs,
        f"A1: sliding the BS carries the mirror AND the sensor beyond it ({carried_by_bs}) -- "
        f"a folder's leg includes the legs emitted further down the chain",
    )
    check(1 not in carried_by_bs, "A2: the folder itself is not in its own carry set")
    check(0 not in carried_by_bs, "A3: the Object row -- the station anchor -- is never carried")
    carried_by_mirror = axis_tree.rows_on_emitted_leg(rows, tree, snaps, 2)
    check(
        carried_by_mirror == [3],
        f"A4: sliding the mirror carries only what is on ITS leg ({carried_by_mirror}), "
        f"not the BS upstream of it",
    )
    check(
        axis_tree.rows_on_emitted_leg(rows, tree, snaps, 3) == [],
        "A5: a row that emits nothing carries nothing",
    )

    # --- B. both slide entry points are hooked --------------------------------------------
    # There are TWO implementations of this operation, each with its own copy of the BS<->LED
    # glue block, and the drag gizmo goes through the axis form -- a carry wired only into the
    # vector form never fires on a real drag. That is exactly what happened first.
    try:
        import inspect as _inspect

        from KrakenOS.UI.services.optical_solid_workflow import LayoutOpticalSolidWorkflowMixin
        from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

        axis_src = _inspect.getsource(LayoutOpticalSolidWorkflowMixin.translate_scene_row_pose)
        vector_src = _inspect.getsource(ScenePlacementMixin.translate_scene_row_pose_vector)
        for label, src in (("axis form", axis_src), ("vector form", vector_src)):
            check(
                "_fold_slide_carry_before" in src and "_fold_slide_carry_apply" in src,
                f"B[{label}]: the slide captures the carry set BEFORE moving and applies it after",
            )
    except Exception as exc:
        notes.append(f"SKIP: slide sources unreadable ({type(exc).__name__}: {exc})")

    # --- C. the real scene ------------------------------------------------------------------
    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes
    editor = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.nonseq_output_ports import axis_fold_emissions

        editor = KrakenLayoutEditor()
        editor.layout_files["fold_slide"] = SCENE
        editor.load_layout_by_name("fold_slide")
        editor.seat_camera_on_sensor()

        def state():
            found = axis_fold_emissions(editor.rows) or {}
            built = axis_tree.build_axis_tree(
                editor.rows,
                fold_emissions={
                    key: {"origin": v["origin"], "direction": v["direction"], "kind": "reflect"}
                    for key, v in found.items()
                },
            )
            by_row = {s.row_index: s for s in axis_tree.snap_rows(editor.rows, built)}
            body = None
            try:
                bounds = np.asarray(
                    editor._transformed_imported_step_mesh_for_label("camera").bounds, dtype=float
                ).reshape(6)
                body = np.asarray(
                    ((bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2)
                )
            except Exception:
                body = None
            return found, by_row, body

        before_folds, before_snaps, before_body = state()
        editor.translate_scene_row_pose(7, "x", -20.0)
        after_folds, after_snaps, after_body = state()

        fold_delta = np.asarray(after_folds[7]["origin"], dtype=float) - np.asarray(
            before_folds[7]["origin"], dtype=float
        )
        check(
            abs(float(fold_delta[0]) + 20.0) < 1e-6,
            f"C1: the slide moved the fold point ({np.round(fold_delta, 4).tolist()})",
        )
        sensor_before, sensor_after = before_snaps.get(8), after_snaps.get(8)
        check(
            sensor_after is not None and sensor_after.offset < 1e-3,
            f"C2: the sensor is still ON the emitted leg (transverse "
            f"{sensor_before.offset:.4f} -> {sensor_after.offset if sensor_after else float('nan'):.4f} mm) "
            f"-- it was left 20 mm off before this",
        )
        check(
            sensor_before is not None
            and sensor_after is not None
            and abs(sensor_after.s - sensor_before.s) < 1e-6,
            f"C3: its arc-length along the leg is UNCHANGED -- a rigid carry, not the leg-split "
            f"trade ({sensor_before.s:.4f} -> {sensor_after.s:.4f})",
        )
        if before_body is not None and after_body is not None:
            body_delta = after_body - before_body
            check(
                float(np.linalg.norm(body_delta - fold_delta)) < 1e-3,
                f"C4: the camera bolted to that arm moved with it "
                f"({np.round(body_delta, 4).tolist()} vs fold {np.round(fold_delta, 4).tolist()})",
            )
        else:
            notes.append("SKIP: no camera STEP body to check the body carry")
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({type(exc).__name__}: {exc})")
    finally:
        if editor is not None:
            try:
                editor.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
