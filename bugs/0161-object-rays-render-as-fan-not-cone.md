# 0161 — object/point-source rays render as a flat fan, not a 3D cone

User report: *"why the ray from the object are now in fan instead of Cone? Can we
have point illuminate in Cone? And preserve the 2D rays gap (looks nicer). If
this conflict with Ray Count, then change the Ray Count to some discrete steps."*

A plain sequential point source (object illumination) drew a **flat meridional
fan** in the 3D view — a planar bundle in the YZ plane — instead of a real
rotationally-symmetric **cone**. The user wants the cone *and* the even 2D ray
spacing kept (the X=0 slice should still read as a clean, evenly-gapped fan).

## Root cause

Sequential non-folded scenes already select the ``world_cone`` *sampling mode*
(`_preview_3d_sampling_mode`), but the cone **sampler**
``_sample_ray_count_cone_points`` was collapsing back to a flat fan for them. Its
gate was ``_launch_pupil_prefers_meridional_fan()``, which returns True for BOTH:

* a plain sequential scene (the common object-illumination case), and
* the bug-0126 carve-out (a scene forced non-sequential *only* by an in-line
  refractive mesh solid).

bugs/0096 + 0126 had deliberately flattened the cone to a fan to dodge a perf
cliff: revolving Ray Count 20 into ``1 + (20//2)*azimuth`` pupil samples (≈201)
is ≈201 **slow non-seq mesh traces** (~70 s) — unacceptable for the inline-solid
case. But that same flattening wrongly caught the *sequential* scene, whose
revolved traces are **cheap sequential traces**. So every object point source
read as a fan.

## Fix

Split the cone gate from the pupil gate (`services/trace_preview_sampling.py`):

* New ``_launch_cone_prefers_flat_fan()`` — the cone stays a flat fan **only**
  for the bug-0126 carve-out: ``_launch_pupil_prefers_meridional_fan()`` **and**
  the resolved trace state is ``use_nonseq``. A plain sequential scene now falls
  through to the revolve branch (a real cone). Branching / folded / tilted /
  decentred scenes still revolve into the area-filling disk (unchanged).
* ``_sample_ray_count_cone_points`` now gates on
  ``_launch_cone_prefers_flat_fan()`` instead of
  ``_launch_pupil_prefers_meridional_fan()``. The revolve branch is unchanged:
  ``n_rings = count // 2`` uniform rings × ``_cone_azimuth_count()`` spokes (a
  multiple of 4 in [16, 24]).
* ``_launch_pupil_prefers_meridional_fan`` is **untouched**, so the 2D pupil
  (`_sample_ray_count_pupil_points`) and the bug-0126 perf carve-out are
  preserved exactly (phase 117 stays green).

**Why the even 2D gap survives — and why odd Ray Counts.** The revolved cone's
radial rings are ``count // 2`` and the azimuth count is a multiple of 4, so the
90°/270° meridional spokes land exactly on ``radius * j / n_rings``. For an
**odd** Ray Count the X=0 slice is then exactly ``linspace(-radius, radius,
count)`` — the same evenly-gapped N-ray fan as before. An **even** N would put
N+1 rays in the slice (a cosmetic mismatch). So the Ray Count control is
discretised to **odd** steps.

**Discrete Ray Count.** ``source_trace_helpers.py`` gains
``RAY_FAN_COUNT_VALUES = ("5", "9", "13", "21", "31", "41")`` (default
``RAY_FAN_COUNT_DEFAULT = "31"``). The main-panel "Ray fan count" entry
(`panels/main_trace_display_controls.py`) and the live-inspector "Ray count"
entry (`panels/open3d_live_controls.py`) become **readonly comboboxes** over that
set (`live_labeled_combo` gained a `sync_fields` param so the live combo keeps
the old entry's object-control sync). Cone ray totals stay well under the 2000
cone draw budget (N=5→33, 13→97, 21→201, 31→361, 41→481).

## Guard

* ``KrakenOS/UI/validate_open3d_sequential_cone_is_cone.py`` (new, penta
  Phase 152) — display-free: binds the real
  ``_sample_ray_count_cone_points`` / ``_launch_cone_prefers_flat_fan`` onto a
  light fake editor and checks (a) a plain **sequential** scene revolves into a
  real cone (off-meridian spokes exist, not a flat fan); (b) its X=0 slice is
  exactly the odd N-ray ``linspace`` fan with even gaps; (c) the bug-0126
  ``use_nonseq`` inline-solid carve-out still keeps the flat N-ray fan; (d) the
  discrete ``RAY_FAN_COUNT_VALUES`` are all odd; (e) cone totals stay under the
  draw budget.
* Updated ``validate_open3d_ray_fan_count.py`` (the ``_ConeStub`` now binds
  ``_launch_cone_prefers_flat_fan`` + a ``_resolved_trace_mode`` and exercises
  both the 0126 carve-out and the 0161 sequential revolve) and
  ``validate_open3d_ray_count_respects_nonbranching.py`` (``_FakeEditor`` binds
  the new method). Phases 40/44/46/47 (cone geometry / 2D-is-slice / cone-density
  / not-reused-as-fan) now pass for the right reason — the sequential cone is a
  genuine cone, where the cone-density guard had been latent branch debt.

## Notes

* **In-app eyeball owed:** headless has no VTK render backend and cannot drive
  the Tk comboboxes, so the *felt* result — object point sources draw a real 3D
  cone whose 2D slice is an evenly-gapped odd-N fan, and the Ray Count control is
  a discrete dropdown — must be eyeballed in the running app.
* The bug-0126 perf carve-out (inline refractive solid → flat fan, ~70 s avoided)
  is preserved; phase 117 (``validate_open3d_ray_count_respects_nonbranching``)
  stays green.
