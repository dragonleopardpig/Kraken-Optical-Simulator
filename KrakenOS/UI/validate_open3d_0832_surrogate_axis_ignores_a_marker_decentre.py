"""bugs/0832 guard -- a marker's decentre is not the lens's optical axis.

Two flags on 2026-09-20 (17:49 "lens and surogate not aligned", 17:51 "is the lens hit the
Edmund filter?") were ONE defect.  ``_lens_surrogate_optical_axis_line`` drew the chord
between the Front and Rear Optical Vertex Datum rows.  In a SEQUENTIAL scene ``desp_x/desp_y``
mean "how far this surface sits OFF the axis", so ``om05a_folded``'s front datum -- which
carries ``desp_x = -8.78`` while every other lens row including the Aperture Stop sits at 0,
and which is optically inert (``rc`` 0, AIR) -- tilted that chord 12.41 deg and put it 7.01 mm
off, on a scene whose rows are DRAWN exactly co-axial (pose_audit: rows 8-14 all at
y 56.36, z -25.00).

``center_lens_body_on_surrogate_axis`` runs on every lens SWAP and moves the CAD body onto
whatever that line says, so the live capture shows the damage: an applied placement offset of
(-6.2694, 0, 0.9938) whose own direction is atan(0.9938/6.2694) = 9.01 deg -- the tilt itself
-- leaving the barrel 6.27 mm off the drawn axis and its rear tip 0.31 mm inside the
Filter 48-926.

In a WORLD scene the opposite holds: the 0433 freeze bakes the folded leg INTO ``desp``, so
the chord is the only right answer, and ``machine_vision_ELS85``'s matched 55/-55 datums must
keep reading (1, 0, 0).  Hence the branch on the ONE placement resolver.

Checks:
  SOURCE  -- the branch and the median helper exist, and the reason is written down.
  SEQ     -- om05a_folded reads 0.0000 mm / 0.0000 deg, AND the old chord is shown to have
             read 7.01 mm / 12.41 deg, so a revert cannot pass.
  WORLD   -- machine_vision_ELS85 still reads (1, 0, 0): the fix is not "always use +z".
  DECENTRE-- a lens that really IS decentred (every span row sharing one offset) keeps it.
             The median is what distinguishes the two; a mean would split the difference and
             leave the body 4.39 mm off, which is the residual a direction-only repair leaves.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SEQ_SCENE = Path("attachment/om05a_folded.py")
WORLD_SCENE = Path("attachment/machine_vision_ELS85.py")

OLD_CHORD_OFFSET_MM = 7.0128
OLD_CHORD_TILT_DEG = 12.4076


def _load(scene: Path):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    app.layout_files["guard"] = scene
    app.load_layout_by_name("guard")
    return app


def _off_axis(app) -> "tuple[float, float] | None":
    """The very reading the swap acts on: body-vs-surrogate offset and tilt."""
    body = app._lens_step_overlay_axis_world_line()
    axis = app._lens_surrogate_optical_axis_line()
    if body is None or axis is None:
        return None
    gap = np.asarray(axis[0], dtype=float) - np.asarray(body[0], dtype=float)
    perp = gap - float(np.dot(gap, axis[1])) * np.asarray(axis[1], dtype=float)
    cosine = min(1.0, abs(float(np.dot(body[1], axis[1]))))
    return float(np.linalg.norm(perp)), float(np.degrees(np.arccos(cosine)))


def _chord(app) -> "tuple[float, float] | None":
    """What the PRE-0832 code returned: the raw datum-to-datum chord."""
    from KrakenOS.UI.services import scene_ir

    front = app._lens_datum_row_index("front")
    rear = app._lens_datum_row_index("rear")
    if front is None or rear is None:
        return None
    front_pose = np.asarray(scene_ir.world_frame(app, int(front))[0], dtype=float).reshape(3)
    rear_pose = np.asarray(scene_ir.world_frame(app, int(rear))[0], dtype=float).reshape(3)
    direction = rear_pose - front_pose
    length = float(np.linalg.norm(direction))
    if length <= 1.0e-9:
        return None
    point, direction = 0.5 * (front_pose + rear_pose), direction / length
    body = app._lens_step_overlay_axis_world_line()
    if body is None:
        return None
    gap = point - np.asarray(body[0], dtype=float)
    perp = gap - float(np.dot(gap, direction)) * direction
    cosine = min(1.0, abs(float(np.dot(body[1], direction))))
    return float(np.linalg.norm(perp)), float(np.degrees(np.arccos(cosine)))


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import layout_polyline_display as lpd

    src = _inspect.getsource(lpd._LayoutPolylineDisplayMixin) if hasattr(
        lpd, "_LayoutPolylineDisplayMixin"
    ) else _inspect.getsource(lpd)
    wanted = (
        "_sequential_surrogate_axis_point",
        "np.median",
        "how far this surface sits OFF the axis",
    )
    if all(token in src for token in wanted):
        notes.append("SOURCE = the space branch, the median helper and the reason are all present")
    else:
        missing = [t for t in wanted if t not in src]
        notes.append(f"SOURCE the axis derivation is missing {missing}")
        ok = False

    if not SEQ_SCENE.exists():
        notes.append("SKIP: om05a_folded is absent (gitignored attachment)")
        return ok, notes

    app = None
    try:
        app = _load(SEQ_SCENE)
        from KrakenOS.UI.services import row_placement as _rp

        front = app._lens_datum_row_index("front")
        rear = app._lens_datum_row_index("rear")
        decentre = float(getattr(app.rows[int(front)], "desp_x", 0.0))
        if abs(decentre) < 1.0:
            notes.append(
                f"SKIP: this om05a_folded no longer carries the marker decentre "
                f"(front datum desp_x = {decentre:.4f})"
            )
            return ok, notes

        old = _chord(app)
        if old is None:
            notes.append("SEQ the pre-0832 chord could not be measured (no lens body axis?)")
            ok = False
        elif old[0] > 1.0 and old[1] > 1.0:
            notes.append(
                f"SEQ = the OLD chord really was broken here: {old[0]:.4f} mm off, "
                f"{old[1]:.4f} deg tilt (recorded {OLD_CHORD_OFFSET_MM} / {OLD_CHORD_TILT_DEG})"
            )
        else:
            notes.append(
                f"SEQ the old chord reads {old[0]:.4f} mm / {old[1]:.4f} deg -- this scene no "
                "longer reproduces the defect, so the guard proves nothing"
            )
            ok = False

        line = app._lens_surrogate_optical_axis_line()
        if line is None:
            notes.append("SEQ the surrogate axis is now refused outright")
            ok = False
        else:
            direction = np.asarray(line[1], dtype=float)
            if abs(abs(float(direction[2])) - 1.0) <= 1.0e-9:
                notes.append("SEQ = the sequential axis runs along the chain (0, 0, +-1)")
            else:
                notes.append(f"SEQ the sequential axis direction is {np.round(direction, 5).tolist()}")
                ok = False

        now = _off_axis(app)
        if now is None:
            notes.append("SEQ the body-vs-axis reading is unavailable")
            ok = False
        elif now[0] <= 1.0e-6 and now[1] <= 1.0e-6:
            notes.append(
                f"SEQ = the swap now reads {now[0]:.4f} mm / {now[1]:.4f} deg, so it moves "
                "the CAD body by nothing -- the 6.27 mm sideways push is gone"
            )
        else:
            notes.append(f"SEQ the body still reads {now[0]:.4f} mm off / {now[1]:.4f} deg tilt")
            ok = False

        # A lens that really IS decentred must keep its decentre.
        lo, hi = sorted((int(front), int(rear)))
        saved = [float(getattr(app.rows[i], "desp_x", 0.0)) for i in range(lo, hi + 1)]
        try:
            for i in range(lo, hi + 1):
                app.rows[i].desp_x = 12.5
            shifted = app._lens_surrogate_optical_axis_line()
            if shifted is not None and abs(float(shifted[0][0]) - 12.5) <= 1.0e-6:
                notes.append(
                    "DECENTRE = a lens whose every span row shares 12.5 mm keeps its axis at "
                    "12.5 mm (the median follows a real decentre, it does not zero one)"
                )
            else:
                got = None if shifted is None else round(float(shifted[0][0]), 6)
                notes.append(f"DECENTRE a real 12.5 mm decentre was not preserved (axis x = {got})")
                ok = False
        finally:
            for offset, i in zip(saved, range(lo, hi + 1)):
                app.rows[i].desp_x = offset
    except Exception as exc:
        notes.append(f"SKIP: sequential scene drive failed ({exc!r})")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass

    if not WORLD_SCENE.exists():
        notes.append("SKIP: machine_vision_ELS85 is absent (gitignored attachment)")
        return ok, notes

    app = None
    try:
        app = _load(WORLD_SCENE)
        line = app._lens_surrogate_optical_axis_line()
        if line is None:
            notes.append("WORLD the frozen scene's surrogate axis was refused")
            ok = False
        else:
            direction = np.asarray(line[1], dtype=float)
            if abs(abs(float(direction[0])) - 1.0) <= 1.0e-6:
                notes.append(
                    "WORLD = the 0433-frozen chord still reads (1, 0, 0): a matched datum pair "
                    "IS the folded leg, and 0832 left it alone"
                )
            else:
                notes.append(f"WORLD the frozen axis direction changed to {np.round(direction, 5).tolist()}")
                ok = False
    except Exception as exc:
        notes.append(f"SKIP: world scene drive failed ({exc!r})")
    finally:
        if app is not None:
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
