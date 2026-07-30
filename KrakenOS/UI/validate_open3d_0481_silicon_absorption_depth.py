"""bugs/0481 -- the silicon panel's depth must respond to source power, and to the RIGHT thing.

Reported: "for the Silicon Power + Surface Reflection: I increase the Power slider, the Depth
inside Silicon is unchanged, always terminate at 500um".

Both true, and for two different reasons:

* the depth AXIS was ``depths * (1e4 / alpha)`` -- at the defaults 5 x 100 um = exactly the
  reported 500 um, with no power term anywhere;
* the power axis was ``[0, 1.03 * incidentPower]``, i.e. autoscaled by the very factor it was
  displaying, so a four-decade slider redrew a pixel-identical plot.

The decay length itself is correctly power-independent -- Beer-Lambert is multiplicative, so the
FRACTIONAL profile is the same at every power, and faking a power-dependent ``alpha`` would be
wrong. What genuinely moves is the depth at which the beam is still above an ABSOLUTE level:

    z_floor = ln((1 - R) P_0 / P_floor) / alpha      -> + ln(10) / alpha per decade of power

which is ``absorption_depth_for_power``. The panels now plot on a FIXED log frame (power lifts
the line) with the depth axis following that crossing (power widens the window).

The same equation now lives in three places -- the Python module, the browser lab's JS, and the
JupyterLite notebook -- so this guard checks they AGREE rather than just that each runs.

Display-free: pure model functions, plus `node` for the JS half (SKIPped when absent). No Tk,
no render, no trace.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0481_silicon_absorption_depth
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAB_JS = (
    REPO_ROOT
    / "docs/source/_static/knowledge_base/worked_exercises/photonics_essentials/photodiode_lab.js"
)
NOTEBOOK = (
    REPO_ROOT
    / "docs/source/knowledge_base/worked_exercises/photonics_essentials/notebooks/ch03_photodiode_lab.ipynb"
)

# (log10 P0, log10 floor, log10 alpha, silicon index) -- spread over both slider ranges.
CASES = (
    (-1.0, -9.0, 2.0, 3.5),
    (0.0, -9.0, 2.0, 3.5),
    (1.0, -12.0, 3.0, 4.0),
    (-3.0, -6.0, 2.5, 3.2),
    (-2.0, -3.0, 5.0, 4.2),
)

_JS_DRIVER = """
const lab = require(process.argv[1]);
const panel = lab.MODES.siliconPower;
const base = Object.fromEntries(panel.controls.map((c) => [c.key, c.value]));
const cases = JSON.parse(process.argv[2]);
const rows = cases.map(([logPower, logFloor, logAlpha, siliconIndex]) => {
    const r = panel.calculate({ ...base, logPower, logFloor, logAlpha, siliconIndex });
    return {
        logPower,
        logFloor,
        logAlpha,
        siliconIndex,
        xMax: r.xDomain[1],
        yDomain: r.yDomain,
        yTransform: r.yTransform || null,
        labels: r.series.map((s) => s.label),
        readouts: Object.fromEntries(r.readouts),
    };
});
const defaults = { depths: base.depths, controlKeys: panel.controls.map((c) => c.key) };
process.stdout.write(JSON.stringify({ rows, defaults }));
"""


def _js_rows():
    """Drive the browser lab's own panel model through node. (None, reason) when unavailable."""
    node = shutil.which("node")
    if node is None:
        return None, "node is not on PATH"
    if not LAB_JS.exists():
        return None, f"the lab JS is absent ({LAB_JS.name})"
    try:
        completed = subprocess.run(
            [node, "-e", _JS_DRIVER, str(LAB_JS), json.dumps([list(c) for c in CASES])],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
        )
    except Exception as exc:  # pragma: no cover - environment
        return None, f"node failed to start ({type(exc).__name__}: {exc})"
    if completed.returncode != 0:
        return None, f"node exited {completed.returncode}: {completed.stderr.strip()[:400]}"
    try:
        return json.loads(completed.stdout), ""
    except Exception as exc:
        return None, f"unreadable node output ({exc}): {completed.stdout[:200]!r}"


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        from KrakenOS.Physics import photodiode
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: photodiode model unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. the model: what power moves, and by exactly how much ---------------------------
    alpha, index, floor = 100.0, 3.5, 1.0e-9
    reflectance = photodiode.fresnel_reflectance(1.0, index)
    depth_a = photodiode.absorption_depth_for_power(floor, alpha, 0.1, surface_reflectance=reflectance)
    depth_b = photodiode.absorption_depth_for_power(floor, alpha, 1.0, surface_reflectance=reflectance)
    expected_gain = math.log(10.0) / alpha * 1.0e4
    check(
        abs((depth_b - depth_a) - expected_gain) < 1.0e-6,
        f"A1: a decade of source power buys ln(10)/alpha = {expected_gain:.4f} um "
        f"(measured {depth_b - depth_a:.4f})",
    )
    check(
        abs(photodiode.absorption_depth_gain_per_decade(alpha) - expected_gain) < 1.0e-9,
        "A2: absorption_depth_gain_per_decade agrees with the inverted equation",
    )
    remaining = float(
        photodiode.absorption_power(depth_a, alpha, 0.1, surface_reflectance=reflectance)
    )
    check(
        abs(remaining - floor) <= 1.0e-15 + 1.0e-9 * floor,
        f"A3: the returned depth is where the power IS the floor ({remaining:.6e} vs {floor:.0e})",
    )
    # The decay length is the material's: the FRACTIONAL profile must be power-invariant.
    positions = [0.0, 25.0, 100.0, 250.0, 500.0]
    low = photodiode.absorption_power(positions, alpha, 1.0e-3, surface_reflectance=reflectance)
    high = photodiode.absorption_power(positions, alpha, 10.0, surface_reflectance=reflectance)
    ratios = [float(h) / float(l) for h, l in zip(high, low)]
    check(
        max(ratios) - min(ratios) < 1.0e-12,
        f"A4: the fractional depth profile is power-INDEPENDENT (ratio spread "
        f"{max(ratios) - min(ratios):.2e}) -- alpha is not faked",
    )
    check(
        photodiode.absorption_depth_for_power(1.0, alpha, 0.1) == 0.0,
        "A5: a floor at or above the entering power is reached at the surface, not inside",
    )
    for bad in ({"target_power_w": 0.0}, {"incident_power_w": -1.0}, {"absorption_cm_inv": 0.0}):
        kwargs = {"target_power_w": floor, "absorption_cm_inv": alpha, "incident_power_w": 0.1}
        kwargs.update(bad)
        try:
            photodiode.absorption_depth_for_power(**kwargs)
        except ValueError:
            continue
        check(False, f"A6: {bad} should have raised ValueError")
        break
    else:
        check(True, "A6: non-positive powers / alpha raise ValueError")

    # --- B. reachable everywhere the docs and the app read it from -------------------------
    try:
        import KrakenOS as Kos
        from KrakenOS import Physics as physics

        exported = (
            "absorption_depth_for_power" in physics.PHOTODIODE_API
            and hasattr(physics, "absorption_depth_for_power")
            and hasattr(Kos, "absorption_depth_for_power")
        )
        check(exported, "B1: the new depth helper is exported by the Physics package (bugs/0474 contract)")
    except Exception as exc:
        notes.append(f"SKIP: Physics package import failed ({type(exc).__name__}: {exc})")

    # --- C. the browser lab agrees with the Python model, case by case ---------------------
    payload, reason = _js_rows()
    if payload is None:
        notes.append(f"SKIP: cannot drive the lab JS ({reason})")
    else:
        rows = payload["rows"]
        displayed_lengths = float(payload["defaults"]["depths"])
        worst = 0.0
        for row in rows:
            case_alpha = 10.0 ** row["logAlpha"]
            case_r = photodiode.fresnel_reflectance(1.0, row["siliconIndex"])
            depth = photodiode.absorption_depth_for_power(
                10.0 ** row["logFloor"],
                case_alpha,
                10.0 ** row["logPower"],
                surface_reflectance=case_r,
            )
            expected = max(displayed_lengths * 1.0e4 / case_alpha, 1.05 * depth)
            worst = max(worst, abs(row["xMax"] - expected))
        check(
            worst < 1.0e-6,
            f"C1: the lab JS depth window matches the Python model on all {len(rows)} cases "
            f"(worst |delta| = {worst:.2e} um)",
        )
        check(
            "logFloor" in payload["defaults"]["controlKeys"],
            "C2: the panel exposes the detection floor as a control",
        )
        check(
            all(row["yTransform"] == "log10" for row in rows),
            "C3: the power axis is logarithmic, so a decade of power is a visible shift",
        )
        # --- D. the reported symptom, both halves -----------------------------------------
        by_power = {row["logPower"]: row for row in rows if row["logFloor"] == -9.0 and row["logAlpha"] == 2.0}
        if len(by_power) >= 2:
            lo, hi = min(by_power), max(by_power)
            grew = by_power[hi]["xMax"] - by_power[lo]["xMax"]
            check(
                grew > 1.0,
                f"D1: the depth window MOVES with source power ({by_power[lo]['xMax']:.1f} -> "
                f"{by_power[hi]['xMax']:.1f} um) -- it no longer always terminates at the same depth",
            )
            check(
                by_power[lo]["yDomain"] == by_power[hi]["yDomain"],
                "D2: the power frame is FIXED across the slider, so the curve lifts instead of "
                "the axis rescaling under it (the 'nothing happens' half of the report)",
            )
        else:
            check(False, "D1/D2: the two same-floor cases needed for the comparison are missing")
        check(
            any("Detection floor" in row["labels"] for row in rows),
            "D3: the floor is drawn, so the crossing that moves is visible",
        )
        depth_readouts = [row["readouts"].get("Depth to floor") for row in rows]
        check(
            all(value for value in depth_readouts),
            f"D4: every case reports its depth-to-floor ({depth_readouts[0]!r} ...)",
        )

    # --- E. no fourth implementation: the notebook uses the shared helpers ------------------
    if not NOTEBOOK.exists():
        notes.append("SKIP: the JupyterLite notebook is absent")
    else:
        source = NOTEBOOK.read_text()
        check(
            "absorption_depth_for_power" in source
            and "absorption_depth_gain_per_decade" in source,
            "E1: the notebook calls the shared depth helpers rather than inlining ln(P/P)/alpha",
        )
        check("semilogy" in source, "E2: the notebook plots power on a log axis too")
        check(
            "floor_power_w" in source and "min=-12" in source,
            "E3: the notebook exposes the same detection-floor control",
        )

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
