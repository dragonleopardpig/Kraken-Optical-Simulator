"""bugs/0291 -- adding an illumination LED must NOT drop the scene's real detector.

Closes flag_20260713_090936_572 ("the detector and object plane seems missing" after Add LED).  Adding a
physical LED seeds an illumination flood (0290) that reflects off the promoted beam-splitter cube into arms
that never converge, so the branch-detector deriver parks PHANTOM branch detectors beside the cube.  bugs/0285
marks every non-imaging flood branch ``draw_suppressed`` (a ray hard-stop only), so none of them draws -- but
``drop_superseded_image_display`` still dropped the real sequential detector *for* them (the gate was
``bool(branch_detectors)``), leaving the scene with no visible detector at all.

The fix (display follows physics): the sequential Image is superseded (droppable) for two independent reasons
only -- a branch detector that will actually DRAW replaces it (bugs/0093/0098/0090), OR the whole scene is a
diffuse double-pass so the sequential trace is itself noise (bugs/0184).  An illumination flood is neither, so
the real detector is kept.

These checks are display-free (no VTK window).  The real-vendor-scene check drives the actual bundle builder
on ``attachment/machine_vision_150mm_test.py`` with a synthetic OPT-CO90 module injected (the gitignored STEP
is not required) and SKIPs when the attachment is absent.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_illumination_keeps_real_detector

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import os
import types
from types import SimpleNamespace

_ATTACHMENT = "attachment/machine_vision_150mm_test.py"

# The real OPT-CO90 placement (memory: 55x78 mm LED, moved +22.9 x, object-facing min-z face at z~187).
_MODULE_BOUNDS = (1.1, 56.1, -39.0, 39.0, 187.0, 265.0)


# --------------------------------------------------------------------------------------------------
# 1. drop_superseded_image_display contract -- pure, always-on
# --------------------------------------------------------------------------------------------------
def _check_helper_contract(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.scene_builder import drop_superseded_image_display

    def scene():
        targets = [
            SimpleNamespace(row_index=0, surface="Object", is_detector=False, is_object=True, metadata={}),
            SimpleNamespace(row_index=8, surface="Image", is_detector=True, is_object=False, metadata={}),
            SimpleNamespace(row_index=100000, surface="Image", is_detector=True, is_object=False,
                            metadata={"draw_suppressed": True}),  # phantom flood branch
        ]
        curves = [
            SimpleNamespace(row_index=0, kind="object"),
            SimpleNamespace(row_index=8, kind="image"),
            SimpleNamespace(row_index=-1, kind="image"),  # branch detector plane
        ]
        labels = [SimpleNamespace(row_index=0, text="Object"), SimpleNamespace(row_index=8, text="Image")]
        rows = [SimpleNamespace(surface="Object"), SimpleNamespace(surface="Image")]
        return targets, curves, labels, rows

    # NOT superseded (the 0291 illumination-flood case): keep the sequential detector + its label.
    t, c, lbls, rows = scene()
    t0, _c0, l0 = drop_superseded_image_display(t, c, lbls, rows, has_branch_detector=False)
    if 8 not in [x.row_index for x in t0]:
        failures.append("HELPER: sequential detector dropped when nothing supersedes it (the 0291 bug)")
    if "Image" not in [x.text for x in l0]:
        failures.append("HELPER: 'Image' label dropped with no superseding branch")

    # Superseded (the 0093/0098/0184 cases): drop the sequential detector, keep the branch row (>=100000).
    t, c, lbls, rows = scene()
    t1, _c1, _l1 = drop_superseded_image_display(t, c, lbls, rows, has_branch_detector=True)
    kept = [x.row_index for x in t1]
    if 8 in kept:
        failures.append("HELPER: sequential detector NOT dropped when superseded")
    if 100000 not in kept:
        failures.append("HELPER: branch detector (row >= 100000) wrongly dropped")

    notes.append("helper: keeps the sequential detector unless superseded; branch rows untouched")


# --------------------------------------------------------------------------------------------------
# 2. build_scene_bundle call site -- the reconciliation is locked in source
# --------------------------------------------------------------------------------------------------
def _check_call_site(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI import scene_builder

    src = inspect.getsource(scene_builder.build_scene_bundle)
    flat = " ".join(src.split())

    if "has_drawn_branch_detector" not in src:
        failures.append("CALLSITE: build_scene_bundle no longer computes has_drawn_branch_detector")
    if "scene_has_diffuse_scatter" not in src:
        failures.append("CALLSITE: the drop no longer keeps the bugs/0184 diffuse-scatter reason")
    if "has_drawn_branch_detector or scene_has_diffuse_scatter" not in flat:
        failures.append("CALLSITE: supersede gate is not (has_drawn_branch_detector OR scene_has_diffuse_scatter)")
    if "draw_suppressed" not in src:
        failures.append("CALLSITE: has_drawn_branch_detector does not exclude draw_suppressed phantom branches")
    # The pre-0291 form dropped the real detector for phantom branches -- it must be gone.
    if "has_branch_detector=bool(branch_detectors)" in src.replace(" ", ""):
        failures.append(
            "CALLSITE: reverted to has_branch_detector=bool(branch_detectors) -- drops the real detector for phantoms"
        )

    notes.append("call-site: drop gated on drawn-branch OR diffuse-scatter; draw_suppressed phantoms excluded")


# --------------------------------------------------------------------------------------------------
# 3. Real vendor scene -- optional (attachment gitignored; runs on the user's machines)
# --------------------------------------------------------------------------------------------------
def _load_vendor_editor(path):
    from KrakenOS.UI.layout_editor import _load_python_data
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor

    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    return editor


def _bundle(editor):
    import KrakenOS as Kos
    from KrakenOS.UI.render_layout_snapshot import _build_runtime_system

    path = editor.current_layout_file
    system = _build_runtime_system(path, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    return editor._build_scene_bundle(system, rays, max_radius)


def _drawn_detector_rows(bundle):
    """Sequential detector rows that will DRAW: 0 <= row < 100000, is_detector, not draw_suppressed."""
    rows = set()
    for t in getattr(bundle, "targets", []) or []:
        ri = int(getattr(t, "row_index", -1))
        if 0 <= ri < 100000 and bool(getattr(t, "is_detector", False)):
            if not (getattr(t, "metadata", None) or {}).get("draw_suppressed"):
                rows.add(ri)
    return rows


def _check_real_vendor_scene(failures: list[str], notes: list[str]) -> None:
    from pathlib import Path

    path = Path(_ATTACHMENT)
    if not path.exists():
        notes.append(f"SKIP real vendor scene: {_ATTACHMENT} absent (gitignored -- see bugs/diag_0291_missing_detector_object)")
        return
    try:
        # (A) baseline, no LED -- the real detector is present.
        base = _load_vendor_editor(path)
        base_bundle = _bundle(base)

        # (B) with a synthetic OPT-CO90 module injected + Add LED -- the same flow that lost the detector.
        led = _load_vendor_editor(path)
        led.imported_led_step_path = "synthetic-OPT-CO90-X.STEP"
        led._transformed_imported_led_step_mesh = lambda: types.SimpleNamespace(bounds=_MODULE_BOUNDS)
        led.add_illumination_led_source(record_history=False)
        led_bundle = _bundle(led)
    except Exception as exc:
        failures.append(f"REAL: driving the vendor scene raised {exc!r}")
        return

    base_rows = _drawn_detector_rows(base_bundle)
    if not base_rows:
        failures.append("REAL: the no-LED baseline has no drawn detector -- fixture changed, check the scene")
        return

    led_targets = list(getattr(led_bundle, "targets", []) or [])
    phantoms = [t for t in led_targets if int(getattr(t, "row_index", -1)) >= 100000]
    drawn_phantoms = [t for t in phantoms if not (getattr(t, "metadata", None) or {}).get("draw_suppressed")]
    if not phantoms:
        failures.append("REAL: Add LED produced NO branch detector -- the scene no longer exercises the 0291 drop path")
    if drawn_phantoms:
        # A phantom that draws would legitimately supersede the sequential detector -- not the 0291 case.
        notes.append(f"REAL: {len(drawn_phantoms)} branch detector(s) draw and legitimately supersede -- not a flood phantom")

    led_rows = _drawn_detector_rows(led_bundle)
    if not led_rows:
        failures.append("REAL: Add LED DROPPED the real detector (the flag) -- 0291 regressed")

    # The surviving detector must have a surface curve + an 'Image' label (drawn by both views).
    curve_rows = {int(getattr(c, "row_index", -1)) for c in (getattr(led_bundle, "surface_curves", []) or [])}
    if led_rows and not (led_rows & curve_rows):
        failures.append(f"REAL: the surviving detector row(s) {sorted(led_rows)} have no surface curve to draw")
    labels = [str(getattr(l, "text", getattr(l, "label", ""))) for l in (getattr(led_bundle, "labels", []) or [])]
    if "Image" not in labels:
        failures.append(f"REAL: the 'Image' detector label is gone after Add LED ({labels})")

    # The object plane must NOT have been dropped (the user's second worry -- it's a framing artefact).
    if not any(bool(getattr(t, "is_object", False)) for t in led_targets):
        failures.append("REAL: the object plane target was dropped after Add LED")

    notes.append(
        f"real vendor scene: detector rows {sorted(base_rows)} survive Add LED as {sorted(led_rows)}; "
        f"{len(phantoms)} phantom flood branch(es) stay suppressed; object + 'Image' label intact"
    )


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_helper_contract(failures, notes)
    _check_call_site(failures, notes)
    _check_real_vendor_scene(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    os.environ.setdefault("MPLBACKEND", "Agg")
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    print(f"\n=== validate_open3d_illumination_keeps_real_detector: {'PASS' if passed else 'FAIL'} ===")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
