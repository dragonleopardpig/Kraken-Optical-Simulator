"""Display-free guard for bugs/0015 — rays must trace per physics regardless of
which element is dropped where along the path.

Regression context
-------------------
A beam splitter (or any non-"Image" element) placed on the terminal prescription
row used to strip that surface's detector role: ``_scene_detector_surface_indices``
only recognised a literal ``surface == "Image"`` row as the terminal image plane.
With no detector, every branch was classified ``escaped`` and the default
"hide clipped rays" display filter silently dropped *every* physically-traced
ray (North Star invariant 4 violation — ambiguous geometry must emit diagnostics,
never a silent drop). The fix treats the final prescription surface as the
terminal image plane for display purposes regardless of its optical type.

Invariants asserted here (all headless / display-free):

1. No silent drop: with "Show Clipped Rays" ON, the number of displayed rays
   equals the number of traced ray paths for *any* element at *any* position.
   A traced ray is always displayable; the default filter is a convenience, not
   a physics gate.
2. Terminal regression guard: a beam splitter on the terminal surface shows its
   forward (transmitted) rays by default (clipped OFF) and the terminal index is
   classified as a detector.
3. Random-element robustness: a seeded sweep drops a random element type at a
   random position (terminal included) and confirms (1) holds and the trace is
   non-empty — rays never vanish silently.
"""
from __future__ import annotations

import argparse
import os
import random

# Headless rendering — never touch a live Wayland/X session.
os.environ.pop("WAYLAND_DISPLAY", None)
os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

from KrakenOS.UI.layout_editor import SurfaceRow
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor

BASE_SETTINGS = {
    "ray_count": "5",
    "field_count": "1",
    "field_type": "Angle",
    "field_value": "0.0",
    "aperture_type": "EPD",
    "aperture_value": "20.0",
    "object_mode": "Finite",
    "wavelength": "0.55",
    "show_clipped_rays": False,
}

# Element types a user can drop onto an existing row. "Standard" is the no-op
# control; the rest are the North Star non-sequential triggers / fold elements.
RANDOM_ELEMENT_TYPES = ("Beam Splitter", "Mirror", "Thin Lens", "Grating", "Standard")


def _lens_rows(element: str | None = None, at_index: int | None = None) -> list[SurfaceRow]:
    """A finite-conjugate BK7 singlet feeding an Image plane.

    When ``element``/``at_index`` are given, the row at ``at_index`` has its
    surface *type* swapped to ``element`` — emulating the user dropping a random
    optical element onto that surface (including the terminal Image row).
    """
    specs = [
        ("Object", "Object", 300.0, "AIR", 0.0),
        ("Standard", "Front", 6.0, "BK7", 80.0),
        ("Standard", "Back", 40.0, "AIR", -80.0),
        ("Aperture", "Stop", 90.0, "AIR", 0.0),
        ("Image", "Image", 0.0, "AIR", 0.0),
    ]
    rows: list[SurfaceRow] = []
    for index, (surface, name, thickness, glass, rc) in enumerate(specs):
        if element and at_index == index:
            surface = element
        rows.append(
            SurfaceRow(
                label=str(index),
                surface=surface,
                name=name,
                rc=rc,
                thickness=thickness,
                diameter=30.0 if index < 4 else 20.0,
                glass=glass,
                axis_move=1.0,
            )
        )
    return rows


def _trace_counts(rows: list[SurfaceRow]) -> dict[str, object]:
    """Trace ``rows`` headless and return display counts both filter ways."""
    editor = _snapshot_editor(rows, dict(BASE_SETTINGS))
    trace_state = editor._resolved_trace_mode()
    detectors = sorted(editor._scene_detector_surface_indices(trace_state))
    _system, rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    paths = len(list(getattr(bundle, "ray_paths", []) or []) if bundle is not None else [])
    editor.show_clipped_rays_var.set(False)
    displayed_off = len(editor._iter_3d_scene_ray_records(rays=rays, scene_bundle=bundle))
    editor.show_clipped_rays_var.set(True)
    displayed_on = len(editor._iter_3d_scene_ray_records(rays=rays, scene_bundle=bundle))
    return {
        "use_nonseq": bool(trace_state.get("use_nonseq")),
        "detectors": detectors,
        "paths": int(paths),
        "displayed_off": int(displayed_off),
        "displayed_on": int(displayed_on),
        "terminal_index": len(rows) - 1,
    }


def run_checks(*, trials: int = 16, seed: int = 20260604) -> tuple[bool, list[str]]:
    """Return ``(passed, notes)`` after exercising all invariants headless."""
    notes: list[str] = []
    passed = True

    def _check(ok: bool, message: str) -> None:
        nonlocal passed
        notes.append(("PASS " if ok else "FAIL ") + message)
        if not ok:
            passed = False

    # Sanity: a clean lens shows its rays by default.
    base = _trace_counts(_lens_rows())
    _check(base["displayed_off"] > 0, f"clean lens displays rays (displayed_off={base['displayed_off']})")
    _check(
        base["displayed_on"] == base["paths"] and base["paths"] > 0,
        f"clean lens: no silent drop (on={base['displayed_on']} paths={base['paths']})",
    )

    # Regression guard: beam splitter on the terminal Image surface.
    terminal_index = base["terminal_index"]
    bs_terminal = _trace_counts(_lens_rows("Beam Splitter", terminal_index))
    _check(
        terminal_index in bs_terminal["detectors"],
        f"terminal beam splitter keeps detector role (detectors={bs_terminal['detectors']})",
    )
    _check(
        bs_terminal["displayed_off"] > 0,
        f"terminal beam splitter shows forward rays by default (displayed_off={bs_terminal['displayed_off']})",
    )
    _check(
        bs_terminal["use_nonseq"],
        "beam splitter forces non-sequential (North Star)",
    )

    # Random element along the path — rays must never vanish silently.
    rng = random.Random(seed)
    positions = list(range(1, terminal_index + 1))  # rows 1..terminal (Object stays at 0)
    for trial in range(trials):
        element = rng.choice(RANDOM_ELEMENT_TYPES)
        at_index = rng.choice(positions)
        counts = _trace_counts(_lens_rows(element, at_index))
        label = f"trial {trial}: {element}@S{at_index}"
        _check(counts["paths"] > 0, f"{label} traces rays (paths={counts['paths']})")
        _check(
            counts["displayed_on"] == counts["paths"],
            f"{label} no silent drop (on={counts['displayed_on']} paths={counts['paths']})",
        )
        # Any element on the terminal row must keep that row a detector.
        if at_index == terminal_index:
            _check(
                terminal_index in counts["detectors"],
                f"{label} terminal stays detector (detectors={counts['detectors']})",
            )

    return passed, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260604)
    args = parser.parse_args()
    passed, notes = run_checks(trials=args.trials, seed=args.seed)
    for note in notes:
        print(note)
    print("RESULT:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
