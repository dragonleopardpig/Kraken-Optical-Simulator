# 0822 -- an illumination map that is mostly shot noise must SAY SO

Not a flag. This comes from reading optiland's NSQ `diagnostics.py`, which turns
"a detector whose map is pure shot noise" into an explicit warning rather than a
number the user has to know to distrust. KrakenOS had the same silent failure and
no equivalent.

## The bug

`source_illumination_map_data_from_samples` picks its grid from the hit count alone:

    bin_count = min(max(24, sqrt(N) * 3), 128)

That is a fine-looking rule and a trap: it grows the grid as fast as the samples,
so hits-per-bin stays roughly **constant and small** no matter how many rays you
launch. At any realistic ray budget the map lands near one hit per bin, and every
feature it shows is Poisson noise. Nothing in the readout said so.

This is the silent-failure class the project already refuses elsewhere: bugs/0594
established that a physical check must not sit below an early refusal, and the
no-silent-solve-failure rule says a solve that cannot deliver must alert rather
than return a number. A heatmap that cannot support its own structure is the same
defect wearing a colormap.

## Measured on the real MV-150 coaxial-LED scene

Running the production layout through `_trace_fov_hit_samples` at the shipped
8000-ray budget (`common_optical_layouts/machine_vision_150mm_coaxial_led.py`):

    traced 8000 rays -> 1726 FOV hits

    2-D heatmap:  124 x 124 bins, 1479 lit, 1.17 hits per lit bin
                  -> 92.6% relative Poisson error
                  -> needs ~343x more rays (~2.7M) for 5% error

**The 2-D map a user looks at for this scene is shot noise.** Any dark edge read
off it is not physical.

The shipped proof survives, because it never used that map. Penta phase 175
measures a **1-D** profile inside a `|perp| <= 5 mm` strip:

    1-D fold-axis profile: 255 hits over 13 bins = 19.6 hits/bin
                           -> 22.6% relative error
                           edge/centre = 0.617, asserted <= 0.85

A 38% dip against 22.6% noise holds, so penta 175's conclusion stands and the
MV-150 dark edges are real. But the validator's own comment claims 8000 rays give
"a wide margin", and 38-vs-23 is not wide. Worth knowing before that number is
trusted again.

One-dimensional binning concentrates the same rays into 13 bins instead of 15376.
That is the whole difference between the two results, and it is exactly what the
diagnostic now makes visible.

## It has cost triage time before

bugs/0596 reached the same verdict by hand, on a different scene: *"The map is shot
noise by construction: 294 object hits over a 16x16 grid spanning the +/-50 mm
auto-fitted extent (~6.3 mm bins, ~1.1 hits/bin). Sampling along X at y=0 gives
[0, 0, 0, 0, .33, .33, .33, .33, .67, .33, .33] -- half the FOV samples zero."*

That triage also tested two candidate fixes -- bin-count scaling by full/robust span,
and [p2, p98] pre-clipping -- and found **both left every metric byte-identical**.
Which is the point: the problem was never the extent or the clipping, it was the ray
budget, and nothing in the readout said so. One line of diagnostic would have named
it before any of that was tried.

## Fix

`source_illumination_map_data_from_samples` now also returns **unweighted** per-bin
`counts` beside the power `hist` -- Poisson error is set by how many rays landed,
never by how much power each carried, so a map with one enormous weight must not
pass. Three pure functions read it:

* `illumination_sampling_diagnostic(map_data, launched_rays=...)` -- hits per lit
  bin, relative error, and the concrete ray count a 5%-error map would need.
* `illumination_flux_ledger(records)` -- closes `input - hit - missed` on power
  and `launched - hit - missed` on rays. A residual means flux reached a terminal
  nothing books.
* `illumination_diagnostic_lines(...)` -- renders both into the report, ABOVE the
  per-source rows, so a reader who stops after the first screen has still seen
  whether the numbers below can be believed.

Thresholds are the standard Poisson argument, not taste: warn below **10 hits per
lit bin** (1/sqrt(10) ~= 32% error), target **400** (exactly 1/0.05^2, ~5% error),
ledger tolerance **5%** of input power.

A clean result still prints its numbers. Silence means nothing was measured, never
that everything is fine.

## Deliberately not done

The bin rule itself is left alone. Capping bins to keep density up would trade a
noisy map for a coarse one and silently change every existing heatmap; telling the
user what they are looking at is the smaller, truer change. Raising the MV-150
ray budget is likewise the user's call -- the diagnostic now names the number.

## Guard

`KrakenOS/UI/validate_open3d_0822_illumination_sampling_diagnostic.py`, penta phase
601. Display-free and pure: 36 checks over the MV-150 shape, a well-sampled map,
power-cannot-mask-sampling, both ledger leaks, a closing ledger, the threshold
bracketed on both sides, malformed input, and the real binning path emitting counts.
