"""Display-free guard: an unchanged STEP-overlay placement re-apply does NOT
cold-rebake the hover face metadata (bug 0143).

Every imported-CAD overlay placement setter -- axis offset, placement offset,
resize, rotation -- used to *unconditionally* pop the face-metadata cache, clear
the live trace-plan cache and invalidate the preview trace, even when the setter
was called with a value identical to the one already stored. That happens
constantly in normal use:

  * a click that registers as a zero-delta drag-release,
  * a glue carry whose partner delta nets to zero,
  * an "orient onto face" onto a face the body already sits on,
  * a scene refresh re-applying the saved pose.

The next hover then cold-rebaked the planar-clustering face metadata for the
display-only labels -- ~0.2 s (led) / ~1.9 s (camera) -- for no actual change,
which is the per-action lag the user felt ("Open 3D ... still very lag" with the
camera + LED + beam-splitter overlays loaded).

The fix wraps every setter in a before/after *mutation signature*
(``_step_overlay_mutation_signature`` = pose-cache signature + resize signature +
axis-anchor identity). ``_invalidate_step_overlay_after_mutation`` runs the three
side-effects only when that signature actually moved; an unchanged re-apply keeps
the cached metadata and trace. A genuine change still invalidates, so the
bugs/0050 / bugs/0010 ghost-highlight fixes stay intact.

This guard pins, with no rendering, for all four placement setters:

  1. UNCHANGED re-apply -- the face-metadata cache entry survives, the trace-plan
     cache keeps its contents, and the preview trace is NOT invalidated (the fix:
     no cold re-bake).
  2. GENUINE change -- the cache entry is popped, the trace-plan cache is reset,
     and the preview trace IS invalidated (no regression of bug 0050/0010).
  3. Source wiring -- the bugs/0050 face-metadata invalidation now lives only
     inside the guarded ``_invalidate_step_overlay_after_mutation`` and every
     setter routes through it (no unconditional invalidation survives).

Penta phase 132 (baseline -> 132).
"""

from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.services.scene_placement_commands import (
    ScenePlacementMixin,
    _step_overlay_label_set,
)

_SENTINEL_TRACE = "0143-trace-plan-sentinel"


class _Harness(ScenePlacementMixin):
    """Minimal stand-in carrying only the state the placement setters touch.

    Every method the setters reach (signature, pose-cache, resize, the
    face-metadata cache pop) is the REAL mixin implementation -- only the leaf
    state and the two display-side stubs (preview-trace invalidate, axis-anchor
    clear) are provided here, so the checks exercise production logic.
    """

    def __init__(self, label: str) -> None:
        self.label = label
        # leaf state read/written by the real methods
        self._step_overlay_axis_anchor_by_label: dict = {}
        self._step_overlay_face_metadata_cache: dict = {}
        self._live_step_overlay_trace_plan_cache: dict = {}
        self.preview_invalidations = 0
        # pose attributes for ``label`` (all neutral)
        setattr(self, f"{label}_step_rotation_x_deg", 0.0)
        setattr(self, f"{label}_step_rotation_y_deg", 0.0)
        setattr(self, f"{label}_step_rotation_z_deg", 0.0)
        setattr(self, f"{label}_step_axis_offset_xy", (0.0, 0.0))
        setattr(self, f"{label}_step_placement_offset_xyz", (0.0, 0.0, 0.0))
        setattr(self, f"{label}_step_resize", None)

    # --- display-side stubs (no Tk / no VTK) --------------------------------
    def _invalidate_preview_scene_trace(self) -> None:
        self.preview_invalidations += 1

    def _clear_step_overlay_axis_anchor(self, label: str) -> None:
        self._step_overlay_axis_anchor_by_label.pop(str(label).strip().lower(), None)

    # --- check helpers ------------------------------------------------------
    def _seed_side_effect_state(self) -> None:
        """Re-arm the three side-effect witnesses before a setter call."""
        self._step_overlay_face_metadata_cache = {(self.label, "stat"): object()}
        self._live_step_overlay_trace_plan_cache = {self.label: _SENTINEL_TRACE}
        self.preview_invalidations = 0

    def side_effects_fired(self) -> bool:
        """True iff a setter ran the bug-0050 invalidation trio."""
        cache_popped = (self.label, "stat") not in self._step_overlay_face_metadata_cache
        trace_cleared = self._live_step_overlay_trace_plan_cache == {}
        preview_hit = self.preview_invalidations > 0
        return cache_popped and trace_cleared and preview_hit

    def side_effects_quiet(self) -> bool:
        """True iff a setter left all three witnesses untouched (the fix)."""
        cache_kept = (self.label, "stat") in self._step_overlay_face_metadata_cache
        trace_kept = self._live_step_overlay_trace_plan_cache == {self.label: _SENTINEL_TRACE}
        preview_quiet = self.preview_invalidations == 0
        return cache_kept and trace_kept and preview_quiet


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    def record(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and bool(passed)
        status = "PASS" if passed else "FAIL"
        notes.append(f"{name} | {status}" + (f" | {detail}" if detail else ""))

    label = "led" if "led" in _step_overlay_label_set() else next(iter(_step_overlay_label_set()))

    # Each entry: (setter name, current/unchanged value, a genuinely different value).
    # The "unchanged" value is byte-for-byte what __init__ already stored.
    cases = [
        ("_set_step_axis_offset_xy", (0.0, 0.0), (1.5, -2.0)),
        ("_set_step_placement_offset_xyz", (0.0, 0.0, 0.0), (3.0, 0.0, -4.0)),
        ("_set_step_resize_for_label", None, (12.0, 8.0, 5.0)),
        ("_set_step_rotation_deg_tuple", (0.0, 0.0, 0.0), (0.0, 0.0, 17.0)),
    ]

    for setter_name, unchanged, changed in cases:
        # 1) UNCHANGED re-apply must NOT invalidate ---------------------------
        h = _Harness(label)
        h._seed_side_effect_state()
        getattr(h, setter_name)(label, unchanged)
        record(
            f"{setter_name}: unchanged re-apply keeps cache + trace (no re-bake)",
            h.side_effects_quiet(),
            f"cache_kept={(label, 'stat') in h._step_overlay_face_metadata_cache} "
            f"trace_kept={h._live_step_overlay_trace_plan_cache == {label: _SENTINEL_TRACE}} "
            f"preview_calls={h.preview_invalidations}",
        )

        # 2) GENUINE change MUST invalidate (no bug-0050 regression) ----------
        h2 = _Harness(label)
        h2._seed_side_effect_state()
        getattr(h2, setter_name)(label, changed)
        record(
            f"{setter_name}: genuine change still invalidates cache + trace",
            h2.side_effects_fired(),
            f"cache_popped={(label, 'stat') not in h2._step_overlay_face_metadata_cache} "
            f"trace_cleared={h2._live_step_overlay_trace_plan_cache == {}} "
            f"preview_calls={h2.preview_invalidations}",
        )

    # 3) source wiring: the bug-0050 invalidation is guarded, never raw -------
    src = (
        Path(__file__).resolve().parent
        / "services"
        / "scene_placement_commands.py"
    ).read_text(encoding="utf-8")
    guarded_sites = src.count("_invalidate_step_overlay_face_metadata_cache(label)  # bugs/0050")
    inside_guard = "def _invalidate_step_overlay_after_mutation" in src
    routed_sites = src.count("_invalidate_step_overlay_after_mutation(label, before_signature)  # bugs/0143")
    record(
        "bug-0050 face-metadata invalidation exists once, inside the mutation guard",
        guarded_sites == 1 and inside_guard,
        f"raw_0050_sites={guarded_sites} guard_defined={inside_guard}",
    )
    record(
        "all four placement setters route through the mutation guard",
        routed_sites == 4,
        f"guarded_setter_calls={routed_sites}",
    )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(note)
    print(
        "[PASS] unchanged STEP-overlay re-apply skips the cold face-metadata re-bake (bug 0143)"
        if ok
        else "[FAIL] STEP-overlay unchanged-pose re-bake guard regressed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
