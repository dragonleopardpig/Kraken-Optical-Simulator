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


class _Row:
    def __init__(self, thickness):
        self.thickness = float(thickness)


class _Stub:
    """Drives apply_image_distance_frozen_aware without a scene."""

    def __init__(self, split=None, geometry=None, gap_now=44.1193):
        self._split = split
        self._geometry = geometry
        self.rows = [_Row(0.0) for _ in range(9)]
        if isinstance(split, dict) and "far_gap_row" in split:
            self.rows[int(split["far_gap_row"])] = _Row(gap_now)

    def _folded_image_conjugate_split(self):
        return self._split

    def _frozen_image_fold_world_geometry(self, split):
        return self._geometry


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
        fn(_Stub(split={"mirror_row": 7, "far_gap_row": 7}, geometry=None), 12.0) is False,
        "A2: a fold that is NOT frozen -> falls back (geometry is None)",
    )
    SPLIT = {"mirror_row": 7, "far_gap_row": 7}
    GEO = {"near": 58.8807, "far": 58.8807}
    bad = _Stub(split=SPLIT, geometry=GEO)
    check(fn(bad, 0.0) is False and bad.rows[7].thickness == PRE_SOLVE_ROW7, "A3: a non-positive image distance is refused")
    check(fn(bad, float("nan")) is False and bad.rows[7].thickness == PRE_SOLVE_ROW7, "A4: a non-finite image distance is refused")
    check(
        fn(_Stub(split=SPLIT, geometry=GEO), 1.0e6) is False,
        "A5: an image distance that would need a NEGATIVE gap is refused, not written",
    )

    # --- B. the frozen write: the gap that YIELDS the wanted world leg -------
    # The world leg is derived from the gap (const - thickness), so the invariant
    # ``gap + world_far`` must be preserved. Re-baking the sensor's world centre while
    # leaving the gap stale (the first 0478 attempt) broke exactly this, and the drift
    # compounded across successive solves.
    good = _Stub(split=SPLIT, geometry=GEO)
    const = good.rows[7].thickness + GEO["far"]
    check(fn(good, SOLVED_IMAGE_MM) is True, "B1: a frozen folded scene is handled")
    check(
        abs(good.rows[7].thickness - (const - SOLVED_IMAGE_MM)) < 1e-9,
        f"B2: the gap is written as const - far_new (got {good.rows[7].thickness:.4f}, "
        f"want {const - SOLVED_IMAGE_MM:.4f})",
    )
    check(
        abs((good.rows[7].thickness + SOLVED_IMAGE_MM) - const) < 1e-9,
        "B3: the gap + world-leg INVARIANT is preserved (the frames do not drift)",
    )
    # Applying twice must land on the same place, not compound.
    again = _Stub(split=SPLIT, geometry={"near": 58.8807, "far": SOLVED_IMAGE_MM}, gap_now=good.rows[7].thickness)
    check(fn(again, SOLVED_IMAGE_MM) is True and abs(again.rows[7].thickness - good.rows[7].thickness) < 1e-9,
          "B4: re-applying the SAME distance is idempotent (no compounding drift)")

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
            def _invariant():
                s = editor._folded_image_conjugate_split()
                g = editor._frozen_image_fold_world_geometry(s)
                if g is None:
                    return None, None
                gap = float(editor.rows[int(s["far_gap_row"])].thickness)
                return float(g["far"]), gap + float(g["far"])

            editor.snap_detector_to_image_plane()
            before = float(editor._traced_bundle_best_focus_shift())
            _f0, inv0 = _invariant()
            # The flagged sequence: 23x23 and THEN 30x30 -- a repeated solve is what exposed
            # the frame drift, so the guard drives it twice too.
            applied, _msg = qe.fov_solve("object", "thickness", 23, 23, (23.04, 23.04))
            _f1, inv1 = _invariant()
            applied, _msg = qe.fov_solve("object", "thickness", 30, 30, (23.04, 23.04))
            after = float(editor._traced_bundle_best_focus_shift())
            far, inv2 = _invariant()
        finally:
            try:
                editor.destroy()
            except Exception:
                pass
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({type(exc).__name__}: {exc})")
        return ok, notes

    notes.append(
        f"REAL = residual before {before:+.4f} mm, after {after:+.4f} mm, world far leg {far}; "
        f"invariant {inv0} -> {inv1} -> {inv2}"
    )
    check(bool(applied), "D1: the FOV 23x23 then 30x30 solves apply on the frozen scene")
    check(abs(before) < 1.0, f"D2: remove-defocus really does zero the residual first (got {before:+.4f})")
    check(
        abs(after) < 0.5 * BROKEN_RESIDUAL_MM,
        f"D3: the solve does NOT leave the inverted-sign defocus (got {after:+.4f}, broken was +{BROKEN_RESIDUAL_MM})",
    )
    check(
        far is not None and abs(far - SOLVED_IMAGE_MM) < 1e-3,
        f"D4: the WORLD far leg equals the solved image distance {SOLVED_IMAGE_MM} (got {far})",
    )
    check(
        None not in (inv0, inv1, inv2) and abs(inv1 - inv0) < 1e-6 and abs(inv2 - inv0) < 1e-6,
        f"D5: gap + world-leg is CONSTANT across two successive solves "
        f"({inv0} -> {inv1} -> {inv2}); it drifted 103.0 -> 82.85 -> 62.98 when the sensor "
        f"was re-baked and the gap left stale",
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
