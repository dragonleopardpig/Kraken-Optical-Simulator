# 0481 — the silicon power slider moved nothing, and the depth axis always ended at 500 um

Reported on the Chapter 3 photodiode lab:

> for the Silicon Power + Surface Reflection: I increase the Power slider, the Depth inside
> Silicon is unchanged, always terminate at 500um

Both halves are true, and they have different causes. One is an arithmetic accident, one is a
missing quantity, and neither is fixed by making absorption depend on power — that would be
wrong physics.

## Why it always ended at 500 um

`siliconAbsorptionPower` built its depth axis from the material alone:

    const absorptionLengthUm = 1e4 / alpha;               // alpha = 10 ** state.logAlpha
    const maximumDepthUm = state.depths * absorptionLengthUm;
    xDomain: [0, maximumDepthUm]

At the panel's defaults `logAlpha = 2` → α = 100 cm⁻¹ → 1/α = 100 um, and `depths = 5`, so the
window is **5 × 100 = exactly the reported 500 um**. There is no power term anywhere in it.

## Why moving the slider changed nothing at all

    yDomain: [0, 1.03 * incidentPower]

The power axis was autoscaled by the very factor it was displaying. Take `P0` from 1 mW to 10 W
and both the curve and its frame grow 10 000×, so the plot is **pixel-identical**: a four-decade
slider that redraws the same picture. Only the text readouts moved. The JupyterLite notebook had
the same shape — `ax.set_ylim(bottom=0)` with an autoscaled top.

## What is actually invariant, and what is not

The instinct "more power should reach deeper" is half a misconception and half a real effect, and
the panel was showing neither half.

Beer-Lambert is *multiplicative*: `P(z) = P_enter e^(−αz)`. The decay length `1/α` is a property
of the silicon, so the **fractional** profile is identical at every source power — 63.2 % of
whatever entered is gone by one absorption length, at 1 mW and at 10 W alike. Faking a
power-dependent α to make the plot respond would have been a lie, and the guard asserts it is not
happening (check A4: the ratio of the 10 W and 1 mW profiles is a constant to 0 parts in 1e12).

What *does* move with power is the depth at which the beam is still above some **absolute** level
— a detector noise floor, a damage threshold, a "fully absorbed" criterion. Inverting Equation
3.22 for depth:

    z_floor = ln((1 − R) P0 / P_floor) / α

which is logarithmic in power: every decade buys a further `ln(10)/α`. Measured at α = 100 cm⁻¹,
n = 3.5 (R = 30.9 %), floor = 1 nW:

    P0 = 0.1 W   ->  z_floor = 1805.40 um
    P0 = 1.0 W   ->  z_floor = 2035.65 um
    delta        =              230.26 um   ==  ln(10) / alpha  =  230.2585 um

So the honest answer to the report is: the decay length never was power-dependent and must not
become so, but the panel had no way to show the depth that *is* — and its own axis choices hid
even the power scaling it did model.

## Fix

**Physics** (`KrakenOS/Physics/photodiode.py`, exported through the package per bugs/0474):

* `absorption_depth_for_power(target, alpha, P0, surface_reflectance=)` — the inversion above.
  Returns `0.0` when the floor is already met at the entrance rather than a negative depth.
* `absorption_depth_gain_per_decade(alpha)` — `ln(10)/α`, the answer to "how much deeper does
  turning the power up actually get me?" without having to pick a floor first.

**Both panels** (browser JS lab and JupyterLite notebook):

* a **Detection floor** control, 1 pW … 1 mW, default 1 nW;
* the power axis is **logarithmic on a fixed frame** (floor/10 → the source slider's top, 10 W),
  so raising the source now *lifts* both curves inside a stationary window — the Fresnel loss
  becomes a constant vertical offset and α becomes the slope;
* the depth axis follows the floor crossing: `max(depths × 1/α, 1.05 × z_floor)`. The window
  therefore widens by 230 um per decade at the defaults, and no longer always ends at 500 um.
  `depths` is relabelled *minimum* displayed absorption lengths, and its range goes to 25 (the
  full four-decade dynamic range needs ln(10⁴·(1−R)/1e-9) ≈ 24 absorption lengths);
* the floor is drawn as its own series/line, with the crossing marked, and readouts for
  "Depth to floor", "Depth per power decade", and "Absorption length … (power-independent)";
* the panel note and the RST table now say which quantity is the material's and which is the
  beam's, so the misconception is answered in the text as well as the picture.

`powerLabel` also grew pW/nW/uW steps — it previously rendered a 1 nW floor as `1e-6 mW`.

## Guard

`KrakenOS/UI/validate_open3d_0481_silicon_absorption_depth.py`, penta **phase 388**,
display-free, 17 checks.

The same equation now lives in **three** places — the Python module, the lab's JS, and the
notebook — which is exactly how a model drifts. So the guard does not merely check that each
runs: it drives the *browser lab's own panel function* through `node` (the JS gained a
`module.exports` branch that is inert in a browser, where `module` is undefined) and compares its
depth window against the Python model across five parameter sets spanning both slider ranges —
**bit-exact, worst |Δ| = 0.00e+00 um** — and asserts the notebook calls the shared helpers rather
than inlining the formula a fourth time.

It also pins the reported symptom in both halves: D1 asserts the depth window *moves* with source
power (1895.4 → 2137.2 um), D2 asserts the power frame is *fixed* across the slider so the curve
lifts instead of the axis rescaling under it.

`node --check` passes on the lab JS; the patched notebook cell was executed headlessly under Agg
at 1 mW / 0.1 W / 10 W (window 1482 → 1990 → 2498 um, log y, fixed frame) and with the floor
above the entering power (the clamped path); 47/47 pytest, up from 40 — two new physics tests and
three new invalid-input cases.
