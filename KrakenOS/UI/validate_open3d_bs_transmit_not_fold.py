#!/usr/bin/env python3
"""Display-free regression for bugs/0093: a beam splitter's TRANSMITTED branch is a
refractive pass-through, NOT a deliberate fold.

`ray_path_has_non_refractive_steering` decides whether a ray is a deliberately
folded branch (a beam-splitter reflection, fold mirror, TIR, grating) -- such rays
stay visible with "Show Clipped Rays" OFF. The token list matched a bare "split",
which also matched the TRANSMIT event_type "split_transmit", so a ray that merely
passed straight through the splitter was tagged as a fold and shown UNCONDITIONALLY.
That is why a transmit ray that missed the detector could never be hidden (the
user's "still show diverging rays ... those are missed rays"). The REFLECTED branch
("split_reflect") must still count (it is a real authored fold).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_bs_transmit_not_fold

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from types import SimpleNamespace


def _ev(event_type: str, surface_name: str = "Beam Splitter"):
    return SimpleNamespace(
        event_kind="surface", event_type=event_type, interaction_model="", surface_name=surface_name
    )


def _path(*event_types: str):
    return SimpleNamespace(events=[_ev(t) for t in event_types])


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.scene_geometry import ray_path_has_non_refractive_steering

    failures: list[str] = []
    cases = [
        # (label, path, expected_steered)
        ("split_transmit straight-through", _path("transmission", "split_transmit", "refraction"), False),
        ("split_reflect (beam-splitter fold)", _path("split_reflect"), True),
        ("plain mirror reflection", _path("reflection"), True),
        ("TIR fold", _path("tir"), True),
        ("grating diffraction", _path("diffraction"), True),
        ("pure refraction chain", _path("refraction", "transmission", "refraction"), False),
        # the surface NAME alone ("Beam Splitter") must not make a refracted ray a fold
        ("refraction at a surface named 'Beam Splitter'", _path("refraction"), False),
    ]
    for label, path, expected in cases:
        got = bool(ray_path_has_non_refractive_steering(path))
        if got != expected:
            failures.append(f"FAIL: {label}: steered={got}, expected {expected}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0093 beam-splitter transmit is not a fold")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] beam-splitter TRANSMIT is a refractive pass-through, not a fold (bugs/0093)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
