"""Guard for bugs/0625 — the launch grid recentres on the DELIVERED field centre.

flag_20260817_080138 ("object side still mising 2 launch rays"): the real folded
machine images the field OFF-CENTRE along the fold axis — a launch grid centred on
the object datum lost the entire x=-27.6 column off the glass (7 of 9 field spots).
The bugs/0591 correction fixes the delivered SCALE; this learns the delivered
CENTRE: three traced probes measure the field->landing Jacobian, the shift solves
J @ S = -C0, a FOURTH probe must verify (bugs/0613) before anything is stored, and
the launch grid + drawn FOV square shift by the learned centre.

Checks (display-free):
  A  CONTRACT — quick_estimation: the learner exists, BOTH refinement exits call it,
     BOTH unmeasurable exits clear the centre state alongside the scale state.
  B  BEHAVIOUR — on a synthetic linear machine the learner recovers the true shift
     exactly; an unverifiable machine (probe 4 shows no improvement) stores NOTHING;
     an already-centred machine stores (0, 0).
  C  BEHAVIOUR — `_sample_imaging_field_grid_pairs` offsets its linspace grids by the
     learned centre; with no learned state the grid is byte-identical symmetric
     (sequential scenes and stub guards unchanged); count<=1 launches AT the centre.
  D  CONTRACT — the detector-coverage overlay shifts the drawn object-FOV square by
     the same state (launch grid and drawn square must agree — bugs/0602 doctrine).
  E  CONTRACT — machine state dies with the machine: cleared in load_layout_by_name,
     open_layout, the zemax loader, lens swap and camera import (two-loader rule,
     bugs/0563).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0625_delivered_field_center
"""

from __future__ import annotations

import inspect

import numpy as np


def _quick_estimation_class():
    from KrakenOS.UI.services import quick_estimation as qe_module

    for name, cls in vars(qe_module).items():
        if isinstance(cls, type) and hasattr(cls, "_learn_folded_field_center"):
            return cls
    return None


class _EditorDouble:
    """Editor stub exposing the world-order instrument as a synthetic linear machine.

    centroid(field) = A @ (field - true_shift): a magnification-like linear map whose
    delivered centre sits at ``true_shift`` on the object plane. ``verify_broken``
    makes the 4th (verification) probe return the ORIGINAL centroid — a machine where
    the correction demonstrably does not work, which bugs/0613 says must store nothing.
    """

    def __init__(self, true_shift, verify_broken=False):
        self._A = np.array([[-0.42, 0.013], [0.021, -0.40]])
        self._true_shift = np.asarray(true_shift, dtype=float)
        self._verify_broken = verify_broken
        self._calls = 0
        self.debug: list[str] = []
        self._folded_field_center_state = None

    def _world_placed_chain_rows(self):
        return [object()]

    def _current_wavelength(self):
        return 0.55

    def _world_launch_acceptance(self, wavelength):
        return 0.08

    def _world_launch_pupil_distance_cached(self, wavelength, acceptance):
        return 150.0

    def _world_order_field_bundle(self, mode, field_x, field_y, rays, acceptance, pupil_distance):
        return (float(field_x), float(field_y))

    def _world_order_trace_landings(self, wavelength, bundle):
        self._calls += 1
        field = np.array(bundle, dtype=float)
        centroid = self._A @ (field - self._true_shift)
        if self._verify_broken and self._calls > 3:
            centroid = self._A @ (np.zeros(2) - self._true_shift)
        ones = np.ones(7)
        return centroid[0] * ones, centroid[1] * ones, ones, ones, ones, ones

    def append_debug(self, message):
        self.debug.append(str(message))


class _ServiceDouble:
    def __init__(self, editor):
        self.editor = editor


def run_checks():
    notes: list[str] = []
    ok = True

    qe_cls = _quick_estimation_class()
    if qe_cls is None:
        return False, ["FAIL: A: no quick-estimation class with _learn_folded_field_center"]

    # ---------------------------------------------------------------- A: contract
    if not hasattr(qe_cls, "_refine_folded_field_fill"):
        return False, ["FAIL: A: quick-estimation class lost _refine_folded_field_fill"]
    refine_srcs = inspect.getsource(qe_cls._refine_folded_field_fill)
    learn_calls = refine_srcs.count("_learn_folded_field_center(")
    center_clears = refine_srcs.count("_folded_field_center_state = None")
    relearn_src = inspect.getsource(qe_cls.relearn_folded_m_correction)
    if learn_calls < 2:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0625): only {learn_calls} refinement exit(s) learn the field "
            "centre -- a solve path exists whose grid stays decentred"
        )
    elif center_clears < 2:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0625): only {center_clears} unmeasurable exit(s) clear the "
            "centre -- a stale centre survives an unlearn (bugs/0613)"
        )
    elif "_learn_folded_field_center(" not in relearn_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0625): relearn_folded_m_correction (the swap/load one-shot) "
            "does not learn the centre -- a loaded or swapped scene keeps a decentred grid"
        )
    else:
        notes.append(
            f"PASS: A: {learn_calls} refinement exits + the swap/load relearn learn, "
            f"{center_clears} unmeasurable exits clear"
        )

    # ---------------------------------------------------------------- B: learning behaviour
    true_shift = (4.3, -1.7)
    editor = _EditorDouble(true_shift)
    result = qe_cls._learn_folded_field_center(_ServiceDouble(editor), 27.55)
    stored = editor._folded_field_center_state
    if (
        result is None
        or stored is None
        or abs(stored[0] - true_shift[0]) > 1e-6
        or abs(stored[1] - true_shift[1]) > 1e-6
    ):
        ok = False
        notes.append(
            f"FAIL: B (bugs/0625): linear machine with centre {true_shift} learned {stored} "
            "-- the Jacobian solve does not recover the delivered centre"
        )
    else:
        notes.append(f"PASS: B: learned {tuple(round(v, 3) for v in stored)} == true centre")

    broken = _EditorDouble(true_shift, verify_broken=True)
    result_broken = qe_cls._learn_folded_field_center(_ServiceDouble(broken), 27.55)
    if result_broken is not None or broken._folded_field_center_state is not None:
        ok = False
        notes.append(
            "FAIL: B (bugs/0625): a shift whose verification probe shows NO improvement "
            f"was stored ({broken._folded_field_center_state}) -- violates bugs/0613 "
            "verified trust"
        )
    elif not any("did not verify" in line for line in broken.debug):
        ok = False
        notes.append("FAIL: B (bugs/0625): unverified shift rejected silently -- no debug note")
    else:
        notes.append("PASS: B: unverified shift stored nothing and logged the refusal")

    centred = _EditorDouble((0.0, 0.0))
    qe_cls._learn_folded_field_center(_ServiceDouble(centred), 27.55)
    if centred._folded_field_center_state != (0.0, 0.0):
        ok = False
        notes.append(
            f"FAIL: B (bugs/0625): already-centred machine stored "
            f"{centred._folded_field_center_state} instead of (0.0, 0.0)"
        )
    else:
        notes.append("PASS: B: already-centred machine stores the explicit (0, 0)")

    # ---------------------------------------------------------------- C: grid consumer
    from KrakenOS.UI.services import trace_preview_sampling as sampling_module

    mixin = None
    for name, cls in vars(sampling_module).items():
        if isinstance(cls, type) and hasattr(cls, "_sample_imaging_field_grid_pairs"):
            mixin = cls
            break
    if mixin is None:
        return False, notes + ["FAIL: C: no sampling mixin with _sample_imaging_field_grid_pairs"]

    class _Sampler(mixin):
        def __init__(self, center, count=3):
            self._folded_field_center_state = center
            self._count = count

        def _imaging_fov_half_extents(self):
            return (10.0, 10.0)

        def _current_field_count(self):
            return self._count

    # SIGN CONTRACT: the learned centre is a WORLD offset (the instrument frame,
    # geometric_analysis: o_x = origin + field_x), but the grid pairs feed PupilCalc-style
    # launchers whose 'height' convention launches from MINUS the pair value (PupilTool:
    # shiftX = -FieldX; the world launcher: origin = anchor - field). The world shift
    # therefore enters the PAIRS negated -- measured on the flagged Apo75: the un-negated
    # shift moved the pencils AWAY from the delivered field and killed the mirrored edge
    # column (probe v1 of diag_0625_field_center_verify).
    shifted = _Sampler((3.25, -1.5))._sample_imaging_field_grid_pairs()
    neutral = _Sampler(None)._sample_imaging_field_grid_pairs()
    single = _Sampler((3.25, -1.5), count=1)._sample_imaging_field_grid_pairs()
    want_shifted_x = sorted({-10.0 - 3.25, -3.25, 10.0 - 3.25})
    got_shifted_x = sorted({round(x, 9) for x, _y in shifted})
    want_neutral_x = [-10.0, 0.0, 10.0]
    got_neutral_x = sorted({round(x, 9) for x, _y in neutral})
    if len(shifted) != 9 or got_shifted_x != want_shifted_x:
        ok = False
        notes.append(
            f"FAIL: C (bugs/0625): learned grid x-values {got_shifted_x} != {want_shifted_x} "
            "-- pairs must carry the world shift NEGATED (PupilCalc launches from -Field), "
            "or the pencils recentre on the WRONG side and the mirrored edge column dies"
        )
    elif got_neutral_x != want_neutral_x or any(round(y, 9) not in (-10.0, 0.0, 10.0) for _x, y in neutral):
        ok = False
        notes.append(
            f"FAIL: C (bugs/0625): unlearned grid moved ({got_neutral_x}) -- sequential "
            "scenes must be byte-identical symmetric"
        )
    elif single != [(-3.25, 1.5)]:
        ok = False
        notes.append(
            f"FAIL: C (bugs/0625): single-field launch {single} != the learned centre in "
            "pair convention (-world shift)"
        )
    else:
        notes.append("PASS: C: grid recentres (world shift negated into pair convention), symmetric when not")

    # The bugs/0522 corner probes must probe the corners of the SAME delivered rectangle
    # -- unshifted corners double-launch beside the shifted grid and probe a field the
    # machine does not image (the four extra 10-ray pencils in the flag_124307 census).
    corner_src = inspect.getsource(mixin._build_world_bundles_from_pupil_points)
    if "_folded_field_center_state" not in corner_src:
        ok = False
        notes.append(
            "FAIL: C (bugs/0625): the FOV-corner probes ignore the learned centre -- they "
            "launch from the unshifted corners and duplicate/mis-probe the field"
        )
    else:
        notes.append("PASS: C: corner probes share the learned-centre shift")

    # ---------------------------------------------------------------- D: overlay contract
    from KrakenOS.UI.services import detector_coverage_overlay as overlay_module

    overlay_cls = None
    for name, cls in vars(overlay_module).items():
        if isinstance(cls, type) and hasattr(cls, "add_overlays"):
            overlay_cls = cls
            break
    overlay_src = inspect.getsource(overlay_cls.add_overlays) if overlay_cls is not None else ""
    if "_folded_field_center_state" not in overlay_src:
        ok = False
        notes.append(
            "FAIL: D (bugs/0625): the drawn object-FOV square ignores the learned centre "
            "-- grid and drawn square disagree (bugs/0602 doctrine)"
        )
    else:
        notes.append("PASS: D: the drawn FOV square shifts by the same learned centre")

    # ---------------------------------------------------------------- E: invalidation
    from KrakenOS.UI.services import layout_import_export as import_export_module
    from KrakenOS.UI.services import layout_table_workbench as workbench_module

    site_sources = {
        "load_layout_by_name": None,
        "swap_imaging_lens_from_folder": None,
        "import_vendor_camera_from_folder": None,
    }
    for module in (workbench_module, import_export_module):
        for name, cls in vars(module).items():
            if not isinstance(cls, type):
                continue
            for site in site_sources:
                if site_sources[site] is None and site in vars(cls):
                    site_sources[site] = inspect.getsource(getattr(cls, site))
    missing = [
        site
        for site, src in site_sources.items()
        if src is None or "_folded_field_center_state = None" not in src
    ]
    open_layout_src = ""
    zemax_src = ""
    for name, cls in vars(import_export_module).items():
        if isinstance(cls, type) and hasattr(cls, "open_layout"):
            open_layout_src = inspect.getsource(cls.open_layout)
            if hasattr(cls, "_load_zemax_prescription_path"):
                zemax_src = inspect.getsource(cls._load_zemax_prescription_path)
            break
    for site, src in (("open_layout", open_layout_src), ("zemax loader", zemax_src)):
        for state in ("_folded_m_correction_state = None", "_folded_field_center_state = None"):
            if state not in src:
                missing.append(f"{site} ({state.split(' ')[0]})")
    # The bugs/0608 doctrine extended to loads: clearing alone leaves a freshly loaded
    # folded scene tracing the RAW first order (the flagged workflow -- load, no solve).
    # Every full-scene loader must RE-MEASURE after clearing.
    for site, src in (
        ("load_layout_by_name", site_sources.get("load_layout_by_name") or ""),
        ("open_layout", open_layout_src),
    ):
        if "_relearn_folded_m_correction_after_swap(" not in src:
            missing.append(f"{site} (no re-measure after clear)")
    if missing:
        ok = False
        notes.append(
            f"FAIL: E (bugs/0625): stale machine state survives {missing} -- a new scene "
            "inherits the old machine's measured centre/scale (two-loader rule, bugs/0563)"
        )
    else:
        notes.append("PASS: E: centre + scale cleared in every loader and both swaps")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Delivered-field-centre validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
