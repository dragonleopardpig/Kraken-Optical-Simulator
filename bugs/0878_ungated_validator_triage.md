# 0878 -- triaging the ungated validators: eight repaired, eight gated

Follow-up to 0877, which found that **178 of KrakenOS's 817 validators are in no penta phase** and
that a sample of 18 contract-style ones ran 12 pass / 6 fail. This is the triage of those six,
plus the four more that the same root cause was hiding.

**Verdict: every one was rot or a validator-side bug. None was an optics regression.**

## The toolbar and menu claims (4 checks)

| claim | what actually happened |
|---|---|
| "the View row exposes a Ray count synced to `ray_count_var`" | **bugs/0093 deleted it on purpose** -- it duplicated the Live Controls entry and both bound `ray_count_var`. The check now asserts the Live Controls panel owns it (`live_labeled_combo(..., "Ray count", "ray_count_var", ..., sync_fields=True)`) *and* that the toolbar keeps no duplicate (`_open3d_toolbar_ray_count_entry = None`) |
| "the View row can hide side panels" | they collapse from their **own headers** now, with an edge arrow (`▶`/`◀`) to bring each back |
| "Import Lens STEP..." | renamed "Import Imaging Lens STEP..." |
| "Accept STEP Placement" | moved into the Scene Components panel (same move 0877 found for the promote button) |

## The right-click parity claims (3 checks)

`_show_surface_function_context_menu` no longer builds the verbs inline: **bugs/0619**
consolidated every CAD/Place/Orient verb into one `append_element_context_actions`, which the
right-click menu *and* the Scene Components tree both call. The contract now spans the handler
plus the builder it delegates to, and all three checks pass untouched.

## The penta prism claims (3 checks) -- conventions, not physics

This one deserved the most care, because "30 of 31 rays miss the detector" reads like a real
break. It is not:

- the **face tuple** `("F005","F003","F004","F006")` became `("F005","F004","F003","F006")`: the
  two *internal reflection* faces swapped labels when the planar-face clustering renumbered them.
  A ray must strike them in a fixed geometric order whatever they are called, so the check now
  pins the **shape** -- one path for every ray, entry face, two *distinct* internal reflections,
  exit face;
- **`missed_detector` instead of `escaped`**: the detector-miss work made a miss *visible*
  instead of silently leaving the scene. A 1 mm image diameter cannot catch a 10 mm collimated
  beam, so 30 of 31 rays miss **by construction**. What must not happen -- a ray absorbed or
  stopped inside the prism -- is now what the check forbids, plus at least one ray landing;
- the **exit along −Y**: the port-anchored pose solution faces **+Y**, and
  `validate_vendor_prism_42779` independently agrees (its runtime trace lands at y = +52.5). The
  old assertion pinned a sign. What a penta prism actually guarantees is a constant **90°
  deviation with collimation preserved**, whichever way the solved pose faces -- so that is what
  is measured now (`spread < 1e-4`, `|exit · launch| < 1e-4`).

## The detector-filter RuntimeError -- one bug, five validators

`validate_phase8_field_contract` died with
`RuntimeError: No detector output or terminal path filter found` on a scene whose detector works
perfectly (`validate_interferogram_detector_accumulation` gets a coherent detector and
`visibility=1` on the *same* layout).

Measured side by side:

```
STALE: [... 'Output: Reflect path', 'Output: Transmit path', 'Terminal: S11 Aperture: ...']
FRESH: [... 'Output: Detector output port', ... 'Terminal: S13 Detector: Path 4 aperture pair']
APP  : Output: Detector output port
```

The call site asked for the path filter **before** handing over the dense retrace's records, so
`_preferred_output_or_terminal_filter` read the editor's stale single-arm records -- where the
recombined detector path does not exist yet. Five validators shared the bug; the two that already
passed `ray_records` were the two that worked. All five now compute the records first.

## Gated

`run_checks()` added to all eight, registered as **penta phases 656-663**, gate green.

| phase | validator |
|---|---|
| 656 | `validate_open3d_toolbar_layout` |
| 657 | `validate_open3d_row_actions_parity` |
| 658 | `validate_2d_3d_projection_sync` |
| 659 | `validate_phase8_field_contract` |
| 660 | `validate_coherent_detector_modes` |
| 661 | `validate_diffraction_detector` |
| 662 | `validate_detector_sampling_stability` |
| 663 | `validate_gaussian_detector_recombination` |

## Left open

`validate_ui_modular_maintainability` fails on an **aspirational line budget**
(`open3d_inspector.py` is 26 239 lines against a budget of 900), not on rot. It is not gated and
should not be until the budget is either met or rewritten.

`validate_fast_contracts` is itself a meta-runner of ungated validators. With the two above fixed
it still reports failing targets: `open3d-live`, `open3d-lens-step-face-pick`,
`five-penta-with-lens-layout`, `cad-scene-cache`, `step-analytic-import`,
`launch-origin-within-object-aperture`. Those are the next batch.
