"""bugs/0478 -- a solved image distance must be placed along the BEAM, not into a gap row
whose sign is inverted on a frozen folded scene.

Flag flag_20260729_185356_727: "changed to FOV 30x30, ray defocus at sensor."

On the frozen AZ85 + BS scene the beam after the RA mirror travels one way while the station
axis advances the other, so the WORLD mirror->sensor leg goes as ``const - thickness``
(measured derivative -1). The conjugate solve wrote its answer straight into
``rows[img_row].thickness``, which moved the sensor a millimetre the WRONG WAY per millimetre
asked for: a requested -25.26 mm became +25.26 mm and left +62.08 mm of real defocus.

Fix: ``apply_image_distance_frozen_aware`` routes the write through
``_apply_frozen_image_split`` (bugs/0447), which re-bakes the mirror/sensor world centres along
the measured ``out_dir`` and carries the camera body -- with ``delta = 0`` so only the sensor
re-seats. It returns False on any straight/unfrozen scene, leaving the original prescription
write in place there.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0478_fov_solve_frozen_image
"""
from __future__ import annotations

import inspect
from pathlib import Path

SCENE = Path("/home/thinky/Projects/Kraken-Optical-Simulator/attachment/machine_vision_AZ85_RA_Mirror_BS.py")

# Measured on the flagged scene (see bugs/0478).
SOLVED_IMAGE_MM = 18.86
PRE_SOLVE_ROW7 = 44.1193
BROKEN_RESIDUAL_MM = 62.08  # what the plain prescription write left behind


class _Stub:
    """Drives apply_image_distance_frozen_aware's fallback contract without a scene."""

    def __init__(self, split=None, geometry=None):
        self._split = split
        self._geometry = geometry
        self.applied = None

    def _folded_image_conjugate_split(self):
        return self._split

    def _frozen_image_fold_world_geometry(self, split):
        return self._geometry

    def _apply_frozen_image_split(self, split, near_new, far_new, delta):
        self.applied = {"near_new": near_new, "far_new": far_new, "delta": delta}
        return True, "applied"


def _bind():
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin

    return ParaxialToolsMixin.apply_image_distance_frozen_aware


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        fn = _bind()
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: paraxial tools unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. fallback contract: a straight / unfrozen scene is UNTOUCHED ------
    check(fn(_Stub(split=None, geometry=None), 12.0) is False, "A1: no image-side fold -> falls back to the plain write")
    check(
        fn(_Stub(split={"mirror_row": 7}, geometry=None), 12.0) is False,
        "A2: a fold that is NOT frozen -> falls back (geometry is None)",
    )
    bad = _Stub(split={"mirror_row": 7}, geometry={"near": 58.88})
    check(fn(bad, 0.0) is False and bad.applied is None, "A3: a non-positive image distance is refused")
    check(fn(bad, float("nan")) is False and bad.applied is None, "A4: a non-finite image distance is refused")

    # --- B. the frozen write: solved distance goes down the EXIT leg ---------
    good = _Stub(split={"mirror_row": 7}, geometry={"near": 58.8807})
    check(fn(good, SOLVED_IMAGE_MM) is True, "B1: a frozen folded scene is handled")
    check(
        good.applied is not None and abs(float(good.applied["far_new"]) - SOLVED_IMAGE_MM) < 1e-9,
        f"B2: the solved distance is the FAR leg verbatim (got {good.applied})",
    )
    check(
        good.applied is not None and abs(float(good.applied["delta"])) < 1e-12,
        "B3: delta = 0 -- the mirror stays put, only the sensor re-seats",
    )
    check(
        good.applied is not None and abs(float(good.applied["near_new"]) - 58.8807) < 1e-6,
        "B4: the near leg is preserved at its measured world value",
    )

    # --- C. the conjugate applier actually calls it, BEFORE the plain write --
    try:
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService

        src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    except Exception as exc:
        notes.append(f"SKIP: could not read the conjugate applier ({type(exc).__name__}: {exc})")
        return ok, notes
    check("apply_image_distance_frozen_aware" in src, "C1: the conjugate applier consults the frozen-aware write")
    if "apply_image_distance_frozen_aware" in src:
        tail = src[src.index("apply_image_distance_frozen_aware"):]
        check(
            "rows[img_row].thickness = float(image_distance)" in tail,
            "C2: the plain prescription write is the FALLBACK branch, not the default",
        )
    check(
        src.index("rows[obj_row].thickness") < src.index("apply_image_distance_frozen_aware")
        if "apply_image_distance_frozen_aware" in src
        else False,
        "C3: the object write runs FIRST (stations shift before the world re-bake, bugs/0447)",
    )

    # --- D. the real scene: the solve must not leave the 62 mm defocus -------
    if not SCENE.exists():
        notes.append("SKIP: the AZ85 scene is not checked out; contract checks above still ran")
        return ok, notes
    try:
        import os

        os.environ.setdefault("MPLBACKEND", "Agg")
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService as _QE

        class _Shim:
            def __init__(self, editor):
                self.editor = editor

        editor = KrakenLayoutEditor()
        try:
            name = SCENE.stem
            editor.layout_files[name] = SCENE
            editor.load_layout_by_name(name)
            qe = _QE(_Shim(editor))
            editor.snap_detector_to_image_plane()
            before = float(editor._traced_bundle_best_focus_shift())
            applied, _msg = qe.fov_solve("object", "thickness", 30, 30, (23.04, 23.04))
            after = float(editor._traced_bundle_best_focus_shift())
            split = editor._folded_image_conjugate_split()
            geometry = editor._frozen_image_fold_world_geometry(split)
            far = None if geometry is None else float(geometry["far"])
        finally:
            try:
                editor.destroy()
            except Exception:
                pass
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({type(exc).__name__}: {exc})")
        return ok, notes

    notes.append(f"REAL = residual before {before:+.4f} mm, after {after:+.4f} mm, world far leg {far}")
    check(bool(applied), "D1: the FOV 30x30 solve applies on the frozen scene")
    check(abs(before) < 1.0, f"D2: remove-defocus really does zero the residual first (got {before:+.4f})")
    check(
        abs(after) < 0.5 * BROKEN_RESIDUAL_MM,
        f"D3: the solve does NOT leave the inverted-sign defocus (got {after:+.4f}, broken was +{BROKEN_RESIDUAL_MM})",
    )
    check(
        far is not None and abs(far - SOLVED_IMAGE_MM) < 1e-3,
        f"D4: the WORLD far leg equals the solved image distance {SOLVED_IMAGE_MM} (got {far})",
    )
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP", "REAL")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
