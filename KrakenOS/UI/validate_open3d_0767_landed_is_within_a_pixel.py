"""Guard for bugs/0767 -- "land it" is a question about the PIXEL, not about millimetres.

Flag `20260910_091428_853` ("30x30x1mm device focus correctly") confirmed the bugs/0764 fix in
the app: the image formed 0.05058 mm off the sensor with a 1.51 um spot there, against a 4.5 um
pixel. The banner nonetheless ended with *"Move the device stage / camera focus to land it"* --
telling the user to adjust hardware that was already right, because the gate was a hardcoded
``abs(offset) >= 0.05`` mm and that residual cleared it by 0.6 um.

A residual in millimetres is not a defect on its own. What matters is whether it costs sharpness
the detector can actually see: a blur inside one pixel IS landed, because no sampling of that
image can tell it from a perfect one.

Checks (display-free, pure):
  A  a sub-pixel blur reports "Landed ... nothing to move", and never the move instruction;
  B  a real miss still asks for the move (the guard must not silence genuine defects);
  C  with no pixel size known the old behaviour is kept -- an unknown pixel is not a licence
     to declare success;
  D  the inspector passes the pixel size from the SAME camera record the system HUD prints,
     so the banner and the HUD can never disagree about how big a pixel is.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0767_landed_is_within_a_pixel
"""

from __future__ import annotations

import inspect


_SOLVE = {"delivered_fov_wh": (31.5, 31.5), "delivered_m": 0.7314}
#: the flagged state, verbatim: 0.05058 mm off, 1.51 um on a 4.5 um pixel
_LANDED = {"offset_mm": -0.05058, "side": "in front of",
           "rms_waist_mm": 0.000224, "rms_plane_mm": 0.00151}
#: the bugs/0764 defect for comparison: 5.932 mm off, 175 um on the sensor
_MISS = {"offset_mm": -5.932, "side": "in front of",
         "rms_waist_mm": 0.000224, "rms_plane_mm": 0.175}


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import format_focus_summary_lines

    # ---- A: a sub-pixel blur is landed ------------------------------------------------------
    landed = format_focus_summary_lines(_LANDED, _SOLVE, pixel_size_um=(4.5, 4.5))
    joined = "\n".join(landed)
    ok(
        "Landed" in joined and "nothing to move" in joined,
        f"A1: a 1.51 um blur on a 4.5 um pixel reports LANDED (got {landed[-1]!r})",
    )
    ok(
        "Move the device stage" not in joined,
        "A2: and never also asks the user to move hardware that is already right",
    )
    ok(
        any("0.05058 mm" in line for line in landed),
        "A3: the measured offset is still reported -- landing is not a reason to hide where "
        "the image forms",
    )

    # ---- B: a real miss still asks for the move ---------------------------------------------
    miss = "\n".join(format_focus_summary_lines(_MISS, _SOLVE, pixel_size_um=(4.5, 4.5)))
    ok(
        "Move the device stage" in miss and "Landed" not in miss,
        "B1: a 175 um blur (the bugs/0764 defect) still asks for the move -- the guard must "
        "not silence a genuine miss",
    )

    # a blur exactly AT the pixel is landed; one just over it is not
    edge = "\n".join(format_focus_summary_lines(
        dict(_LANDED, rms_plane_mm=0.0045), _SOLVE, pixel_size_um=(4.5, 4.5)))
    over = "\n".join(format_focus_summary_lines(
        dict(_LANDED, rms_plane_mm=0.0046), _SOLVE, pixel_size_um=(4.5, 4.5)))
    ok("Landed" in edge, "B2: a blur exactly one pixel wide counts as landed")
    ok("Move the device stage" in over, "B3: a blur wider than a pixel does not")

    # a non-square pixel is judged by its SMALLER side (the finer sampling direction)
    rect = "\n".join(format_focus_summary_lines(
        dict(_LANDED, rms_plane_mm=0.0040), _SOLVE, pixel_size_um=(4.5, 2.5)))
    ok(
        "Move the device stage" in rect,
        "B4: a rectangular pixel is judged by its SMALLER side -- a 4.0 um blur is resolved "
        "by a 2.5 um pitch even though it fits the 4.5 um one",
    )

    # ---- C: unknown pixel keeps the old behaviour -------------------------------------------
    for label, kwargs in (
        ("None", {"pixel_size_um": None}),
        ("empty", {"pixel_size_um": ()}),
        ("zero", {"pixel_size_um": (0.0, 0.0)}),
        ("junk", {"pixel_size_um": ("x", "y")}),
    ):
        text = "\n".join(format_focus_summary_lines(_LANDED, _SOLVE, **kwargs))
        ok(
            "Move the device stage" in text and "Landed" not in text,
            f"C1[{label}]: with no usable pixel size the old instruction stands -- an unknown "
            f"pixel is not a licence to declare success",
        )
    ok(
        not format_focus_summary_lines(None, None, pixel_size_um=(4.5, 4.5)),
        "C2: nothing measured -> no lines at all (the bugs/0728 contract is unchanged)",
    )

    # ---- D: the pixel comes from the HUD's own source ----------------------------------------
    from KrakenOS.UI import open3d_inspector
    from KrakenOS.UI.services import system_info_hud

    inspector_src = inspect.getsource(open3d_inspector)
    ok(
        "pixel_size_um=self._flag_camera_pixel_size_um()" in inspector_src,
        "D1: the focus banner is given the pixel size (it cannot judge landing without it)",
    )
    helper_src = inspect.getsource(open3d_inspector.Kraken3DInspector._flag_camera_pixel_size_um)
    hud_src = inspect.getsource(system_info_hud)
    ok(
        "_current_camera_record()" in helper_src
        and "pixel_size_um" in helper_src
        and "_current_camera_record()" in hud_src,
        "D2: from the SAME camera record the system HUD prints -- two sources could disagree "
        "about how big a pixel is, and the user reads both in one frame",
    )

    class _Boom:
        def _current_camera_record(self):
            raise RuntimeError("no camera")

    class _Host:
        editor = _Boom()
        _flag_camera_pixel_size_um = open3d_inspector.Kraken3DInspector.__dict__[
            "_flag_camera_pixel_size_um"
        ]

    ok(
        _Host()._flag_camera_pixel_size_um() is None,
        "D3: a scene with no camera record yields None rather than raising into the banner",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0767 landed-is-within-a-pixel validation PASSED")
        return 0
    print("0767 landed-is-within-a-pixel validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
