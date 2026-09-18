"""bugs/0801 -- the Show Rays toggle states what is on screen, and ticking it traces.

User: *"if ray is not on, why not just untick the rays on? Main thing here is matching UI toggle
with actual scene. If user toggle rays on or off, it should immediately show the ray, right now
on fresh load, without clicking Trace Now, the rays on/off toggle is not functioning."*

Right on both counts. After a fast load the gate (bugs/0646, made authoritative by bugs/0718)
makes every refresh bodies-only, so the box read ON over an empty scene AND ticking it ran
``refresh_from_editor`` which drew nothing -- a control that does nothing.

bugs/0800 only made the view SAY so, which left the toggle still broken. The resolution is that
**ticking the box IS the deliberate trace request** bugs/0646 asks for, exactly like Trace Now,
so it may clear the gate -- while an INCIDENTAL refresh still may not, which is all bugs/0718
ever required.

Display-free: source contracts plus a stub toggle. No app window.
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    from KrakenOS.UI import open3d_inspector as o3d
    from KrakenOS.UI.services import open3d_trace_refresh as otr
    from KrakenOS.UI.services import three_d_scene_tools as tdst

    # ---- A: ticking the box is a deliberate trace request ----------------------------------
    src = inspect.getsource(o3d.Kraken3DInspector._on_show_rays_changed)
    ok("_preview_trace_deferred_until_requested = False" in src,
       "A: ticking Show Rays clears the fast-load gate -- the toggle works without Trace Now")
    ok("if bool(self.show_rays_var.get())" in src,
       "A: only when it is turned ON; unticking never starts a trace")
    ok(src.index("show_rays_var.get()") < src.index("refresh_from_editor"),
       "A: and it clears the gate BEFORE refreshing, or the refresh would stay bodies-only")

    # ---- B: an INCIDENTAL refresh still cannot clear it (bugs/0718) -------------------------
    refresh_src = inspect.getsource(otr)
    ok("_preview_trace_deferred_until_requested = False" not in refresh_src,
       "B: the refresh service never clears the gate -- bugs/0718's protection against the "
       "in-process trace wedging the UI on crashed geometry is untouched")
    open_src = inspect.getsource(tdst.ThreeDSceneToolsMixin.open_3d_view)
    ok("_preview_trace_deferred_until_requested = False" not in open_src,
       "B: and neither does merely opening the 3D view")

    # ---- C: the toggle is unticked so it MATCHES the bodies-only scene ----------------------
    class _Var:
        def __init__(self, value):
            self._value = bool(value)

        def get(self):
            return self._value

        def set(self, value):
            self._value = bool(value)

    class _Editor(tdst.ThreeDSceneToolsMixin):
        def __init__(self, deferred):
            self._preview_trace_deferred_until_requested = deferred

    class _Insp:
        """bugs/0818 moved the rule to the painter and left `_pending_rays_note` delegating to
        `Kraken3DInspector._sync_show_rays_toggle_to_scene`, so a fake inspector that carries
        only the toggle no longer models the thing under test -- it would make this check pass
        (or, as it did, fail) for a reason that has nothing to do with the behaviour. Carry the
        REAL method, bound to the fake, and this still tests what it says it tests."""

        def __init__(self, rays_on, editor=None):
            from KrakenOS.UI.open3d_inspector import Kraken3DInspector

            self.show_rays_var = _Var(rays_on)
            self.editor = editor
            self._sync_show_rays_toggle_to_scene = (
                Kraken3DInspector._sync_show_rays_toggle_to_scene.__get__(self, type(self))
            )

    deferred_editor = _Editor(True)
    insp = _Insp(True, deferred_editor)
    note = deferred_editor._pending_rays_note(insp)
    ok(not insp.show_rays_var.get(),
       "C: a deferred open unticks Show Rays, so the box states the empty scene")
    ok("tick it" in note and "Trace Now" in note,
       f"C: and says how to get rays ({note.strip()[:70]}...)")

    traced_editor = _Editor(False)
    kept = _Insp(True, traced_editor)
    ok(traced_editor._pending_rays_note(kept) == "" and kept.show_rays_var.get(),
       "C: a traced scene leaves the user's toggle exactly as it was")

    already_off = _Insp(False, deferred_editor)
    ok(deferred_editor._pending_rays_note(already_off) == "",
       "C: nothing to say when the box is already off")

    # ---- D: the export keeps following the view (bugs/0800) --------------------------------
    from KrakenOS.UI.services import optical_solid_workflow as osw

    ray_src = inspect.getsource(
        osw.LayoutOpticalSolidWorkflowMixin._step_export_ray_polylines)
    ok("_preview_trace_deferred_until_requested" in ray_src,
       "D: with the toggle now honest, the export still writes rays only when the view has "
       "them -- tick the box and they appear in both")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0801 rays-toggle validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
