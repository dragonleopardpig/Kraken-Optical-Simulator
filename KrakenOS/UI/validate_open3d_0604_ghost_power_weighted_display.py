"""Guard for bugs/0604 — re-split ghost branches draw at power-weighted brightness.

flag_20260810_164247_396: "still have some stray rays at detector". Measured: 256 of the
265 on-sensor arrivals were the 2^8 reflect/transmit combinations of an 8-deep TIR
ladder inside the S6 beam splitter — real stray light carrying ~0.3% power each, drawn
at the same full brightness as the image-forming paths (~250x exaggeration).

Fix: `_ray_branch_power_display_weight(branch_path, branch_power)` multiplies the ray
line opacity in BOTH scene draw loops. Contract:

  A  Scope — the root path and first-generation splitter arms are NEVER faded
     (weight 1.0 regardless of power), so dim sources are not dimmed further.
  B  Fade — re-split branches fade below 5% power, monotone, floored at 0.15, and
     quantized to the {1.0, 0.55, 0.3, 0.15} buckets (bugs/0223 merged-actor grouping
     keys on exact opacity).
  C  Wiring — both draw loops in open3d_scene_refresh multiply the style opacity by
     the weight.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0604_ghost_power_weighted_display
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    weight = ThreeDSceneToolsMixin._ray_branch_power_display_weight

    # ------------------------------------------------------------------- A: scope
    scope_cases = [
        ("", 0.001, 1.0, "root path (empty lineage)"),
        (None, 0.0001, 1.0, "root path (no lineage)"),
        ("S6:S6/reflect", 0.001, 1.0, "first-generation arm"),
    ]
    for lineage, power, expected, label in scope_cases:
        got = weight(lineage, power)
        if got != expected:
            ok = False
            notes.append(f"FAIL: A (bugs/0604): {label} weight {got} != {expected} — dim sources get dimmed")
    if ok:
        notes.append("PASS: A: root and first-generation branches are never faded")

    # ------------------------------------------------------------------- B: fade
    resplit = "S6:S6/reflect -> S6:S6/transmit"
    fade_ok = True
    if weight(resplit, 0.25) != 1.0 or weight(resplit, 0.05) != 1.0:
        fade_ok = False
        notes.append("FAIL: B (bugs/0604): a strong re-split branch (>=5%) is faded")
    buckets = {weight(resplit, p) for p in (0.031, 0.01, 0.0031, 0.0001, 0.0)}
    if not buckets <= {1.0, 0.55, 0.3, 0.15}:
        fade_ok = False
        notes.append(f"FAIL: B (bugs/0604): weights {sorted(buckets)} not quantized to the buckets")
    series = [weight(resplit, p) for p in (0.05, 0.031, 0.01, 0.0031, 0.0001)]
    if any(a < b for a, b in zip(series, series[1:])):
        fade_ok = False
        notes.append(f"FAIL: B (bugs/0604): fade not monotone in power: {series}")
    if weight(resplit, 0.0031) > 0.3 or weight(resplit, 0.0001) < 0.15:
        fade_ok = False
        notes.append(
            f"FAIL: B (bugs/0604): the flagged 8-deep forest draws at "
            f"{weight(resplit, 0.0031)} — the 250x exaggeration is back (or below the floor)"
        )
    if fade_ok:
        notes.append("PASS: B: re-split ghosts fade with power, quantized, floored at 0.15")
    ok = ok and fade_ok

    # ------------------------------------------------------------------- C: wiring
    from KrakenOS.UI.services import open3d_scene_refresh as refresh_module

    src = inspect.getsource(refresh_module)
    applications = src.count("_ray_branch_power_display_weight")
    multiplies = src.count('float(style["line_opacity"]) * power_weight')
    if applications < 2 or multiplies < 2:
        ok = False
        notes.append(
            f"FAIL: C (bugs/0604): the power weight is applied in {applications} places / "
            f"multiplied {multiplies} times — a draw loop lost it and the ghost forest "
            "draws at full brightness there"
        )
    else:
        notes.append("PASS: C: both scene draw loops apply the power weight to ray opacity")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Ghost-power-weighted-display validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
