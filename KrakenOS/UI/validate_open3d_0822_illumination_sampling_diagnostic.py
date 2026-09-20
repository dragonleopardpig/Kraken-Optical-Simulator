"""Guard for bugs/0822 -- an illumination map that is mostly shot noise must SAY SO.

`source_illumination_map_data_from_samples` picks its grid from the hit count alone:

    bin_count = min(max(24, sqrt(N) * 3), 128)

At N = 10_000 hits that is a 128x128 grid -- 16_384 bins for 10_000 hits, well under one
hit per bin. Every feature such a map shows is Poisson noise, and a reader has no way to
tell it from physics. The MV-150 coaxial-LED case is exactly the shape that would be
believed: a fold-axis edge/centre ratio of <= 0.85 is a 15% dip, while 1 hit/bin carries
100% relative error. The dark edges there ARE real (penta 175/176 proved them on a real
non-seq LED->BS->Object trace), which is precisely why the map must distinguish itself --
the same readout would have shown "dark edges" on noise alone.

This is the silent-failure class the project already refuses elsewhere: a solve that
cannot deliver must alert rather than return a number.

Fix: the map now carries UNWEIGHTED per-bin `counts` alongside the power `hist`, and
`illumination_diagnostic_lines` renders two findings into the report -- a sampling verdict
(Poisson error from hits per lit bin, plus the ray count a 5%-error map would need) and a
flux ledger (input - hit - missed, and launched - hit - missed).

Checks (display-free, pure -- every function under test takes and returns plain data):
  A  the MV-150 shape (10k hits on a 128x128 grid) WARNS, names the hits per lit bin,
     says the structure is not physical, and recommends a concrete ray count;
  B  a well-sampled map does NOT warn but still prints its numbers -- silence is never
     how this reports a clean result;
  C  the verdict reads COUNTS, not power: one bin carrying enormous weight does not buy
     a sparse map a passing grade;
  D  the flux ledger catches both a power leak and a ray leak, and names the shortfall;
  E  a ledger that closes says so, with the terms, rather than staying quiet;
  F  the threshold is bracketed on both sides rather than tested on its edge;
  G  empty and malformed input degrade to "not available" instead of a fabricated verdict;
  H  the real binning path actually emits `counts`, shaped like the power histogram.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0822_illumination_sampling_diagnostic
"""

from __future__ import annotations

import numpy as np


def _map_with_counts(counts: np.ndarray) -> dict[str, object]:
    """A map_data dict carrying only what the sampling diagnostic reads."""
    return {"counts": np.asarray(counts, dtype=float)}


def _uniform_counts(lit_bins: int, hits_per_bin: float, total_bins: int) -> np.ndarray:
    """`lit_bins` bins each holding `hits_per_bin`, padded with empty bins."""
    counts = np.zeros(int(total_bins), dtype=float)
    counts[: int(lit_bins)] = float(hits_per_bin)
    return counts


def _records(
    *,
    input_power: float,
    hit_power: float,
    missed_power: float,
    launched: int,
    hit_rays: int,
    missed_rays: int,
) -> list[dict[str, object]]:
    return [
        {
            "source_id": "S1",
            "source_name": "LED",
            "input_power": input_power,
            "hit_power": hit_power,
            "missed_power": missed_power,
            "launched_rays": launched,
            "hit_rays": hit_rays,
            "missed_rays": missed_rays,
        }
    ]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.source_illumination_analysis import (
        ILLUMINATION_FLUX_LEDGER_WARN,
        ILLUMINATION_TARGET_HITS_PER_BIN,
        ILLUMINATION_UNDERSAMPLED_HITS_PER_BIN,
        illumination_diagnostic_lines,
        illumination_flux_ledger,
        illumination_sampling_diagnostic,
        source_illumination_map_data_from_samples,
    )

    # ---- A: the MV-150 shape -- 10k hits spread over a 128x128 grid ----------------------------
    # 16_384 bins; say 6_000 of them catch the beam, carrying 10_000 hits between them.
    mv150 = _map_with_counts(_uniform_counts(6_000, 10_000 / 6_000, 128 * 128))
    diag = illumination_sampling_diagnostic(mv150, launched_rays=20_000)
    ok(diag["available"] is True, "A1: a map with hits produces a verdict at all")
    ok(bool(diag["undersampled"]),
       f"A2: 1.67 hits per lit bin is flagged undersampled (got {diag['mean_hits_per_lit_bin']:.3g})")
    ok(float(diag["relative_error"]) > 0.5,
       f"A3: relative error exceeds 50% at that density (got {float(diag['relative_error']):.3g})")
    ok("recommended_rays" in diag and int(diag["recommended_rays"]) > 20_000,
       f"A4: a concrete larger ray count is recommended (got {diag.get('recommended_rays')})")

    lines = illumination_diagnostic_lines(map_data=mv150, launched_rays=20_000)
    blob = "\n".join(lines)
    ok(any(line.startswith("WARNING:") for line in lines),
       "A5: the report line is a WARNING, not a footnote")
    ok("shot noise" in blob,
       "A6: the warning names the cause -- shot noise")
    ok("NOT physical" in blob,
       "A7: it states plainly that structure below the noise is not physical")
    ok(str(int(diag["recommended_rays"])) in blob,
       "A8: and carries the recommended ray count into the text the user reads")
    # The heatmap dialog holds a map but no records; the records path must reach
    # the same number, and neither route available must still give usable advice.
    via_records = "\n".join(illumination_diagnostic_lines(
        map_data=mv150,
        records=_records(input_power=1.0, hit_power=1.0, missed_power=0.0,
                         launched=20_000, hit_rays=20_000, missed_rays=0),
    ))
    ok(str(int(diag["recommended_rays"])) in via_records,
       "A9: the launch count summed from records reaches the same recommendation")
    blind = "\n".join(illumination_diagnostic_lines(map_data=mv150))
    ok("WARNING:" in blind and "x more rays" in blind and "Launch about" not in blind,
       f"A10: with no launch count known the advice degrades to a multiplier, not a fake total")

    # ---- B: a well-sampled map reports its numbers rather than going quiet ----------------------
    good = _map_with_counts(_uniform_counts(4_096, 500.0, 128 * 128))
    good_diag = illumination_sampling_diagnostic(good, launched_rays=4_000_000)
    ok(not good_diag["undersampled"],
       f"B1: 500 hits per lit bin passes (got {good_diag['mean_hits_per_lit_bin']:.4g})")
    good_lines = illumination_diagnostic_lines(map_data=good, records=None)
    ok(len(good_lines) == 1 and not good_lines[0].startswith("WARNING:"),
       "B2: a clean map still emits exactly one line -- silence is not the clean signal")
    ok("Sampling adequate" in good_lines[0] and "500" in good_lines[0],
       f"B3: and that line carries the measured density (got {good_lines[0]!r})")

    # ---- C: the verdict reads COUNTS, never power ----------------------------------------------
    # Same sparse map; the power histogram is irrelevant to Poisson error, and a single
    # enormous weight must not buy a passing grade.
    sparse_but_bright = dict(mv150)
    sparse_but_bright["hist"] = np.full((128, 128), 1e9, dtype=float)
    sparse_but_bright["total_power"] = 1e12
    bright_diag = illumination_sampling_diagnostic(sparse_but_bright, launched_rays=20_000)
    ok(bool(bright_diag["undersampled"]),
       "C1: huge per-bin POWER does not rescue a map with 1.67 rays per lit bin")
    ok(float(bright_diag["mean_hits_per_lit_bin"]) == float(diag["mean_hits_per_lit_bin"]),
       "C2: the density is identical to the un-weighted case -- power was never read")

    # ---- D: the flux ledger catches a leak ------------------------------------------------------
    leaky = _records(input_power=1.0, hit_power=0.4, missed_power=0.2,
                     launched=1_000, hit_rays=400, missed_rays=200)
    ledger = illumination_flux_ledger(leaky)
    ok(not ledger["closes"], "D1: a ledger missing 40% of the power does not close")
    ok(abs(float(ledger["power_residual"]) - 0.4) < 1e-12,
       f"D2: the shortfall is measured, not estimated (got {ledger['power_residual']!r})")
    ok(int(ledger["ray_residual"]) == 400,
       f"D3: the ray shortfall is counted exactly (got {ledger['ray_residual']!r})")
    leak_lines = illumination_diagnostic_lines(map_data=None, records=leaky)
    leak_blob = "\n".join(leak_lines)
    ok(sum(1 for line in leak_lines if line.startswith("WARNING:")) == 2,
       f"D4: BOTH the ray and power leaks are reported (got {len(leak_lines)} lines)")
    ok("unaccounted" in leak_blob,
       "D5: the wording names the missing flux as unaccounted, not merely 'lost'")

    # ---- E: a closing ledger says so ------------------------------------------------------------
    clean = _records(input_power=1.0, hit_power=0.7, missed_power=0.3,
                     launched=1_000, hit_rays=700, missed_rays=300)
    clean_ledger = illumination_flux_ledger(clean)
    ok(clean_ledger["closes"] is True, "E1: input = hit + missed closes the ledger")
    clean_lines = illumination_diagnostic_lines(map_data=None, records=clean)
    ok(len(clean_lines) == 1 and clean_lines[0].startswith("Flux ledger closes"),
       f"E2: closure is stated rather than implied by silence (got {clean_lines!r})")

    # ---- F: the threshold is bracketed on both sides --------------------------------------------
    below = illumination_sampling_diagnostic(
        _map_with_counts(_uniform_counts(100, ILLUMINATION_UNDERSAMPLED_HITS_PER_BIN - 0.5, 200))
    )
    above = illumination_sampling_diagnostic(
        _map_with_counts(_uniform_counts(100, ILLUMINATION_UNDERSAMPLED_HITS_PER_BIN + 0.5, 200))
    )
    ok(bool(below["undersampled"]) and not bool(above["undersampled"]),
       "F1: 9.5 hits/bin warns and 10.5 does not -- the threshold bites in both directions")
    ok(0.0 < ILLUMINATION_UNDERSAMPLED_HITS_PER_BIN < ILLUMINATION_TARGET_HITS_PER_BIN,
       "F2: the warn threshold is a real density below the target density")
    ok(0.0 < ILLUMINATION_FLUX_LEDGER_WARN < 1.0,
       "F3: the ledger tolerance is a real fraction")
    ok(abs(ILLUMINATION_TARGET_HITS_PER_BIN - 1.0 / 0.05**2) < 1e-9,
       "F4: the target density is exactly the 5%-relative-error count, not a round guess")

    # ---- G: malformed input degrades safely -----------------------------------------------------
    empty = illumination_sampling_diagnostic(_map_with_counts(np.asarray([])))
    ok(empty["available"] is False and empty["undersampled"] is False,
       "G1: a map with no bins reports unavailable, never a verdict")
    all_zero = illumination_sampling_diagnostic(_map_with_counts(np.zeros(64)))
    ok(all_zero["available"] is False,
       "G2: a grid where no bin was hit reports unavailable rather than dividing by zero")
    ok(illumination_diagnostic_lines(map_data=None, records=None) == [],
       "G3: nothing measured produces no lines at all")
    ok(illumination_flux_ledger([])["available"] is False,
       "G4: an empty record list has no ledger to close")
    no_counts = illumination_sampling_diagnostic({"hist": np.ones((8, 8))})
    ok(no_counts["available"] is False,
       "G5: a map_data lacking counts is unavailable, not silently judged from power")

    # ---- H: the real binning path emits counts --------------------------------------------------
    rng = np.random.default_rng(0)
    n = 5_000
    samples = {
        "x": rng.normal(0.0, 3.0, n),
        "y": rng.normal(0.0, 3.0, n),
        "weights": np.ones(n, dtype=float),
    }
    real_map = source_illumination_map_data_from_samples(samples)
    ok("counts" in real_map, "H1: the production binning path carries per-bin counts")
    ok(np.asarray(real_map["counts"]).shape == np.asarray(real_map["hist"]).shape,
       "H2: counts and the power histogram share a grid")
    ok(abs(float(np.sum(real_map["counts"])) - float(n)) < 1e-9,
       f"H3: every hit is counted exactly once (got {float(np.sum(real_map['counts']))})")
    real_diag = illumination_sampling_diagnostic(real_map, launched_rays=n)
    ok(real_diag["available"] is True,
       "H4: and the diagnostic reads that real map without further plumbing")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0822 illumination-sampling-diagnostic validation PASSED")
        return 0
    print("0822 illumination-sampling-diagnostic validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
