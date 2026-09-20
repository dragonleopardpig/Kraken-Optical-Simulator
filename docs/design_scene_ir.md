# Design: a materialized Scene IR — one producer of "where is it"

Status: **proposal, agreed in outline 2026-09-20.** Supersedes the migration half of
`design_row_placement_space.md`; that document's *analysis* stands and is not repeated here.

## Why this, and not finishing the previous plan

The 2026-07-28 design called for one resolver, `world_pose()`. Steps 0 and 1 shipped:
`tools/pose_audit.py` and `services/row_placement.py`. Step 2 — pointing consumers at the
resolver — stalled, and it is worth being exact about how, because the failure mode dictates
this design.

**Step 2 could not find the producer.** Option (a) was implemented in
`_compute_folded_layout_geometry_for_rows`; the audit came back *completely unchanged* — the
edit was inert. A second round wrapped `_build_folded_surface_curves`,
`_build_sequential_surface_curves` and every `_compute_*_layout_geometry*`, loaded the scene and
forced a synchronous refresh: **not one of them fired**, while the audit reported twelve row
actors. Three sites eliminated by measurement, and the drawn geometry still came from somewhere
nobody had named.

A resolver cannot fix that. A resolver is something consumers *choose* to call, so an unmapped
producer keeps producing. A materialized IR routes around the blocker instead of solving it: you
do not have to find the old producer, because the IR becomes the producer and the old path is
re-pointed or deleted.

**The resolver's central promise is also still unfulfilled.** `world_pose()` returns
`prescription_pose()` unchanged, i.e. the *straight-equivalent* pose, with no fold applied. It
says so honestly in its docstring and tags the result with `space`. But the function nine
consumers call does not return a world pose for a SEQUENTIAL row — and SEQUENTIAL is
**176 of 179** scenes (`stay_put_freeze` / `last_axis_to_axis_move` appear in 3 of 20 attachment
scenes and 0 of 159 layouts). The fold has to move inside the producer. That is the whole job.

## The one invariant

    In the IR, `to_world` is ALWAYS post-fold. There is no unfolded pose in the IR.

A row folded twice becomes unrepresentable, because there is no second place that folds. This is
the 2026 design's §2 claim, finally true, because the fold happens in the lowering rather than in
whichever consumer got there first.

The straight-equivalent chain still exists — the sequential trace is *defined* over it — but it
is a separate, explicitly named field consumed only by the trace builder. Never the default, and
never the answer to "where is it". bugs/0593 already established that the straight equivalent is
a different *prescription*, not an unfold, and must not answer conjugate or where-is-it questions.

## Shape

Following optiland's `nonsequential/ir/` (`scene_ir.py`, `lower.py`, `interpreter.py`): frozen,
data-only dataclasses; no closures, no live object references, no lazy callbacks. If it cannot be
written to disk and read back identically, it does not belong in the IR.

    @dataclass(frozen=True)
    class EntityIR:
        id: str                      # stable across a rebuild
        kind: str                    # "surface" | "body" | "source" | "detector"
        to_world: np.ndarray         # (4,4) homogeneous, POST-FOLD, always
        placement_space: str         # provenance: how to_world was derived
        source_row: int | None       # the row it came from, for the audits
        params: dict                 # kind-specific, plain data

    @dataclass(frozen=True)
    class SceneIR:
        entities: tuple[EntityIR, ...]
        legs: tuple[LegIR, ...]          # the fold structure, as data
        prescription: tuple[RowIR, ...]  # straight-equivalent chain, trace builder ONLY
        provenance: dict                 # scene path, build stamp, lowering version

`lower(editor) -> SceneIR` is the only code permitted to read `row.desp_*`, `_row_z_positions()`,
`ScenePlacement`, or a fold transform. Everything else reads the IR.

Full scope was chosen, so all four kinds lower: optical surfaces, STEP bodies (imported and
promoted), scene sources, and detectors. Bodies matter most — bugs/0748 and 0815 are body drift,
not surface drift.

## Migration

Incremental, because a big-bang cannot be validated and this codebase has already reverted five
fixes written ahead of their reproduction.

**Phase A — build it, read it from nowhere.** `lower()` and `SceneIR` land alongside. No consumer
changes. Both audits are extended with a third comparison: *IR pose vs each existing consumer's
pose, per entity*. This is the instrument that answers "who produced this", which no previous
attempt could.

**Phase B — make the IR reproduce TODAY, bugs included.** The lowering is extracted verbatim from
current behaviour until the Phase-A comparison is green everywhere. This is the discipline that
made Step 1 safe, and it has one non-obvious requirement:

> Phase B must reproduce the 8.820 mm drift of bugs/0815, not fix it.

If the IR silently improves something here, "the IR is wired correctly" becomes
indistinguishable from "the IR changed an answer", and every later divergence is unattributable.
Fixes come in Phase D, deliberately, with the audit showing the number go to zero.

**Phase C — re-point consumers, one per commit,** both audits green after each. Order by blast
radius, smallest first; the nine `row_placement` importers are the mapped set. The unmapped actor
producer surfaces here as an entity whose drawn pose still disagrees with the IR after its
nominal consumer is converted — which is exactly the diagnostic that was missing before.

**Phase D — the fold moves inside `lower()`.** The only phase that changes physics. Own gate run,
own eyeball, and the audits are expected to *move*: the 8.820 mm goes to zero here, on purpose.

## Acceptance

Both instruments, gated together, per commit — neither alone caught everything before:

* `scene_placement_audit.pinned_placement_drifts` — authored centre vs live centre. This is what
  the user actually reports (*"the prisms are all off centered"*).
* `tools/pose_audit.py` — drawn == traced == body, **visible actors only**. The 0457 lesson is
  load-bearing: an audit that measured a zero-opacity picking proxy produced a confident, precise,
  wrong 51.50 mm, and three investigations chased it.

Plus the Phase-A addition: IR pose == consumer pose, per entity, per kind.

### Measured baseline, ELS85, 2026-09-20

    rows=9  drawn_row_actors=9  bodies=0
    row 7 Standard   PRESCRIPTION (245.02, 0.00, 54.35)
                     DRAWN        (246.28, 0.00, 55.60)   1.78 mm  <== DISAGREE
    every other row  0.00 mm

The repro is alive. Row 7's 1.78 mm is the divergence the previous design left
uncharacterised (candidate: the solid's centroid-vs-vertex convention), and it is
reproducible in about two minutes. That is Phase B's target number: it must still read
1.78 mm after the IR is wired, and move only in Phase D.

### Phase A has a prerequisite: the instrument is blind to bodies

`bodies=0` above is not a property of the scene. ELS85 declares **six** promoted-solid
references and its STEP file is present on disk
(`attachment/cad_cache/beam_splitter_templates/bs_plate_8980ed101283236d.step`, 16.6 kB),
yet `_body_centers` -- which calls `_transformed_imported_step_mesh_for_label` -- returns
nothing.

So the acceptance instrument cannot currently see the entity kind that generates the live
bugs: 0748 and 0815 are **body** drift, seven rows at 8.820 mm. Gating on a pair of audits
where one is blind to bodies would repeat the 0457 lesson prospectively -- a confident,
precise measurement of the wrong thing.

### The audit's own core comparison is invalid on a FOLDED scene

Running it on `om05a_folded.py` reports **9 drawn-vs-prescription disagreements** with
values like row 8 `drawn [-185.27, 56.36, -25.00]` against `prescription [0, 0, 275.01]`.
Those are not defects. DRAWN is folded; PRESCRIPTION is the straight-equivalent, because
`row_placement.world_pose()` does not apply the fold. The instrument is comparing the two
quantities this whole design exists to stop people comparing.

So today the audit's core reading is only meaningful on an UNFOLDED scene, which is why
ELS85 reads cleanly (one genuine 1.78 mm) and om05a reads as nine false positives. The
audit becomes valid on folded benches at exactly the moment Phase D moves the fold inside
`lower()` -- the instrument and the fix are the same change, and neither can be judged
before it.

Practical consequence for the gate set: until Phase D, gate the drawn-vs-prescription
comparison on the unfolded scenes only, and gate the folded benches on **body drift**,
which is already correct on them (all eleven promoted bodies read 0.0000 mm).

**Fix `_body_centers` before Phase A begins.** Until it reports bodies on ELS85 and on the
om05a benches, the IR comparison has no baseline for the half of the scope that matters
most, and no phase after it can be honestly gated.

A note on the corpus: the 0457 repro scene `machine_vision_AZ85_RA_Mirror_BS.py` is no longer in
`attachment/`, but its successor is — **AZ85 IS ELS-85**, the same lens renamed, and
`machine_vision_ELS85.py` carries the same structure that made it the repro: 21 world-placement
keys and a promoted beam splitter. `tools/pose_audit.py` now defaults to it.

The world-placed scenes are `machine_vision_ELS85.py`, `machine_vision_Pyrite85.py` and
`machine_vision_Apo75.py` (21 placement keys each); the folded om05a benches are the live
body-drift cases. The gate set should be those five, not the old one.

## Explicitly not in scope

* Changing the sequential trace's own mathematics. It keeps consuming `prescription`.
* Re-plumbing the seven overlay services (bugs/0823 registry is the identification layer; the
  draw path is separate).
* Serialization of the IR to the saved `.py` scene format. The IR is derived; the scene file
  stays the source of truth.

## Open questions

0. **Why does `_body_centers` see no bodies?** Blocks Phase A (above).
   Not a design question so much as the first task, but it is unanswered and everything
   downstream is gated on it.

1. **Entity identity across a rebuild.** `id` must be stable or the audits cannot pair entities
   between runs, and per-row desp compounding (0815) means row index alone is not stable under
   insertion. Candidate: `(kind, authored label, ordinal)`. Needs a decision before Phase A.
2. **Where does `lower()` run, and how often?** Once per scene change is the intent, but the
   0700/0646 fast-load work means "scene change" is not currently one event. Lowering on every
   refresh would be correct and possibly too slow — needs measurement against
   `summarize_open3d_timing` before Phase C.
3. **Do promoted STEP bodies carry their own `to_world`, or derive it from their anchor row?**
   0503 says lens glue is *relative* (reference + datum delta) and the reference must never be
   shifted in slide/carry code. The IR must express that relationship, not flatten it — otherwise
   lowering bakes in a seat that later moves.
