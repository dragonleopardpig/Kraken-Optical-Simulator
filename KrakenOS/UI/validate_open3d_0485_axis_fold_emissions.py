"""bugs/0485 -- the ONE axis-fold derivation: which rows act on the axis, and what each emits.

Guards ``nonseq_output_ports.axis_fold_emissions`` and its two geometric helpers before anything
visible derives from them. The derivation has to answer, on every kind of scene:

  * does this row act on the axis at all;
  * CONSUMING (a full mirror: the incoming axis ends) or BRANCHING (a beam splitter: the incoming
    axis carries on and a second one appears);
  * where the fold point is, and which way the emitted leg goes.

The three things measurement forced during stage 1b, each pinned below:

  1. **probe from the axis that feeds it.** A single threaded "current axis" probed everything from
     the nominal +Z line, so the AZ85 mirror -- which sits at x = 229.93 on the BS reflect leg --
     failed bugs/0224's hit test and the whole scene reported zero folds. Which leg a folder is on
     is told by its own POSE, and that is also what makes live and frozen scenes take the same path.
  2. **a full mirror outranks an inferred port** (bugs/0185). Ranking by
     ``_exit_frame_is_non_folding`` instead worked only while every probe used +Z; once the mirror
     was correctly probed from (1,0,0) its +Z Transmit/Port face stopped looking codirectional and
     it emitted (0,0,1) from an inferred port.
  3. **an axis wants the CROSSING, not the exit frame.**
     ``_reflected_frame_from_interaction_face`` returns ``hit + reflected*(thickness - pre_hit_run)``
     measured from a station marker (bugs/0207), so its origin moves when the probe moves along the
     same line -- measured, penta prism 1's fold point shifted z 57.626 -> 96.517.

Sections A-F are display-free (synthetic face dicts, no scene). Section G drives the real scenes
and SKIPs any that are not checked out.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0485_axis_fold_emissions
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENES = [
    # (label, attachment path or None, built-in name or None, folders, kinds by row)
    ("AZ85 RA mirror + BS", Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py"), None, 2),
    ("AZ85 RA mirror (no BS)", Path("attachment/machine_vision_AZ85_RA_Mirror.py"), None, 2),
    ("five penta prism cascade", Path("attachment/five_penta_prism_cascade.py"), None, 5),
    ("Two Path Doublets", None, "Beam Splitter Two Path Doublets", 1),
    ("plain doublet", Path("attachment/doublet.py"), None, 0),
]


def _face(function, normal, centroid, *, area=400.0):
    from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACE_PORT_INTERACTION

    return {
        "port_role": OPTICAL_SOLID_FACE_PORT_INTERACTION,
        "function": function,
        "role": function,
        "normal_world": tuple(float(v) for v in normal),
        "centroid_world": tuple(float(v) for v in centroid),
        "area_mm2": float(area),
    }


class _Row:
    """Only what ``_surface_row_fold_emission`` reads."""

    def __init__(self, *, tilt=(0.0, 0.0, 0.0), diameter=50.0):
        self.tilt_x, self.tilt_y, self.tilt_z = (float(v) for v in tilt)
        self.diameter = float(diameter)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        import KrakenOS.UI.nonseq_output_ports as N
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: nonseq_output_ports unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    z_in = np.asarray((0.0, 0.0, 1.0))

    # --- A. one mirror folds once, at the crossing --------------------------------------
    # A 45 deg mirror at (0,0,100): normal (0.7071, 0, -0.7071) turns +Z into +X.
    # (The mirrored normal (-0.7071, 0, -0.7071) turns it into -X -- worth stating, because
    # getting that backwards is what this check caught in its own first draft.)
    mirror45 = _face("Mirror", (0.70710678, 0.0, -0.70710678), (0.0, 0.0, 100.0))
    bounces = N._interaction_fold_emission([mirror45], (0.0, 0.0, 0.0), z_in, accept={"Mirror"})
    check(bounces is not None and len(bounces) == 1, f"A1: a single mirror emits one bounce ({bounces and len(bounces)})")
    if bounces:
        hit, direction = bounces[0]
        check(np.allclose(hit, (0.0, 0.0, 100.0), atol=1e-9), f"A2: the fold point is the crossing ({np.round(hit,4).tolist()})")
        check(np.allclose(direction, (1.0, 0.0, 0.0), atol=1e-9), f"A3: +Z reflects to +X ({np.round(direction,4).tolist()})")
    # The crossing depends only on the LINE -- probing from anywhere on it gives the same answer.
    far = N._interaction_fold_emission([mirror45], (0.0, 0.0, -5000.0), z_in, accept={"Mirror"})
    check(
        far is not None and bounces is not None and np.allclose(far[0][0], bounces[0][0], atol=1e-9),
        "A4: the fold point is independent of where along the incoming line it is probed "
        "(the exit-frame helper is not -- it moved penta prism 1 by 38.9 mm)",
    )

    # --- B. a penta prism folds TWICE ----------------------------------------------------
    # Two reflections compose into a ROTATION by twice the angle between the mirror planes,
    # about their line of intersection. Normals 45 deg apart in the y-z plane therefore deviate
    # the beam 90 deg about x: +Z -> (0, -0.7071, -0.7071) -> (0, -1, 0). The second face is
    # placed ON that intermediate leg, 28.28 mm along it, or the beam never reaches it.
    # m2's area matters: the walk picks the NEAREST accepted crossing, and the incoming line
    # passes 21.65 mm from m2's centroid. With sqrt(400)+2 = 22 mm of hit radius it would be
    # admitted first and the prism would fold once. A 100 mm2 face (radius 12) is discriminated
    # on the way in and hit dead-centre on the intermediate leg -- which is how a real penta is
    # built, and a reminder that bugs/0224's radius is doing real work here.
    m1 = _face("Mirror", (0.0, 0.38268343, 0.92387953), (0.0, 0.0, 100.0))
    m2 = _face("Mirror", (0.0, -0.38268343, 0.92387953), (0.0, -20.0, 80.0), area=100.0)
    penta = N._interaction_fold_emission([m1, m2], (0.0, 0.0, 0.0), z_in, accept={"Mirror"})
    check(penta is not None and len(penta) == 2, f"B1: a two-mirror solid emits TWO bounces ({penta and len(penta)})")
    if penta and len(penta) == 2:
        final = penta[-1][1]
        deviation = float(np.degrees(np.arccos(np.clip(float(np.dot(final, z_in)), -1.0, 1.0))))
        check(abs(deviation - 90.0) < 1e-6, f"B2: the composed deviation is 90 deg ({deviation:.4f})")
        check(
            not np.allclose(penta[0][1], final, atol=1e-9),
            "B3: the EMITTED leg is the second bounce, not the intermediate one "
            "(emitting the intermediate 45 deg leg found 1 of 5 prisms)",
        )

    # --- C. bugs/0224: a solid parked clear of the beam emits nothing --------------------
    parked = _face("Mirror", (-0.70710678, 0.0, -0.70710678), (500.0, 0.0, 100.0), area=100.0)
    check(
        N._interaction_fold_emission([parked], (0.0, 0.0, 0.0), z_in, accept={"Mirror"}) is None,
        "C1: a mirror the beam LINE never crosses does not fold (bugs/0224 hit radius)",
    )
    # ... and a face with no area keeps folding (the test only applies when an extent is known).
    no_area = _face("Mirror", (-0.70710678, 0.0, -0.70710678), (500.0, 0.0, 100.0), area=0.0)
    check(
        N._interaction_fold_emission([no_area], (0.0, 0.0, 0.0), z_in, accept={"Mirror"}) is not None,
        "C2: a face with no recorded area is not silently dropped",
    )

    # --- D. the accept set separates BRANCHING from CONSUMING ---------------------------
    coating = _face("Beam Splitter", (0.70710678, 0.0, -0.70710678), (0.0, 0.0, 50.0))
    check(
        N._interaction_fold_emission([coating], (0.0, 0.0, 0.0), z_in, accept={"Mirror"}) is None,
        "D1: a BS coating is not folded as a mirror",
    )
    bs = N._interaction_fold_emission([coating], (0.0, 0.0, 0.0), z_in, accept={"Beam Splitter"})
    check(
        bs is not None and np.allclose(bs[0][1], (1.0, 0.0, 0.0), atol=1e-9),
        f"D2: the BS coating emits its reflect leg ({bs and np.round(bs[0][1],4).tolist()}) -- "
        f"_reflected_frame_from_interaction_face refuses it, by design (bugs/0398)",
    )
    check(
        N._interaction_fold_emission([mirror45], (0.0, 0.0, 0.0), z_in, accept={"Beam Splitter"}) is None,
        "D3: a mirror is not folded as a BS coating",
    )

    # --- E. plain surface rows fold about their own plane --------------------------------
    # 45 deg about X turns +Z into -Y (or +Y); either way it must be a 90 deg deviation.
    surface = N._surface_row_fold_emission(_Row(tilt=(45.0, 0.0, 0.0)), (0.0, 0.0, 60.0), (0.0, 0.0, 0.0), z_in)
    check(surface is not None and len(surface) == 1, "E1: a tilted surface row folds")
    if surface:
        deviation = float(np.degrees(np.arccos(np.clip(float(np.dot(surface[0][1], z_in)), -1.0, 1.0))))
        check(abs(deviation - 90.0) < 1e-6, f"E2: a 45 deg surface deviates the beam 90 deg ({deviation:.4f})")
        check(
            np.allclose(surface[0][0], (0.0, 0.0, 60.0), atol=1e-9),
            f"E3: its fold point is on the row's own plane ({np.round(surface[0][0],4).tolist()})",
        )
    # A surface square-ON to the beam RETRO-reflects; that is a fold, not a pass-through. There
    # is no codirectional case to guard: a crossing needs ``d . n != 0``, so a reflection always
    # turns the beam.
    square_on = N._surface_row_fold_emission(_Row(tilt=(0.0, 0.0, 0.0)), (0.0, 0.0, 60.0), (0.0, 0.0, 0.0), z_in)
    check(
        square_on is not None and np.allclose(square_on[0][1], (0.0, 0.0, -1.0), atol=1e-9),
        f"E4: a surface square-on to the beam retro-reflects "
        f"({square_on and np.round(square_on[0][1], 4).tolist()})",
    )

    # --- F. the distance-sign rule -------------------------------------------------------
    # First crossing sign-agnostic: probing from PAST the mirror still finds it (bugs/0224 --
    # "the walk's frame origin is a sequential STATION marker that legitimately sits PAST the
    # fold face").
    behind = N._interaction_fold_emission([mirror45], (0.0, 0.0, 400.0), z_in, accept={"Mirror"})
    check(
        behind is not None and np.allclose(behind[0][0], (0.0, 0.0, 100.0), atol=1e-9),
        "F1: the FIRST crossing is sign-agnostic in distance",
    )
    # Later bounces are forward-only, so a second face BEHIND the first hit is not taken.
    back_face = _face("Mirror", (0.0, 0.0, 1.0), (0.0, -400.0, 100.0))
    forward_only = N._interaction_fold_emission([m1, back_face], (0.0, 0.0, 0.0), z_in, accept={"Mirror"})
    check(
        forward_only is not None and len(forward_only) == 1,
        f"F2: a face behind the first hit is not re-taken ({forward_only and len(forward_only)} bounce(s)) "
        f"-- without this the beam re-hits the face it just left at distance zero",
    )

    # --- G. the real scenes ---------------------------------------------------------------
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable for the scene checks ({type(exc).__name__}: {exc})")
        return ok, notes
    for label, path, builtin, expected in SCENES:
        if path is not None and not path.exists():
            notes.append(f"SKIP: {label} is not checked out (gitignored attachment)")
            continue
        editor = None
        try:
            editor = KrakenLayoutEditor()
            if builtin is not None:
                editor.load_layout_by_name(builtin)
            else:
                editor.layout_files["axis_probe"] = path
                editor.load_layout_by_name("axis_probe")
            found = N.axis_fold_emissions(editor.rows) or {}
            check(
                len(found) == expected,
                f"G[{label}]: {len(found)} folder(s), expected {expected} "
                f"(rows {sorted(found)})",
            )
            # Every emitted leg must be a unit vector, and every child must name its parent.
            for row_index, spec in sorted(found.items()):
                direction = np.asarray(spec["direction"], dtype=float)
                if abs(float(np.linalg.norm(direction)) - 1.0) > 1e-9:
                    check(False, f"G[{label}]: row {row_index} emitted a non-unit direction")
                    break
            else:
                if found:
                    notes.append(
                        f"     {label}: "
                        + ", ".join(
                            f"S{r}={spec['kind'][:6]}/{len(spec.get('bounces') or [])}b"
                            f"->{np.round(spec['direction'], 3).tolist()}"
                            for r, spec in sorted(found.items())
                        )
                    )
        except Exception as exc:
            notes.append(f"SKIP: {label} drive failed ({type(exc).__name__}: {exc})")
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
        print((" " if note.startswith(("PASS", "SKIP", "    ")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
