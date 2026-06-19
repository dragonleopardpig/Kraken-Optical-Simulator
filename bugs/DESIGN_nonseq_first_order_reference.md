# Design note — the non-sequential first-order seam (source/pupil aiming fails on beam splitters)

Status: **PHASE 1 (one-arm reference, §5/§6) SHIPPED + CONFIRMED in-app** — `c86e23c` +
`3b91f99`. **PHASE 2 FIRST-ORDER CORE (per-branch pupil, §5b) SHIPPED + headless-proven** —
`1188dd9` (`_pupil_model_inputs(rows=leaf)` per-leaf hook + `validate_open3d_per_branch_pupil`:
private-stop arms → pupils differ ~66 mm; a stop *before* the split → one shared pupil) +
`7138c46` (`unfold_branch_tilts` → a folded reflect arm unfolds to the same axial pupil).
**REMAINING Phase 2 = the per-leaf tagged LAUNCH + live 2D/3D display** — trace-dependent
(extract each imaging leaf's rows via `branch_selector`; the two-arm scene
`beam_splitter_two_arm_doublets.py` exists) + display-integrated → needs in-app render verify.
Date: 2026-06-19. Branch: `nonseq-display-refactor`.

---

## 1. TL;DR

When a beam-splitter cube is promoted before the lens, the 3D beam "focuses at the
beam splitter" and the transmit rays don't focus on the detector. **Root:** KrakenOS's
**pupil/source model is sequential and cannot trace a beam splitter** — `Kos.PupilCalc`
throws, the failure is **silently swallowed** (`except Exception: pass`), and the
fallback aims the source rays at `rows[0].thickness` — which the in-path promotion
shrank from *object→lens* (275) to *object→cube* (~176). So the rays are aimed at the
cube. **Fix:** give the first-order subsystem a *transmissive sequential reference* of
the layout (beam splitters & mesh solids → flat plates; mirrors already folded out) and
trace **that** for the pupil, instead of choking on the non-seq system. This is the
upstream root of the whole cube-before-lens bug arc. **The general target (§5b) is a
*per-branch* source — each terminal beam-splitter leaf gets its own first-order
reference, entrance pupil, and launch; the single reference is the one-imaging-arm
special case, and the per-branch form handles cascading splitters.**

---

## 2. User-visible symptoms (recordings 2026-06-19 08:38–08:48)

- flag `084227` — "ISO view, **why beam focus to beam splitter?**"
- flag `084149` — "clipped OFF, **seems not getting back to original**."
- flag `083959`→`084052` — promote, rays on/off, clipped on/off.
- Earlier arc (`231705`, `001801`, `003937`) — "still show diverging rays", "the rays
  do not even focus after passing surrogate lens", "those are missed rays".

The side view (`084149`) is unambiguous: the object rays **converge to a crossing at the
cube (z≈201)**, then the transmit beam **diverges** through the lens. In the original
(no cube) that crossing is at the **aperture stop (z≈301, inside the lens)**.

The scene is the 1X datasheet (`KrakenOS/common_optical_layouts/machine_vision_150mm_datasheet_1x.py`):
`Object → Front Datum → Thin Lens G1 → Aperture Stop F/5.6 → Thin Lens G2 → Rear Datum → Image`
(two ideal thin-lens groups + a stop). The promoted cube is a flat (Rc=0, no paraxial
power) **mesh solid with a 45° beam-splitter face**, inserted in-path before the stop.

---

## 3. Confirmed root cause

### 3.1 The reproduction (headless, definitive)

```
PupilCalc on ORIGINAL 1X (no cube), stop idx 3   →  entrance pupil z = 303.40   OK
PupilCalc on PLAIN mesh cube before lens          →  entrance pupil z = 277.78   OK  (plain mesh is NOT the trigger)
PupilCalc on BEAM-SPLITTER cube before lens       →  IndexError: index 1 is out of bounds for axis 0 with size 1
        → app falls back to object_distance = rows[0].thickness = 176  (aims the beam at the cube)
```

Aim-correction effect (flat mesh cube, on-axis finite object, fill EPD r=13.4 at the aim plane,
count transmit rays reaching the detector):

```
BUGGY aim z=176 (object_distance fallback):  5/11 reach the detector
FIXED aim z=278 (reference-pupil PupilCalc): 7/11 reach the detector
```

The aim correction is **necessary but not a silver bullet alone**: "beam focuses at the
cube" is the **chief-ray crossing** of the field fan at the (wrong) aim plane — correcting
the aim moves that crossing from the cube (176) to the lens (278). The residual overfilled
rays are then caught by the **aperture-stop vignette** (`3d398bdb`) and the **fold
classification** (`62886562`) already shipped. Chain: *correct pupil aim (upstream) +
vignette + fold-fix (downstream) → clean beam.*

### 3.2 The three stacked failures

1. **The pupil/source model is sequential.** `_build_grid_finite_object_bundles`
   (`KrakenOS/UI/services/trace_preview_sampling.py:1127`) calls
   `Kos.PupilCalc(system, ...)` (line 1130) to locate the entrance pupil and aim the
   rays. `PupilCalc` (`KrakenOS/PupilTool.py:568-668`) launches 5 paraxial test rays via
   the **sequential** `system.Trace` and minimizes spot RMS to find `PosPupInp`. A beam
   splitter in the path makes that sequential trace throw.
   - Mesh solids are forced flat in the paraxial matrix (`KrakenOS/ParaxialMatrix.py:240-241`,
     `Solid_3d_stl != "None" → radius = _FLAT_RADIUS`), so a *plain* mesh plate is fine
     (z=277.78 above). The **45° beam-splitter face / branch** is what breaks it.
2. **The failure is silently swallowed.** `trace_preview_sampling.py:1149` —
   `except Exception: pass`. No log, no surfaced error; the beam just becomes wrong.
3. **The fallback aim is wrong.** `object_distance = self._current_object_distance()`
   (line 1156) returns `float(self.rows[0].thickness)`
   (`KrakenOS/UI/services/layout_analysis_display.py` `_current_object_distance`). The
   in-path promotion (`KrakenOS/UI/services/step_overlay_promotion.py:1092` →
   `optical_chain_insert.plan_inpath_insertion`) **splits the object→lens gap**, so
   `rows[0].thickness` becomes object→cube (~176) instead of object→lens (275). The rays
   are then aimed at `(pupil_x, pupil_y, 176)` (line 1167) — the cube.

---

## 4. The architecture (why this keeps happening — the seam you doubted)

KrakenOS is fundamentally a **sequential symbolic ray tracer**. The non-sequential
capability (beam splitters, diffuse scatter, promoted mesh solids) is a **mesh-based
layer bolted on top**, not a unified redesign:

- **Trace engine** (`KrakenOS/KrakenSys.py`): `NsTrace` (line 4612) dispatches to
  `__NsTraceBranching` (line 3884) when a deterministic beam splitter / diffuse scatter
  is present. `__NonSequentialChooser` (line 1350) ray-traces **every surface as a mesh**
  (`__TraceSceneMeshRay`, line 1319) to pick the next hit — *all* analytic surfaces are
  pre-meshed into discs sized to their clear aperture (`Prerequisites3D.Face3D`,
  `Prerequisites3D.py:188`; `Flat2SigmaSurface:162`). Then `InterNormal`
  (`InterNormalCalc.py:375`) throws the mesh hit away and reverts to **symbolic math**
  for analytic surfaces (aperture checked twice). Thin lenses are meshed as discs but
  their refraction is *overridden* by the thin-lens formula — they don't really
  participate in the mesh-level branching.
- **First-order subsystems are still sequential** and cannot trace a beam splitter or
  mesh solid: the pupil (`PupilCalc`), the paraxial solve / cardinals
  (`paraxial_tools.py`, which already *rejects* non-`Standard/Thin Lens/Aperture` rows,
  line 168, and tilted rows, line 170-182), and the source aiming.

**Every bug in this cube-before-lens arc is one instance of this seam:**

| Symptom | Seam instance | What I patched (downstream) |
|---|---|---|
| Detector pulled forward | branch-detector convergence from a truncated branch path | reached-image pin `37f7e186` |
| Diverging tail past detector | ray passes the detector vertex; hard-stop endpoint skip | vertex truncation `6a01ffa4` |
| Rays skip the lens / "diverging" | analytic surface meshed to clear-aperture disc → ray outside isn't chosen → skips | aperture-stop vignette `3d398bdb` |
| Missed transmit rays always shown | branching at mesh level; "split_transmit" tagged a fold | drop `"split"` token `62886562` |
| **Beam focuses at the splitter / won't focus** | **pupil/source model is sequential → throws → silent wrong-aim fallback** | **(this note — the upstream root)** |

The downstream patches are individually correct, but they're all compensating for the
same upstream fact: **the first-order/source layer doesn't understand non-sequential
elements, fails, and falls back silently.**

---

## 5. Proposed fix — a universal first-order reference

A first-order property (entrance pupil, chief-ray aim, focal length, cardinals) is a
property of the **transmissive, centered, paraxial-equivalent** of the layout. Beam
splitters and mesh solids are, to first order on the imaging (transmit) path, just **flat
plates** (glass + thickness). Mirrors are folds. So:

> Build one **first-order reference** of any layout — beam splitters & mesh solids →
> flat plates, mirrors → folded out — and have **all** first-order code trace *that*. Use
> the full non-sequential system **only** for the actual `NsTrace`.

The pattern already exists for mirrors:
`AnalysisComputeWorkflow._paraxial_reference_rows_for_layout`
(`KrakenOS/UI/services/paraxial_tools.py:157-192`) folds mirrors out so centered ABCD
solves see the equivalent unfolded air gap. It just needs to become the **universal**
path instead of a mirror-only special case.

### Verified: a flat-plate reference gives a sane pupil
`PupilCalc` on a plain flat BK7-plate-before-lens reference returns z≈277.78 (no throw) —
exactly the kind of clean system the reference produces. So routing the pupil through the
reference fixes the aim.

---

## 5b. The real target — per-branch source/pupil (handles cascades)

The single reference in §5 is the **one-imaging-arm special case** (the current scene:
the lens is on the transmit arm; the reflect arm is afocal to a near detector, so one
launch is fine). The general architecture, when **each arm carries its own imaging lens
+ stop**:

**Why one launch can't serve two imaging arms.** A launch fills the *entrance pupil* =
the image of the *aperture stop* in object space. Where the stop sits decides everything:
- **Common stop *before* the split** (one objective → BS → two sensors): both arms share
  one entrance pupil → a single launch fills both, and each arm may differ in post-split
  focal length / sensor / magnification and still focus cleanly. **Seamless.**
- **A stop in *each* arm after the split** ("different aperture size"): each arm images
  its stop back to a **different entrance pupil — different *location* AND *diameter***
  (EPD = stop diameter scaled by the magnification of the optics imaging it into object
  space, which differs per arm). One launch fills only one; the other arm still *focuses*
  (the lens does that regardless of sampling) but is **vignetted at its stop rim and
  non-uniformly filled** — its spot / energy / MTF is wrong.

**The construction (per terminal leaf).** For each terminal branch *B* (the leaves
`branch_detectors.derive_branch_detectors` already discovers), linearise object→…→*B*'s
detector: each beam splitter on the path → a **flat plate** where *B* transmits, a **fold
mirror** where *B* reflects (the fold-merge `_paraxial_reference_rows_for_layout` already
does for mirrors). That sequential reference yields *B*'s stop, entrance pupil, and EPD.
Launch a **separate bundle per branch** (same field grid, branch-specific pupil aim +
size), **tag** each ray with *B*, and each detector collects **its own** bundle. This is
a multi-configuration source — one config per imaging detector — parallel to the
per-branch detectors and the B2 per-branch camera/sensor work; each arm becomes a full
`{lens, stop, pupil, sensor}` configuration.

**Cascading beam splitters — yes, this works.** A terminal leaf's path is a well-defined
*sequential chain* no matter the cascade depth, once the transmit/reflect choice is fixed
at each splitter (e.g. `branch_path = "S4:BS/reflect → S7:BS2/transmit"`). The plate/fold
substitution simply **composes along the cascade**, and the per-leaf reference
**auto-finds the limiting stop along that full path** via `_pupil_surface_index_for_rows`
— so it transparently handles a stop shared *upstream* of a splitter (children share that
part of the pupil) vs a stop *private* to each leaf. The cascade topology is **already
discovered** by the branch-detector walk, so per-branch pupils inherit it for free.

Caveats / bounds:
- **Launch count = number of *imaging* terminal leaves** (afocal / absorbed leaves need no
  pupil). Up to 2^N for N splitters in principle, but in practice the number of imaging
  detectors.
- **Tagging + collection:** each launched bundle still spawns the full ray tree at every
  splitter; a detector keeps only the rays from the bundle aimed at *its* leaf (the rest
  are the deliberately-mis-sampled strays for other arms).
- **Out of scope:** resonators / loops (a leaf's path isn't a simple chain) and gratings
  (need a first-order angular-dispersion / tilt model, not just plate/fold).

---

## 6. Implementation plan (the change set, when approved)

**Phasing.** Changes (A)–(D) below implement the **one-arm reference** (§5) and fix the
current scene. The **per-branch source** (§5b) is the general target — it generalises
(A)–(C) to build a reference + launch *per terminal leaf* (reusing `branch_detectors`'
topology) and tags rays per branch. Land the one-arm fix first (small, verifiable), then
the per-branch generalisation as its own reviewed change.

Three first-order files; blast radius limited to layouts that contain a non-seq element
(which today already fail into the silent fallback). No change to the ray trace itself.

**(A) Extend the reference builder** — `paraxial_tools.py:157` `_paraxial_reference_rows_for_layout`:
before the surface-type/tilt rejection (lines 168-182), detect a **non-seq element**
(`row.surface == "Beam Splitter"`, or `advanced.Solid_3d_stl` set, or
`advanced.OpticalSolidFaces`) and convert it to a clean transmissive flat plate:
`surface="Standard", rc=0, glass=row.glass, thickness=row.thickness, diameter=row.diameter`,
strip `Solid_3d_stl`/`OpticalSolidFaces`/coating, zero `tilt_*`/`desp_*`/`axis_move`.
Keep mirrors folded as-is. (This also lets the existing paraxial-solve / cardinals work
through a beam splitter, not just the pupil.)

**(B) Use the reference for the pupil** — `analysis_compute_workflow.py:780`
`_pupil_model_inputs`: build the reference when the layout has **any** non-seq element
(new helper `_layout_needs_first_order_reference`), not only when a `Mirror` is present
(current line 788).

**(C) Route the source launch through it** — `trace_preview_sampling.py:1127` and the
angular twin `_build_grid_angular_bundles`: obtain `(pupil_system, pupil_rows,
pupil_index)` from `_pupil_model_inputs(system, build_reference=True)` and call
`Kos.PupilCalc(pupil_system, pupil_index, ...)` instead of `Kos.PupilCalc(system,
self._analysis_surface_index(), ...)`.

**(D) Stop swallowing the failure** — `trace_preview_sampling.py:1149`: replace bare
`except Exception: pass` with a logged warning (`self.append_debug(...)`), and make the
geometric fallback aim at the reference entrance-pupil distance (or object→first-*powered*
element) rather than `rows[0].thickness`, so even a future reference-builder gap degrades
sanely instead of aiming at a non-powered element.

### Verification gate (before commit)
1. Unit-test the reference builder: a BS/mesh-solid row → a clean flat-plate row.
2. `PupilCalc` on the built reference for the cube scene → finite, sane `PosPupInp`
   (~278), no throw.
3. End-to-end: source rays aimed at the reference pupil focus on the detector through the
   real BS+lens system (combined with the shipped vignette + fold fixes).
4. Regression: a normal scene (no non-seq element) builds **no** reference and is
   byte-identical in aim; run `validate_open3d_aperture_stop_vignette`,
   `validate_open3d_bs_transmit_not_fold`, the branch-detector/hard-stop validators, and
   any paraxial/pupil validators.
5. In-app confirm: promote the cube, beam crosses at the lens (not the cube), transmit
   focuses on the detector, clipped-OFF restores the clean beam.

---

## 7. Risks & open questions

- **Which path does the reflect branch's pupil use?** Resolved by §5b: each branch gets
  its own reference + pupil (BS → flat plate where it transmits, → fold mirror where it
  reflects). The one-arm fix (§5/§6) models only the transmit imaging path; the reflect
  arm in the current scene is afocal and needs no pupil. When the reflect arm carries its
  own lens, the per-branch source (§5b) is required, not optional.
- **Residual overfill.** Even with the correct aim, the EPD maps with a little overfill /
  thin-lens-mesh aberration (7/11 above). That residual is by design caught by the
  aperture-stop vignette; the aim fix removes the *gross* mis-aim, not micro-vignetting.
- **Reference thickness for the solid.** The flat plate must carry the cube's **glass
  path** (body depth), with the trailing AIR spacer preserving the geometry. Need to
  confirm the promoted row's `thickness` is the glass depth (vs an axial_reserve) — if
  not, derive the plate thickness from the promotion bounds.
- **Should ALL first-order consumers route through the reference?** Cardinals, MTF/spot
  analysis surface, FOV/quick-estimation. Recommended end state: yes — one reference, one
  source of first-order truth. This note implements pupil/source first; the rest can
  follow once the pattern is proven.
- **Index keying after in-path insertion.** Agent survey flagged that some output-port /
  follower code keys off fixed surface indices built *before* insertion
  (`nonseq_output_ports.py`). Out of scope for the pupil fix, but it's another instance of
  the same seam worth a follow-up.

---

## 8. Appendix — key file:line references

- Source launch + fallback: `trace_preview_sampling.py:1127` (`_build_grid_finite_object_bundles`),
  `:1130` PupilCalc, `:1149` `except: pass`, `:1156` `object_distance`, `:1167` aim target.
- Object distance: `layout_analysis_display.py` `_current_object_distance` (`rows[0].thickness`).
- Pupil engine: `PupilTool.py:568-668` (entrance-pupil paraxial trace), `:769-827` `Pattern2Field`.
- Mesh forced flat in paraxial: `ParaxialMatrix.py:240-241`.
- First-order reference (mirror folding): `paraxial_tools.py:157-192`.
- Pupil model inputs: `analysis_compute_workflow.py:780-792`.
- Pupil surface (stop) index: `geometric_analysis.py:927-944`.
- In-path insertion: `step_overlay_promotion.py:1092`, `optical_chain_insert.plan_inpath_insertion:44`.
- Promoted solid row (Rc unset → 0): `optical_solid_workflow.py:196-236`.
- Non-seq trace: `KrakenSys.py:4612` NsTrace, `:3884` branching, `:1350`/`:1301`/`:1319` chooser,
  `:3294` beam-splitter detect; `InterNormalCalc.py:93`/`:375` intersection;
  `Prerequisites3D.py:188`/`:392` mesh build.
