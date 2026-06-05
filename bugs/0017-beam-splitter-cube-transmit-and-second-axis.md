# 0017 — Beam-splitter cube blocks the transmitted beam; reflected branch has no optical axis

**Status:** Fixed (2026-06-05).
**Component:** Open 3D inspector — the non-sequential output-port follower
(`build_optical_solid_output_port_pose_overrides`,
`KrakenOS/UI/nonseq_output_ports.py`) and the traced-optical-axis builder
(`Kraken3DInspector._optical_axis_records_for_3d`,
`KrakenOS/UI/open3d_inspector.py`).
**Reported via:** in-app recorder, follow-up to bug 0016. **Repro bundles are
gitignored**, so the evidence below is transcribed here. Saved repro
prescription: `attachment/machine_vision_150mm_measured_test.py` (8 surfaces; S6
is a promoted beam-splitter cube, BK7, mesh z≈200–225; the imaging lens datums
S1–S5 sit at z≈268–317; the Image plane S7 is authored at its real station
z≈665).

## Symptoms (user's words)

> ray reflected and exit the surface not obeying physics. The ray transmitting
> stop right at the imaging lens entrance.

and a paired request:

> please also make sure the 2nd beam path of beam splitter has new optical axis
> auto generated, this is supposed already in the code but please check and
> confirm after your test.

Two facets:

- **Facet A** — the transmitted beam dies at the cube; nothing reaches the
  imaging lens behind it.
- **Facet B** — the reflected beam path (the beam splitter's second output) gets
  no optical-axis guide of its own.

## Root cause (confirmed 2026-06-05, headless)

### Facet A — an inferred straight-through exit snapped the Image onto the cube

Promotion defaults every cube face to Transmit/Port with `port_role:'Auto'`
(bug 0016's contract — the user authors only the special faces, here just the
45° Beam Splitter). The cube's straight-through exit face (F003, side Right /
+Z normal) is therefore *inferred* — not user-authored — as an Output Port.

`build_optical_solid_output_port_pose_overrides` treats any optical-solid output
face as an exit frame onto which it repositions the downstream rows (so a folded
prism drags its follower lens / image onto the new optical path). For this cube
that downstream row is the **Image plane**, and the inferred exit frame sits at
the cube's +Z face (world z≈265) — *in front of* the imaging-lens entrance
(≈268). The Image plane was snapped there, so it intercepted every transmitted
ray at the cube face and the rays "stopped right at the imaging lens entrance".

Headless reproduction (`machine_vision_150mm_measured_test.py`):

| quantity | pre-fix | post-fix |
|---|---|---|
| Image plane world z | **265.0** (snapped to cube exit) | **665.0** (authored station) |
| lens datums S1–S5 hit by rays | **none** | **S1,S2,S3,S4,S5** |
| max ray end-z | **265.0** (dies at cube) | **665.0** (reaches image) |

This is not a physics error in the trace — it is a *placement* error: the
output-port follower moved a downstream plane onto the path. A purely inferred
exit that runs **straight through along the incoming axis** does not fold the
beam, so the downstream rows already lie on that axis at their authored spacing;
repositioning them is wrong.

### Facet B — a single "chief" ray left the reflected branch with no axis

`_optical_axis_records_for_3d` drew the global `axis:global` (+Z) guide, then
built traced "Optical Axis N" guides from a **single** chief ray path
(`chief = min(physical_paths, key=_path_score)`). A beam splitter fans the
central ray into an on-axis **transmit** branch (already covered by `axis:global`)
*and* a folded **reflect** branch. The transmit branch is the most central, so it
won the chief score — and its on-axis segment is filtered out as collinear — so
the reflected beam path produced **no** traced axis at all (`traced = 0`).

## Fix

### Facet A — don't reposition rows onto a straight-through inferred exit

New helper `_exit_frame_is_on_axis_passthrough`
(`nonseq_output_ports.py:1053`): true when an exit frame is collinear,
codirectional, and laterally centered on the incoming optical axis — i.e. it
neither bends nor offsets the beam. The follower loop
(`nonseq_output_ports.py:1150`) now skips repositioning when the frame source is
`inferred_output:*` **and** the exit is such a straight-through passthrough, so
the Image/Object rows keep their authored stations. **Folded** inferred exits,
**explicit** user-authored output ports, and **physics-traced** exits
(`physics_exit_trace`, e.g. the Dove prism) are untouched and still drive the
follower workflow. (Guarded both ways: the new test asserts a folded inferred
exit still repositions the Image.)

### Facet B — one traced axis per distinct fold direction

`_optical_axis_records_for_3d` (`open3d_inspector.py:7491`) now walks **every**
steered path in centrality order and keeps one representative segment per
distinct fold **direction** instead of a single chief:

* `_segment_is_genuine_fold` skips segments collinear with the global +Z guide
  (transverse deviation < 0.1 ≈ 5.7°) — `axis:global` already represents that
  direction, so on-axis field spread on the transmit branch does not spawn a
  cloud of near-duplicate guides.
* remaining folds are clustered by angular proximity
  (`fold_merge_cos = cos(15°)`), so the reflected branch's own field rays (a few
  degrees apart) collapse to a single axis while a genuinely different fold (a 90°
  splitter reflection) stays separate.

The reflected branch now reliably earns `Optical Axis 2` (direction +X for this
cube) even though the transmit branch wins the chief score; the on-axis transmit
branch stays represented by `axis:global` only.

## Tests

* **Display-free unit** —
  `KrakenOS/UI/validate_open3d_beam_splitter_transmit_and_second_axis.py`
  (`python -m KrakenOS.UI.validate_open3d_beam_splitter_transmit_and_second_axis`).
  Asserts, CAD-free: (Facet A) a straight-through inferred exit leaves a
  downstream Image row put while a folded inferred exit still repositions it
  (the fix is surgical, not a blanket disable); (Facet B) a synthetic
  beam-splitter bundle whose on-axis transmit branch wins the chief score still
  yields exactly one folded reflected axis (+X), and the reflected branch's
  field-angle spread collapses to that single axis. When the CAD cache is present
  it also re-traces the user's real cube scene: Image plane stays at z≈665,
  transmit rays reach S1–S5, max end-z≈665, and exactly one folded reflected axis
  is auto-generated. Verified fail-before / pass-after by stashing the two
  source fixes (pre-fix: Image snapped to 265, no lens hit, `traced=0`).
* **Reference validator repair** —
  `KrakenOS/UI/validate_open3d_optical_axis_guides.py` could not run (its fake
  inspector never seeded the rays-off cache attributes the cache feature later
  introduced, so `_optical_axis_records_for_3d` raised `AttributeError` before
  reaching the logic under test). Seeded `_cached_traced_axis_signature` /
  `_cached_traced_axis_records` so it exercises the axis-selection logic again;
  its centered-vs-folded assertions pass with the Facet-B change.
* **Regression / end-to-end** — `Phase 26`
  (`phase_26_beam_splitter_transmit_and_second_axis`) in
  `validate_open3d_penta_telescope_comprehensive.py` wraps the `run_checks()`.
  Gate baseline regenerated (`tools/penta_validator_baseline.json`).
* **Visual** — the real `machine_vision_150mm_measured_test` scene was rendered
  off-screen (full retrace under Xvfb, `show_rays`) in two framed views and
  inspected by eye on 2026-06-05:
  * **XZ plane** (camera on +Y, +X up) — the beam-splitter cube (small square
    with its 45° splitter line) sits at the left, the imaging-lens barrel
    immediately behind it, and the image-plane detector at the far right. The
    ray bundle passes **through** the cube, **through** the lens stack, and
    converges on the image plane — Facet A, the transmit no longer dies at the
    cube face. A second bright branch peels off the cube — the reflected path.
  * **Isometric** — two distinct ray branches and two optical-axis guides leave
    the cube: the transmit branch focuses into the image-plane detector along
    the global +Z axis, while the reflected branch carries its own guide.
  The traced-axis records confirm exactly one extra guide,
  `Optical Axis 2` with `segment_direction = [1, 0, 0]` (+X), plus
  `Optical Axis` (global +Z). Fit bounds span z≈200→701 (image authored at 665);
  6 row actors + 2 promoted-cube step actors render, so the bodies are present.
