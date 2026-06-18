# 0093 — Open 3D: a promoted beam-splitter cube OVER-focuses the transmitted beam (focus lands before, not beyond, the bare-lens focus)

## Status: RESOLVED — NOT A TRACE BUG. The detector position is CORRECT; the "266 bare focus" premise was wrong (2026-06-18, re-recordings flag_20260618_085552/085713/085815)

The user re-recorded a 3-step sequence. It is decisive:
- **`085552` "without beam splitter": the bare image/focus is at z=216.4** (NOT 266).
- **`085713` "after inserting the splitter": the image plane jumps to z=266.4** — exactly
  +50 mm, the inserted cube's thickness. The sequential layout just shoved the
  original Image surface back by the new element's thickness; **266 is not the focus.**
- **`085815` "after promotion": transmit branch detector at z=233.4.**

Physics: true bare focus 216.4 + plate shift `t*(1-1/n)=50*(1-1/1.5168)=17.0` = **233.4
= exactly the detector**. Headless trace at this geometry (bare focus 216.4, real
`step_32704` cube) gives transmit z=233.49. **So the detector is physically correct;
the cube pushes the focus 216→233, and the stale Image plane sits at 266 only because
it was mechanically displaced +50 mm by the cube insertion.** The original 0093 report
("focus lands before the bare focus") rested on treating 266 as the bare focus, which
it is not.

**The genuine remaining issue (085815's actual words): the displaced original Image
plane at z=266 is still drawn BEHIND the correct branch detector at z=233** — a
redundant/confusing leftover. NOT a trace fix.

### FIX (display, shipped): drop the superseded Image's curve + label
0092 hid only the 3-D clear-aperture **disk** (`_suppress_reference_aperture`). The
plane the user still sees at z=266 is the Image's **bundle `surface_curve`** (its
rectangle outline) + its **label**, which BOTH the 2-D and 3-D views draw from
`SceneBundle`. New `scene_builder.drop_superseded_image_display(...)` (called in
`build_scene_bundle` right after branch-detector derivation) drops the sequential
Image's curve + label whenever a split produced a branch detector — so the only
focus marker left is the branch detector at the true focus (233), and the Image
"lands on" it. The Image *target* is kept (hard-stop / picking; it has no visible
plane of its own). No-op on plain sequential/folded scenes (no branch detector).

**Follow-up #1 (re-recordings 092957/093142):** the running app was STALE (the curve
fix `5aba0933` wasn't loaded). A 2nd reveal path: the thickness dimension drew an
arrow to z=266; first attempt skipped that span.

**Follow-up #2 (re-recording 094836 after restart — "thickness missing after
splitting surface. The old image location is still there"):** ground-truth dump of a
real editor-built bundle showed TWO things the curve/label drop missed:
- the sequential **Image TARGET** survived (kept "for hard-stop") and, being
  `is_detector`, still drew an **orange detector footprint** at z=266 — the marker
  the user kept seeing. Fix: `drop_superseded_image_display` now also drops the Image
  target (the branch detector hard-stops the rays before it; nothing needs the 266
  plane). Verified: real bundle now has 0 sequential-Image targets.
- skipping the dimension entirely *removed the cube's own thickness* ("thickness
  missing"). Resolved in follow-up #3 below.

**Follow-up #3 (re-recordings 101227/101442 — "Detector missing, ray goes beyond …
how to measure?" / "is the S3 thickness overlay correct? … Where is the reflected ray
thickness overlay?"):** user-chosen direction = **per-branch distance overlays, cube
exit face → each detector**. The sequential thickness dims only follow the
straight-through chain, so the reflect arm had none and the transmit's was a
confusing redirect. New design:
- `BranchDetector.exit_point_world` (the arm's mean exit-ray origin = where it leaves
  the cube), carried into the scene-target metadata.
- `Open3DThicknessDimensionService._branch_distance_overlays(...)` draws one TEAL
  dimension per branch detector from `exit_point_world` → detector focus, labelled
  `"<arm>: exit→detector = N mm"` (e.g. transmit + reflect). Verified on a real
  bundle: reflect exits the +y face → its detector; transmit exits the back face →
  its detector.
- the sequential span into the superseded Image is now simply **skipped** (the branch
  overlay replaces it — no redundant blue arrow on the transmit arm). Reverted the
  `_superseding_branch_focus` redirect.

**Follow-up #4 (S3 fix + doublet→splitter dimension):** user confirmed the per-branch
overlay distance is physically correct (bare 216 + 17 plate shift = 233 detector;
overlay = exit-face→focus air gap = 48 mm — verified headlessly). Then: fix S3 (the
stale 97.376 lens→image back-focal distance, exposed post-promotion because the
gap-split only scans imported STEP overlays, not promoted solid rows) and add a
doublet-last-surface → beam-splitter-first-surface dimension. Both done with one
change: when a thickness dimension's NEXT row is a promoted optical solid
(`_row_optical_solid_stl`), measure from this surface to the solid's ENTRY face
(`_optical_solid_entry_point`, the body's near axial bound from the rendered actor
bounds) and label the real air gap (`"to <solid> = N mm"`), instead of the stale
stored thickness. Headless-safe (no rendered actors → returns None → unchanged), so
it only activates in the live app. Display-free guard covers the detection, short
name and near-face math.

Guard: `validate_open3d_superseded_image_plane_hidden` (display-free; target+curve+
label drop, dimension skip, branch-overlay exit-point + arm label) + penta Phase 86.
**Requires an app RESTART to load; in-app visual confirm pending (headless VTK
segfaults).**

---
### (superseded) earlier headless conclusion

Headless investigation (see `bugs/repro_0093.py`) shows the promoted beam-splitter
cube trace is **correct**: across a flat BK7 cube, a hand-built BK7 BS cube, and
the **real** promoted STEP cube (`step_32704`), the transmitted focus always lands
*further* than the bare-lens focus by the plane-parallel-plate shift `t*(1-1/n)`,
never closer. The 45° face is classified `internal` (no refraction) and
`inside_volumes` tracks correctly on both arms. So the over-convergence in the
recording is NOT a generic non-seq trace bug. Likely a **stale running app** at
record time (see the bug-handling note: a recording that won't reproduce after a
thorough dig → ask the user to restart + re-record), or a scene-specific factor
(coating / doublet placement / index) not captured by the recording's UI snapshot.
**Action: ask the user to restart Open 3D + re-record before any trace surgery.**
See the investigation log at the bottom.

Discovered 2026-06-18 from the user's physics reasoning while reviewing the
branch-detector positions (recordings `flag_20260618_001227_407` +
`_000848_194`). Documented here for a later session; **no fix committed yet.**

## Symptom (user)

> The old image location is the focus before the beam splitter was inserted.
> Since the beam splitter will always make the focusing further, the new detector
> position should be **after**, not **before**, the old image location.

The user only **inserted a beam splitter and promoted it while rays were on** (no
quick-estimation, no manual placement). The transmit-arm branch detector landed
*before* the original (bare-lens) focus — physically backwards.

## The data (recording flag_20260618_001227_407)

Scene: doublet (rows 1–3, z≈110–119) → promoted BK7 beam-splitter cube (row 4,
z=142–193, 50 mm, face `S001/F001` = "Partial Reflecting / Transmitting"), rays
on, `use_nonseq: True`. Cube diagonal (split point) at z≈167.

| | z (mm) | distance from diagonal |
|---|---|---|
| bare-lens focus = old Image (row 5) | 266 | 99 mm |
| traced transmit focus = branch detector (row 100001) | 233 | **66 mm** |
| traced reflect focus = branch detector (row 100000) | y=66 | **66 mm** |
| physically-expected with-cube focus (+t(1−1/n)≈17 mm) | ~283 | ~116 mm |

So the cube **over-converges** the beam: the transmit focus is ~50 mm too short
(66 mm vs ~116 mm expected) and lands *before* the bare-lens focus instead of
beyond it. Both arms converge at exactly 66 mm from the split (suspiciously
symmetric — the remaining convergence distance is the same for both, but it's the
*wrong* distance).

## Why this is a TRACE bug, not a detector-display bug

The branch detector (bugs/0088 B1 / 0090) sits at wherever the traced rays
actually converge — `_closest_approach_point` of the exit rays. So the detector
display is **correct relative to the trace**; the fault is upstream: the
non-sequential trace of the promoted beam-splitter cube is bending/over-converging
the transmitted beam.

Physics: a real beam-splitter cube is two same-glass prisms cemented at the coated
hypotenuse. The 45° interface has **no index step**, so it must only *split*
(partial reflection) and **never refract** the transmitted ray. The flat
front/back faces should contribute only the small plane-parallel-plate shift
(focus slightly **further**). Over-converging means the transmitted beam is being
refracted where it shouldn't be.

## Leading hypotheses (to check)

1. The internal 45° "Beam Splitter" face is being traced as a **refracting**
   interface (index step) instead of a coated, no-index-step split — bending the
   transmit beam.
2. The cube's front/back face refraction is applied **wrong-signed** (glass↔air
   swapped), converging instead of shifting.
3. The mesh-solid (STL-faceted) trace mishandles refraction for a converging beam
   at the flat faces.

## Investigation plan

- Reproduce headlessly: a converging beam (lens) → a flat BK7 cube (no coating) →
  confirm the focus shifts **further** by ~t(1−1/n); then add the 45° Beam
  Splitter face and check whether the transmit focus moves *closer* (the bug).
- Trace how the non-seq engine handles a promoted optical-solid's faces for the
  TRANSMIT branch (refraction vs straight-through at the Beam Splitter face);
  the 45° internal face must not apply refraction.
- North-Star: fix the non-sequential trace physics, do not dodge to sequential.
- This is separate from the detector-redesign display series (A/B1/0090/0091/0092),
  which is correct relative to the trace.

## Investigation log (2026-06-18, headless — `bugs/repro_0093.py`)

All headless (numeric ray convergence via `_closest_approach`, no VTK), so the
trace physics is verified directly (not the display). Converging cone focusing at
a bare z=200; cube centered ~z=80.

| experiment | transmit focus | reflect focus | verdict |
|---|---|---|---|
| flat BK7 cube (40 mm, no BS, no branch) | z=213.7 (+13.7 = plate shift) | — | CORRECT (further) |
| hand-built BK7 BS cube (40 mm, branching) | z=213.7 (+13.7) | 133.7 mm from split (=120+13.6) | CORRECT (further) |
| **real promoted STEP cube `step_32704` (50 mm)** | **z=217.1 (+17 = 50 mm plate shift)** | **+137 mm from split (=120+17), reflects +y** | **CORRECT (further)** |

Media sequence on every branch: `entry → internal(split) → exit`; the 45° face is
`internal` (no index step, no refraction). Both arms get the right plate shift.

Findings that overturn the original hypotheses:
- Hypotheses 1–3 (45° face refracting / front-back wrong-signed / mesh refraction)
  are all FALSE for the generic and the real geometry.
- The "media-state propagation through the split" theory is also FALSE — the child
  rays correctly inherit `inside_volumes`, so the exit faces refract glass→air.
- The detector display (`derive_branch_detectors._closest_approach_point`) is a
  faithful readout of where the traced rays converge, and that point is correct.

Conclusion: the recording's "transmit focus before the bare focus" does not occur
on current code. Most likely a **stale app** at record time (the running Open 3D
predated a trace fix in the 0085–0092 series), or a scene factor the UI snapshot
(`state.json`) doesn't carry (a coating on the cube faces, the doublet's exact
prescription, or a non-BK7 index). Re-record on a freshly restarted app; if it
still over-focuses, capture the full prescription (not just the UI snapshot) so the
exact scene can be rebuilt headlessly.

Repro harness `bugs/repro_0093.py` is reusable: it builds flat / synthetic-BS /
real-STEP cubes, traces a converging cone with the real non-seq engine, and prints
per-branch media sequence + convergence. Swap `stl_override` to test any cached
promoted cube under `attachment/cad_cache/promoted_step_overlays/`.

## Related

[[project-open3d-detector-redesign]] (B1 detectors follow this focus — confirmed
faithful), [[feedback_trace_mode_north_star]], [[feedback_random_element_ray_trace]],
[[feedback_stale_app_recording]].
