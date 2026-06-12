"""Guard: the camera STEP overlay renders the WHOLE camera body (bugs/0068).

Reported (recording flag_20260612_113305_426, layout machine_vision_120mm_65M):
"Camera STEP is wrong." The 65 MP vendor camera (Japan Bopixel
BC-GM(C)65M12X4-F) drew as a thin ~6 mm slab floating at the sensor instead of
the real 80x80x96 mm body in attachment/65M.png.

Root cause: the camera overlay was loaded with ``largest_component=True``.
``_largest_connected_step_component`` keeps only the single connected region with
the MOST TRIANGLES (``argmax`` over per-region cell counts). On this assembly the
densest part is a small, highly-curved sensor-window cover -- solid #3, 41.75 x
35.75 x 6.24 mm, ~50 k triangles at 0.1 mm deflection -- while the actual body
(solids #0/#19, 80 x 80 x 29 mm, ~23x the volume) is a simpler box with far
fewer triangles and loses the vote. So the camera collapsed to its window.

Fix: a camera is a multi-part assembly (body + heat sink + mount + connectors),
so render the WHOLE thing -- ``largest_component=False`` -- in both the build
(``_transformed_imported_camera_step_mesh``) and the cache warm-up
(``_open3d_step_cache_warmup_specs``). The full 37-solid assembly is only
~116 k triangles total at 0.1 mm (barely more than the slab alone), well inside
the memoised "100 k cells render comfortably" envelope the code already cites.

This guard is DISPLAY-FREE and portable (the vendor STEP is a gitignored
attachment, so it is never required):
  * A -- the metric trap, on a synthetic disconnected mesh: the production
    ``_largest_connected_step_component`` returns the dense-but-tiny region, not
    the big-but-coarse one (this is exactly why the camera collapsed).
  * B (fail-before/pass-after) -- the cache warm-up now lists the camera with
    largest=False, exercised behaviourally through the real method.
  * C (fail-before/pass-after) -- the camera build requests the full assembly.
  * D -- real-cache enrichment (skip-if-absent): the largest-component cache is a
    thin slab; once present, the full cache is the deep body.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_camera_step_full_body

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import glob
import inspect
import os
import tempfile

try:  # pyvista is a hard dependency of the app; the synthetic/cache checks need it.
    import pyvista as pv
except Exception:  # pragma: no cover - environment without pyvista
    pv = None


_CAMERA_CACHE_GLOB = "attachment/cad_cache/BC-GM*65M12X4-F*"


def _bbox_dims(bounds) -> tuple[float, float, float]:
    return (
        float(bounds[1] - bounds[0]),
        float(bounds[3] - bounds[2]),
        float(bounds[5] - bounds[4]),
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    # --- A. the metric trap that collapsed the camera ------------------------
    # A multi-part assembly + a "keep the most-tessellated region" rule picks the
    # densest *small* part, not the biggest body. Prove it against the real
    # production selector on a synthetic two-region mesh.
    if pv is None:
        skip("A: pyvista unavailable -- cannot exercise _largest_connected_step_component")
    else:
        class _SelShim:
            def append_debug(self, *_a, **_k):
                return None

            def _drop_invalid_step_cell_data(self, mesh, context=""):
                return mesh

        # Big, coarse body (few triangles) vs small, dense window (many triangles).
        body = pv.Box(bounds=(-40.0, 40.0, -40.0, 40.0, -48.0, 48.0)).triangulate()
        window = (
            pv.Box(bounds=(188.0, 212.0, -10.0, 10.0, -3.0, 3.0))
            .triangulate()
            .subdivide(3)
        )
        body_cells, window_cells = int(body.n_cells), int(window.n_cells)
        combined = body.merge(window, merge_points=False).extract_surface()

        kept = LayoutPolylineDisplayMixin._largest_connected_step_component(_SelShim(), combined)
        kept_cells = int(getattr(kept, "n_cells", 0))
        bdx, bdy, bdz = _bbox_dims(body.bounds)
        kdx, kdy, kdz = _bbox_dims(kept.bounds)
        body_vol, kept_vol = bdx * bdy * bdz, kdx * kdy * kdz

        ok(window_cells > body_cells,
           f"A1: synthetic window out-triangulates the body ({window_cells} > {body_cells} cells) -- the trap's premise")
        ok(kept_cells == window_cells,
           f"A2: _largest_connected_step_component keeps the most-TRIANGLE region (kept {kept_cells} cells == window {window_cells})")
        ok(kept_vol < 0.25 * body_vol,
           f"A3 (root cause): the kept region is the SMALL dense part, not the big body "
           f"(kept bbox vol {kept_vol:.0f} mm^3 << body {body_vol:.0f} mm^3) -- this is what shrank the camera to its window")

    # --- B. cache warm-up now requests the FULL camera assembly --------------
    tmp_path = None
    try:
        fd, tmp_name = tempfile.mkstemp(suffix=".step")
        os.close(fd)
        tmp_path = tmp_name

        class _WarmupShim:
            imported_lens_step_path = None
            imported_optical_step_path = None
            imported_led_step_path = None
            lens_step_largest_component_only = True

            def __init__(self, camera_path):
                self.imported_camera_step_path = camera_path

            def _open3d_step_display_cache_ready(self, *_a, **_k):
                return False  # force the spec to be emitted so we can read its flag

        specs = ThreeDSceneToolsMixin._open3d_step_cache_warmup_specs(_WarmupShim(tmp_path))
        camera_specs = [s for s in specs if s and s[0] == "camera"]
        ok(len(camera_specs) == 1,
           f"B0: warm-up emits exactly one camera spec ({len(camera_specs)} found)")
        if camera_specs:
            largest_flag = bool(camera_specs[0][2])
            ok(largest_flag is False,
               f"B1 (fail-before/pass-after): camera warm-up requests the FULL assembly, not the largest component "
               f"(largest_component={largest_flag}; was True -> rendered the window slab)")
    except Exception as exc:  # pragma: no cover - defensive
        ok(False, f"B: warm-up wiring probe raised {type(exc).__name__}: {exc}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # --- C. the camera BUILD path requests the full assembly -----------------
    build_src = inspect.getsource(LayoutPolylineDisplayMixin._transformed_imported_camera_step_mesh)
    ok("largest_component=False" in build_src,
       "C1 (fail-before/pass-after): _transformed_imported_camera_step_mesh loads with largest_component=False")
    ok("largest_component=True" not in build_src,
       "C2: the camera build no longer requests largest_component=True (the regression line is gone)")

    # --- D. real vendor-cache enrichment (skip-if-absent, non-portable) ------
    if pv is None:
        skip("D: pyvista unavailable -- cannot read STEP display caches")
    else:
        largest_caches = sorted(glob.glob(_CAMERA_CACHE_GLOB + "analytic_largest*.vtp"))
        full_caches = sorted(
            p for p in glob.glob(_CAMERA_CACHE_GLOB + "*.vtp")
            if "analytic_largest" not in os.path.basename(p) and ".analytic." in os.path.basename(p)
        )
        if largest_caches:
            try:
                dx, dy, dz = _bbox_dims(pv.read(largest_caches[-1]).bounds)
                ok(dz < 10.0 and dz < 0.25 * max(dx, dy),
                   f"D1: the largest-component cache IS the thin slab the user saw "
                   f"(dims {dx:.1f} x {dy:.1f} x {dz:.1f} mm) -- proves the old path was wrong on real vendor data")
            except Exception as exc:  # pragma: no cover
                skip(f"D1: could not read largest-component cache ({type(exc).__name__}: {exc})")
        else:
            skip("D1: no largest-component camera cache on disk (regenerated only on the original machine)")
        if full_caches:
            try:
                dx, dy, dz = _bbox_dims(pv.read(full_caches[-1]).bounds)
                ok(dz > 60.0,
                   f"D2: the full-assembly cache is the DEEP camera body "
                   f"(dims {dx:.1f} x {dy:.1f} x {dz:.1f} mm) -- the fix's output on real vendor data")
            except Exception as exc:  # pragma: no cover
                skip(f"D2: could not read full-assembly cache ({type(exc).__name__}: {exc})")
        else:
            skip("D2: no full-assembly camera cache yet (created on the next in-app layout load after the fix)")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Camera-STEP full-body validation passed.")
        return 0
    print("Camera-STEP full-body validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
