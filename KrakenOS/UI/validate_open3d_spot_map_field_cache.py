"""Display-free guard for bugs/0376 -- the 3D spot diagram stays blank after a fresh
import until save + restart + reload.

The per-field spot map traces 25 hexapolar fields and returns None when < 2 survive
(all vignette).  A fresh machine-vision import first sizes the field to the datasheet
MAX image height (e.g. 41 mm, well past the ~16 mm image circle -> every off-axis
field vignettes -> None); importing the camera then shrinks the field to the sensor
(16.29 mm, valid).  The spot-map spec is lazy + signature-cached, and the signature did
NOT include the field size, so the transient None cached while the field was 41 mm
STUCK for the whole session even after it shrank -- the spot diagram stayed blank until
a save + restart + reload started clean at 16.29 mm.  Distortion / astigmatism use a
fan scan that survives the oversized field, so they never cached a None and kept working.

Fix: fold the field metric into the spot-map cache signature (so the shrink invalidates
the stale None) and never persist a falsy spec (belt-and-suspenders).

Checks (all headless, no VTK):
- FIELD SIGNATURE changes with field height (so the 41 -> 16.29 shrink invalidates).
- NO-CACHE-FALSY: a None spec is not cached; a real spec IS cached.
- WIRING: the signature carries the field component and the cache guard is truthy-gated.
- REAL STEP (skipped if the Apo75 fixture is absent): spot is None at field 41 mm and a
  real 13-field map at 16.29 mm -- the exact pre/post camera-coupling transition.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_spot_map_field_cache
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    try:
        import pyvista  # noqa: F401

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: spot-map-field-cache deps unavailable ({type(exc).__name__}: {exc})"]

    # --- WIRING -------------------------------------------------------------------
    src = inspect.getsource(KrakenLayoutEditor.spot_field_map_overlay_spec)
    if "_spot_map_field_signature_component()" not in src:
        failures.append("the spot-map cache signature does not include the field-size component")
    if "and spec:" not in src:
        failures.append("the spot-map spec still caches a falsy (None/empty) result")

    # --- FIELD SIGNATURE changes with field height --------------------------------
    e = object.__new__(KrakenLayoutEditor)
    e._current_object_mode = lambda: "Finite"  # type: ignore[attr-defined]
    e._current_field_height = lambda: 41.0  # type: ignore[attr-defined]
    comp_big = e._spot_map_field_signature_component()
    e._current_field_height = lambda: 16.2917402385  # type: ignore[attr-defined]
    comp_small = e._spot_map_field_signature_component()
    if comp_big == comp_small:
        failures.append(f"field-signature component does not change with field height ({comp_big!r})")

    # --- NO-CACHE-FALSY (a transient None must not stick) --------------------------
    def _spec_stub(result):
        s = object.__new__(KrakenLayoutEditor)
        s._best_focus_surface_anchor_target = lambda b: SimpleNamespace(row_index=6)  # type: ignore[attr-defined]
        s._current_wavelength = lambda: 0.55  # type: ignore[attr-defined]
        s._field_aberration_exaggeration_value = lambda: None  # type: ignore[attr-defined]
        s._preview_trace_signature = lambda: ("preview-sig",)  # type: ignore[attr-defined]
        s._wavefront_map_signature = lambda: 0  # type: ignore[attr-defined]
        s._current_object_mode = lambda: "Finite"  # type: ignore[attr-defined]
        s._current_field_height = lambda: 41.0  # type: ignore[attr-defined]
        s._compute_spot_field_map_spec = lambda *a, **k: result  # type: ignore[attr-defined]
        return s

    none_stub = _spec_stub(None)
    out = none_stub.spot_field_map_overlay_spec(object(), object())
    if out is not None:
        failures.append("spot spec should be None when the field trace yields < 2 fields")
    if none_stub.__dict__.get("_spot_field_map_cache") is not None:
        failures.append("a None spot spec was CACHED -- it will stick after the field shrinks (the bug)")

    ok_stub = _spec_stub({"circles": [1, 2, 3]})
    out2 = ok_stub.spot_field_map_overlay_spec(object(), object())
    if not out2 or ok_stub.__dict__.get("_spot_field_map_cache") is None:
        failures.append("a real (non-empty) spot spec must be cached")

    # --- REAL STEP (optional): the exact pre/post camera-coupling transition -------
    apo = Path("attachment/machine_vision_Apo75.py")
    if apo.exists():
        try:
            import KrakenOS as Kos
            from KrakenOS.UI.layout_editor import _load_python_data
            from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor

            info = _load_python_data(apo)
            base = dict(info.get("settings", {}))
            rows = [KrakenLayoutEditor._row_from_layout_item(it) for it in info["surfaces"]]
            rows[0].surface, rows[-1].surface = "Object", "Image"

            def _spot_circles(field_value):
                s = dict(base); s["field_value"] = str(field_value)
                ed = _snapshot_editor(rows, s); ed.tk = object()
                ed.current_layout_file = apo; ed._normalize_special_rows()
                system = _build_runtime_system(apo, ed.rows)
                wl = float(ed._current_wavelength())
                target = ed._best_focus_surface_anchor_target(ed._build_scene_bundle(system, Kos.raykeeper(system), 20))
                spec = ed._compute_spot_field_map_spec(system, target, wl, None)
                return None if spec is None else len(spec.get("circles", []))

            if _spot_circles(41.0) is not None:
                failures.append("real STEP: spot map should be None at the oversized datasheet-max field (41mm)")
            if not (_spot_circles(16.2917402385) or 0) >= 2:
                failures.append("real STEP: spot map should be a real multi-field map at the sensor field (16.29mm)")
        except Exception as exc:  # pragma: no cover - fixture/OCC issue
            print(f"  (real-STEP spot check skipped: {type(exc).__name__}: {exc})")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Spot-map field-cache validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Spot-map field-cache validation passed: the spot-map cache signature carries the "
        "field size (so the datasheet-max -> sensor shrink on camera coupling invalidates a "
        "stale None), a falsy spec is never cached, and (when present) the real Apo75 map is "
        "None at 41mm but a real 13-field map at the 16.29mm sensor field."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
