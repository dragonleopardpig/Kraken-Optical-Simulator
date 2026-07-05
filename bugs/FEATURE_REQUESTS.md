# Feature requests — captured backlog (not yet started)

User-requested features, jotted down for later design/implementation. Each notes the request verbatim,
the grounding scene/reference, and pointers to existing infrastructure to build on. These are FEATURES
(new capability), distinct from the numbered bug fixes.

Captured: 2026-07-05.

---

## FR-1 — 3-D Relative Illumination overlay ON the detector plane

**Request (user).** "The 39×39 mm MV150mm 1X with Cube BS (`attachment/machine_vision_150mm_test.py`)
has a dark side at LEFT and RIGHT (caused by the 55 mm side of the BS with the LED attached); the TOP
and BOTTOM (the 78 mm side) has no problem. Can we add an additional analysis overlay to the DETECTOR
for the Relative Illumination to illustrate this? The overlay shall illustrate the actual area,
visually showing bright/uniform illumination at the CENTER and DARK on LEFT and RIGHT — matching the
2-D graph-plotted version."

**What it is.** A spatial (2-D-over-area) relative-illumination heat-map rendered as an overlay on the
detector/image plane in the Open 3-D view, so the anisotropy (bright centre, dark left/right from the
55 mm BS aperture with the LED) is visible in situ on the sensor rectangle — not just as a separate
line/graph. Colours must agree with the existing 2-D RI analysis.

**Grounding.**
- Scene: `attachment/machine_vision_150mm_test.py` (39×39 mm MV150 1× + cube beam-splitter + LED on the
  55 mm face). The dark L/R vs uniform T/B is the phenomenon to visualise.

**Existing infrastructure to build on (verify before use — these are 2026-07-05 pointers).**
- 2-D RI already exists: `services/analysis_plot.py` `analysis_mode == "relative_illumination"`
  (~line 1906), titles "Relative Illumination" / "Wide-Field Relative Illumination Map" (~1728/2029);
  `layout_plot_controller.py` maps `"relative_illumination" -> "Illum"`. Reuse its sampling so the 3-D
  overlay and the 2-D plot share one RI computation (single source of truth for the colours).
- Detector overlay plumbing exists: `open3d_inspector.py` `show_detector_overlays_var` (~610),
  `show_detector_overlays=` (~1702), detector-carry rows (`_is_detector_carry_row`). The RI map would
  be a new detector overlay layer, gated by its own toggle, drawn on the sensor rectangle.

**Design sketch.** Sample RI over a grid on the detector/object FOV rectangle → build a coloured
texture / per-cell quad mesh → draw as a flat overlay on the detector plane (respecting the folded
pose, cf. bugs/0217/0220 detector placement) → shared colormap + legend with the 2-D plot.

**Open questions.** Grid resolution vs speed (ties into the trace-perf work, task #78); absolute vs
per-field normalisation; whether to key off the same detector-coverage FOV rectangle already drawn.

---

## FR-2 — Tolerance Analysis workflow

**Request (user).** "Often an optical designer needs to go through Analysis of Tolerance. I downloaded
a Zemax example: `attachment/How_to_perform_a_sequential_tolerance_analysis_Samples`. Can we design a
workflow on how to do Tolerance Analysis?"

**What it is.** A guided, end-to-end tolerance-analysis workflow (define tolerances → set the
compensator(s) + merit/criterion → run sensitivity + Monte-Carlo → read the sensitivity table +
statistical yield), modelled on the Zemax sequential tolerancing flow in the downloaded sample.

**Grounding.**
- Reference: `attachment/How_to_perform_a_sequential_tolerance_analysis_Samples` (+ `.zip`) — mine it
  for the canonical operand set (TWAV/TEDX/TETX/TFRN/…), default tolerance defaults, and the
  sensitivity + Monte-Carlo report layout to mirror.

**Existing infrastructure to build on (verify before use).**
- `ToleranceModelingMixin` + `capture_tolerance_monte_carlo_case_study_screenshots.py` (a Monte-Carlo
  case study already renders).
- `services/analysis_compute_workflow.py::_build_tolerance_merit_function` (~1234).
- Pose-tolerance machinery in `services/layout_scene_projection.py`: `_pose_tolerance_entries` (~1030),
  `_pose_tolerance_variant_assignments` (~1055), `_rows_with_pose_tolerance_assignment` (~1093),
  `_project_pose_tolerance_rows` (~1107); `services/layout_analysis_display.py::_current_tolerance_compare_view`.
- So the PIECES (pose tolerances, a merit function, Monte-Carlo variants) exist — the request is the
  glue: a discoverable, guided WORKFLOW that sequences them like the Zemax sample and reports results.

**Open questions.** Which tolerance operands to expose first; sensitivity vs full Monte-Carlo default;
where the workflow lives in the UI (a wizard/panel); compensator selection UX.

---

## FR-3 — Stray Light Analysis workflow

**Request (user).** "Same feature as [FR-2] but with Stray Light Analysis." — i.e. design a guided
workflow for stray-light analysis (ghost reflections, scatter, out-of-field/aperture-edge light).

**Grounding.** No Zemax sample was attached for this one; the flagged FR-1 scene (BS + LED, with the
55 mm-side darkening) is itself partly a stray/aperture-illumination phenomenon and could serve as a
first test case.

**Existing infrastructure to build on (verify before use).**
- Greenfield: no `stray_light` / `StrayLight` code exists today (grep found none) — this is the
  largest of the three.
- Adjacent building blocks: the non-sequential trace already supports coatings / beam-splitter /
  diffuse-scatter faces (see the promote path + `DiffuseScatter` / `Coating` face metadata), which is
  the physical basis for ghost + scatter paths. A stray-light workflow would drive multi-bounce
  non-seq traces and tally irradiance reaching the detector from non-nominal paths.

**Open questions.** Scope (ghost-only first, or scatter too?); how to seed/limit bounce depth; how to
report (stray irradiance map on the detector — overlaps FR-1's overlay; a ranked ghost-path list).

---

### Suggested sequencing (my read, for discussion — not decided)

FR-1 is the most self-contained and has the most existing infrastructure (2-D RI + detector overlays)
→ good first target, and its detector heat-map is reusable by FR-3. FR-2 is mostly gluing existing
tolerance pieces into a guided flow. FR-3 is the biggest (greenfield physics + workflow). The 3-D
overlay work (FR-1) will want the trace-perf fix (task #78) in place first, since an over-the-area RI
sample multiplies trace cost.
