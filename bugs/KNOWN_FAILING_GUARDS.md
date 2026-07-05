# Known failing / flaky guards — discovered incidentally

These failures were found while shipping other bugs (0219–0222). Each was confirmed **pre-existing**
(fails on a clean tree with the current work stashed out), so none was introduced by those fixes.
Recorded here so they aren't rediscovered from scratch.

**Status (2026-07-05): items 1 and 2 are now FIXED (backlog-clear pass). Item 3 (test infrastructure)
remains open.**

Last verified: 2026-07-05.

---

## 1. Phase 92 — `validate_open3d_fov_solve_after_promote` — RecursionError (tkinter `__getattr__`) — ✅ FIXED

**FIXED 2026-07-05.** Root cause confirmed: `_snapshot_editor` (`render_layout_snapshot.py`) builds the
editor via `KrakenLayoutEditor.__new__` — bypassing both `__init__` and `tk.Tk.__init__` — so `self.tk`
is unset and `_optical_led_glued` (never set except by the glue setter / settings-load) is missing. On
a `tk.Tk` subclass with no `self.tk`, `getattr(editor, "_optical_led_glued", False)` recurses through
`__getattr__` instead of returning the default. Fix: give `_optical_led_glued` a real `False` default in
BOTH `KrakenLayoutEditor.__init__` and `_snapshot_editor`, so it's a plain attribute that never reaches
`__getattr__`. (In-app editors were never affected — `tk.Tk.__init__` sets `self.tk` there.) Guarded by
the guard now passing. Details of the original diagnosis kept below for reference.

**Symptom.** The guard aborts with `RecursionError: maximum recursion depth exceeded`, ~990 repeats of:

**Symptom.** The guard aborts with `RecursionError: maximum recursion depth exceeded`, ~990 repeats of:

```
File ".../tkinter/__init__.py", line 2557, in __getattr__
    return getattr(self.tk, attr)
```

**Call path into the recursion:**
`fov_solve` (`services/quick_estimation.py:1198`) → `_apply_conjugate_pair` (:970) →
`_object_locked_redirect_row` (:936). Line 936 is:

```python
if obj_row is None or not bool(getattr(self.editor, "_optical_led_glued", False)):
```

**Root cause (hypothesis).** `self.editor` in this guard's fixture is a `tkinter`-derived object whose
`.tk` was never initialised. Tk's `__getattr__` resolves any unknown attribute as `getattr(self.tk,
attr)`; with `tk` itself missing, `getattr(self.editor, "_optical_led_glued", …)` recurses on `tk`
forever and raises `RecursionError` **instead of** `AttributeError` — so the `default=False` third arg
never gets a chance to apply. `_object_locked_redirect_row` (the glued-LED QE exclusion, bugs/0118-ish)
reads `_optical_led_glued`; the `fov_solve_after_promote` fixture predates that read and supplies an
editor that can't answer it.

**Fix direction.** This is a test-fixture problem, not an optics bug. Either (a) build a complete/real
editor in `validate_open3d_fov_solve_after_promote` (or a plain non-Tk fake object that returns the
attributes QE now reads), or (b) make QE's editor-attribute reads robust to a half-built editor —
note `getattr(..., default)` does **not** save you here because the failure is `RecursionError`, not
`AttributeError`; you'd have to catch it or stop deriving the fake editor from a Tk widget.

---

## 2. Phase 115 — `validate_open3d_object_to_led_dimension` — STALE GUARD — ✅ FIXED

**FIXED 2026-07-05.** This was NOT a code bug — the guard was stale. The failing assertion
(`register_drag=False`, "no drag yet") encoded the pre-**bugs/0132** contract. bugs/0132 intentionally
added the right-click/drag "re-anchor to a surface/edge" handle to the object→LED overlay, so
`_emit_led_object_edge_dimension` now passes `register_drag=True` on purpose (see its docstring: the
value-drag is harmless because the sentinel row is rejected by `drag_state_from_current_pick`). The
guard (written for bugs/0123 + 0125) was never updated when 0132 shipped. Fix: update the guard's
check A to assert `register_drag=True` (the re-anchor handle exists) and note the 0132 supersession in
its docstring. The original (wrong) diagnosis, that the overlay "wires its drag at build time when it
should defer", is retracted — registering the drag at build time is the correct, shipped behaviour.

---

## 3. No push gating today, AND the gate wrapper fails OPEN under the Xvfb SIGSEGV

Two separate facts, both meaning a green push proves nothing:

**(a) The pre-push hook is currently DISABLED.** `git config core.hooksPath` is **unset** (verified
2026-07-04), so `.githooks/pre-push` never runs on push — pushes are ungated. (The user disabled it
~2026-06-06 because the marathon is too slow to gate every push.) The hook file still exists but is
inactive. This is why the 0219–0222 pushes went through in seconds with no validator output.

**(b) Even run by hand, the gate fails open.** `validate_open3d_penta_telescope_comprehensive` (the
~199-phase marathon, phases 0–198) SIGSEGVs partway through under Xvfb software rendering (llvmpipe)
and prints no per-phase `[PASS]/[FAIL]` lines (known — see the VTK render-backend segfault memory;
individual guards + short probes run fine). `tools/penta_validator_gate.py` parses phase states from
that stdout and blocks only on a `pass → fail` flip vs `tools/penta_validator_baseline.json`. With
**zero** parsed states, `compare()` finds no regressions and the gate passes — it fails *open*, not
closed.

Together these explain how phases 92 and 115 sit at `pass` in the baseline yet fail when run directly:
nothing has observed their failure — the baseline was baked from a run that never reached/recorded
them (or recorded them before they regressed), and nothing since re-checks them.

**Fix direction.** (a) Run the marathon under a hardware/EGL backend (NVIDIA renders it clean per the
memory note); and/or (b) shard the marathon into crash-isolated subprocess batches so one segfault
doesn't void every result; and/or (c) make the gate **fail closed** when it receives no phase output
(treat "no states parsed" as an error, not an all-clear); then re-enable the hook
(`git config core.hooksPath .githooks`). Until then, **run the individual guard for any phase you touch
by hand** — do not trust a clean push.

---

## Not-a-bug / already resolved this session (for context, no action needed)

- `camera_overlay_hover_alignment` failed transiently after bugs/0220 because its `_FakeEditor` lacked
  the new `_camera_track_image_plane_z` method — **fixed** by adding it to the fake. Lesson: adding an
  editor method that a scene-build path calls means updating the `_FakeEditor` stubs in the guards that
  use it.
