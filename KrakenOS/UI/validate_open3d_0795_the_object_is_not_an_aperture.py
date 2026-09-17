"""bugs/0795 -- the object is not an aperture.

flag_20260916_113737, "why the rays look so wierd, sudden bend on last two surrogate and single
pencils rays reaching the sensor, not the focusing rays type": the SPO TCL4.0X-65DI-5M scene
launched 0.330 mm of beam through a lens with a 26.076 mm front aperture and a 15.076 mm stop.

``_resolved_preview_pupil_radius`` sized that launch from two numbers that measure the wrong
thing. ``_entrance_radius`` clamps to the OBJECT's semi-diameter -- a FIELD extent, which says
how wide the object is and never what angle the lens accepts -- and at 1x and below the object
is the larger of the two, so the clamp never bound until a 4x lens imaged a 2.75 mm object
through 26 mm of glass. Behind it, ``PupilCalc`` cannot solve an object-space telecentric at all
(its entrance-pupil Newton step divides by zero, because the chief ray is parallel to the axis
for EVERY object height), so the fallback was half the stop diameter used as an aim radius at the
first surface, 132 mm and two groups upstream.

The fix measures instead of assuming: one probe ray from the axial object point, its height read
at the stop row, scaled. The pupil is a paraxial construction, so one probe fixes the cone.

Display-free: synthetic layouts in a temp dir, no repo writes, no rendering, no vendor CAD for
the physics claims.
"""

from __future__ import annotations

import contextlib
import io
import pprint
import tempfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# The 4x conjugate-constrained surrogate of bugs/0792: object 65 mm, groups f1 +47.112667 and
# f2 -23.882528 at 132.5 mm, stop 15.0761 at group 1's back focal plane, image at the flange.
_MAGNIFYING = [
    ("Object", "Object", 0.0, 65.0, 2.75),
    ("Standard", "Front Optical Vertex Datum", 0.0, 5.0, 26.0761),
    ("Thin Lens", "Blackbox Group 1", 47.112667, 47.112667, 26.0761),
    ("Aperture", "Aperture Stop", 0.0, 85.387333, 15.0761),
    ("Thin Lens", "Blackbox Group 2", -23.882528, 5.0, 26.0761),
    ("Standard", "Rear Optical Vertex Datum", 0.0, 17.526, 26.0761),
    ("Image", "Image / Sensor", 0.0, 0.0, 11.0),
]

STOP_SEMI_DIAMETER = 15.0761 / 2.0        # 7.53805 -- at the STOP plane
FRONT_CLEAR_SEMI = 26.0761 / 2.0          # 13.03805 -- the physical front aperture
OBJECT_SEMI = 2.75 / 2.0                  # 1.375 -- what the launch was clamped to
EXPECTED_STOP_FILL = 10.4                 # measured, and = 0.16 x 65
EXPECTED_OBJECT_NA = 4.0 / (2.0 * 12.5)   # m / (2 N_working) = 0.16


def _layout_source(rows, *, aperture_type: str, aperture_value: str,
                   object_mode: str = "Finite") -> str:
    settings = {
        "aperture_type": aperture_type,
        "aperture_value": aperture_value,
        "display_orientation": "YZ",
        "field_count": 3,
        "field_type": "Real Image Height",
        "field_value": 5.5,
        "object_mode": object_mode,
        "projection_display_mode": "Full 3D",
        "wavelength": 0.55,
    }
    surfaces = [
        {"surface": s, "name": n, "rc": rc, "thickness": t, "diameter": d, "glass": "AIR"}
        for s, n, rc, t, d in rows
    ]
    return (
        '"""bugs/0795 synthetic probe layout."""\n\n'
        "TITLE = 'bugs 0795 probe'\n\n"
        f"SETTINGS = {pprint.pformat(settings)}\n\n"
        f"SURFACES = {pprint.pformat(surfaces)}\n"
    )


def _editor_for(tmpdir: Path, name: str, source: str):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    path = tmpdir / name
    path.write_text(source, encoding="utf-8")
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["probe"] = path.resolve()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        editor.load_layout_by_name("probe")
        editor._preview_trace_deferred_until_requested = False
    return editor


def _pre_0795_resolved(editor, system, fallback: float = 12.0) -> float:
    """The resolution this bug replaced, recomputed from the same inputs."""
    import KrakenOS as Kos

    radius = max(float(editor._entrance_radius(fallback)), 1e-6)
    aperture_value = abs(float(editor._current_aperture_value()))
    aperture_radius = aperture_value * 0.5 if aperture_value > 1e-9 else None
    try:
        psys, _rows, pidx = editor._pupil_model_inputs(system, build_reference=True)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            pupil = Kos.PupilCalc(psys, pidx, editor._current_wavelength(),
                                  editor._current_aperture_type(),
                                  editor._current_aperture_value())
        value = float(getattr(pupil, "RadPupInp", 0.0))
        if np.isfinite(value) and value > 1e-9:
            aperture_radius = value
    except Exception:
        pass
    if aperture_radius is None or not np.isfinite(aperture_radius) or aperture_radius <= 1e-9:
        return radius
    return max(min(radius, float(aperture_radius)), 1e-6)


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    with tempfile.TemporaryDirectory(prefix="kraken0795_") as tmp:
        tmpdir = Path(tmp)

        # ---- the magnifying scene: object SMALLER than the cone the lens accepts -----------
        editor = _editor_for(
            tmpdir, "probe_magnifying.py",
            _layout_source(_MAGNIFYING, aperture_type="STOP", aperture_value="15.0761"),
        )
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                system, _rays, _bundle = editor._build_preview_system_rays_bundle(trace_rays=False)

            # ---- A: the historical clamp, still object-driven, is what we are raising ------
            entrance = float(editor._entrance_radius(12.0))
            clear = float(editor._first_optical_clear_radius())
            ok(abs(entrance - OBJECT_SEMI) < 1e-9,
               f"A: _entrance_radius still returns the OBJECT semi-diameter ({entrance:.4f}), "
               f"not the {clear:.4f} mm the front aperture actually passes")
            ok(clear > entrance * 9.0,
               f"A: a 4x lens's front aperture is {clear / entrance:.2f}x its own object -- "
               "the first scene in the corpus where the clamp binds")

            # ---- B: the measured stop-filling cone -----------------------------------------
            stop_fill = editor._stop_filling_launch_radius(system)
            ok(stop_fill is not None and abs(float(stop_fill) - EXPECTED_STOP_FILL) < 1e-3,
               f"B: the measured stop-filling aim radius is {stop_fill} mm (expected "
               f"{EXPECTED_STOP_FILL})")
            if stop_fill is not None:
                na = float(stop_fill) / 65.0
                ok(abs(na - EXPECTED_OBJECT_NA) < 1e-4,
                   f"B: which is object NA {na:.5f} = m/(2 N_working) = 4/(2x12.5) = "
                   f"{EXPECTED_OBJECT_NA:.5f} -- the datasheet's own working f-number, "
                   "recovered from the geometry")

            # ---- C: the resolution the bundles actually get --------------------------------
            resolved = float(editor._resolved_preview_pupil_radius(12.0, system=system))
            before = _pre_0795_resolved(editor, system)
            ok(abs(before - OBJECT_SEMI) < 1e-6,
               f"C: before this fix the launch resolved to {before:.4f} mm -- the object "
               "semi-diameter, the flag's pencil")
            ok(resolved > EXPECTED_STOP_FILL - 1e-2,
               f"C: it now resolves to {resolved:.4f} mm, the measured cone")
            ok(resolved <= clear + 1e-9,
               f"C: and never past the physical front clear radius ({clear:.4f})")
            ok(abs(resolved - STOP_SEMI_DIAMETER) > 1.0,
               f"C: nor is it half the stop diameter ({STOP_SEMI_DIAMETER:.4f}) -- that is a "
               "radius AT THE STOP, two groups and 132 mm from the plane the bundles aim at")

            # ---- D: PupilCalc cannot serve an object-space telecentric ---------------------
            import KrakenOS as Kos

            raised = None
            try:
                psys, _rows, pidx = editor._pupil_model_inputs(system, build_reference=True)
                with contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    Kos.PupilCalc(psys, pidx, editor._current_wavelength(),
                                  editor._current_aperture_type(),
                                  editor._current_aperture_value())
            except Exception as exc:
                raised = f"{type(exc).__name__}: {exc}"
            ok(raised is not None,
               "D: PupilCalc raises on an object-space telecentric -- its entrance-pupil solve "
               "Newton-steps on a derivative that is identically zero, because the chief ray is "
               f"parallel to the axis for every object height ({raised})")

            # ---- E: the cone reaches the sensor as a cone ----------------------------------
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                _s, _r, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
                info = editor._measure_focused_image_plane(bundle)
            paths = [
                np.asarray(p.points_world, float)
                for p in (getattr(bundle, "ray_paths", []) or [])
                if str(getattr(p, "termination_reason", "")) in ("image", "target_termination")
            ]
            axial = [q for q in paths if np.hypot(q[0][0], q[0][1]) < 0.01 and len(q) >= 4]
            ok(len(axial) >= 8, f"E: {len(axial)} axial rays reach the image")
            if axial:
                at_front = max(float(np.hypot(q[1][0], q[1][1])) for q in axial)
                at_stop = max(float(np.hypot(q[3][0], q[3][1])) for q in axial)
                ok(at_front > 8.0,
                   f"E: the axial bundle is {at_front:.3f} mm across at the front datum "
                   "(the flag traced 0.330)")
                ok(at_stop > 0.7 * STOP_SEMI_DIAMETER,
                   f"E: and fills {at_stop / STOP_SEMI_DIAMETER:.0%} of the stop "
                   f"({at_stop:.3f} of {STOP_SEMI_DIAMETER:.3f} mm) -- it passed 4% before")
            offset = float(info.get("offset_mm") or 0.0)
            ok(abs(offset) < 1e-3,
               f"E: and the conjugate is untouched -- {offset:.2e} mm of defocus. This bug "
               "fills the cone; it does not move the focus")
        finally:
            with contextlib.suppress(Exception):
                editor.destroy()

        # ---- F: a scene whose object is WIDER keeps its launch to the byte -----------------
        wide = [("Object", "Object", 0.0, 65.0, 40.0)] + _MAGNIFYING[1:]
        editor = _editor_for(
            tmpdir, "probe_wide_object.py",
            _layout_source(wide, aperture_type="EPD", aperture_value="18.0"),
        )
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                system, _rays, _bundle = editor._build_preview_system_rays_bundle(trace_rays=False)
            before = _pre_0795_resolved(editor, system)
            after = float(editor._resolved_preview_pupil_radius(12.0, system=system))
            ok(abs(after - before) < 1e-9,
               f"F: an object wider than the front aperture resolves to {after:.6f} mm before "
               "and after -- the clamp is only ever RAISED, never lowered")
        finally:
            with contextlib.suppress(Exception):
                editor.destroy()

        # ---- G: an infinite object has no aim plane to scale against -----------------------
        editor = _editor_for(
            tmpdir, "probe_infinity.py",
            _layout_source(_MAGNIFYING, aperture_type="EPD", aperture_value="18.0",
                           object_mode="Infinity"),
        )
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                system, _rays, _bundle = editor._build_preview_system_rays_bundle(trace_rays=False)
            ok(editor._stop_filling_launch_radius(system) is None,
               "G: an Infinity object measures nothing -- its launch grid IS the pupil, there is "
               "no aim plane to scale a cone against")
        finally:
            with contextlib.suppress(Exception):
                editor.destroy()

    # ---- H: the importer declares the aperture this lens HAS -------------------------------
    spo = PROJECT_ROOT / "attachment/Information/RD-80000/Drawings/SPO TCL4.0X-65DI-5M"
    if spo.is_dir():
        from KrakenOS.UI.services import machine_vision_folder_import as mvi

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            model = mvi.import_lens_folder(spo)
        ok(str(model.aperture_type).upper() == "STOP",
           f"H: a conjugate-constrained build declares STOP, not FNO (got {model.aperture_type})")
        # bugs/0807: the SPO drawing pins the stop at its iris, which changes the solved groups and
        # with them the stop (15.0761 at the rim placement, 11.974 at the iris) -- so check the
        # declaration against the importer's OWN solve: NA 0.16 through group 1's focal length.
        solved_stop = 2.0 * float(model.solution.f1) * 4.0 / (2.0 * 12.5)
        ok(abs(float(model.aperture_value) - solved_stop) < 1e-3,
           f"H: with the solved stop diameter ({model.aperture_value}, the solve gives {solved_stop:.4f})")
        # bugs/0792: this build's EFL is an EQUIVALENT number with no infinite-conjugate
        # meaning, so an f-number taken against it means nothing either.
        fno_pupil = float(model.effl) / 12.5
        # (18x under at the rim placement; bugs/0807's iris placement raises the equivalent EFL to
        # 23.8 mm and it is still 6x under -- the point is that the f-number route misdeclares it)
        ok(float(model.aperture_value) / fno_pupil > 3.0,
           f"H: FNO 12.5 against its equivalent EFL {model.effl:.4f} would declare a "
           f"{fno_pupil:.3f} mm pupil -- {float(model.aperture_value) / fno_pupil:.0f}x smaller "
           "than the aperture the lens has")
    else:
        notes.append("SKIP: H: the SPO folder is not in this checkout")

    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0795 object-is-not-an-aperture validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
