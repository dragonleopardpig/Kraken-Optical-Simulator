"""Guard: direct right-click face-assign promote clamps its forced retrace to a
sparse 3-ray fan (bugs/0116).

The plain "Promote to Optical Element" path already wraps its post-promote
``force_retrace`` in ``editor._promote_preview_ray_count_override = 3``
(bugs/0105) so a promote on a beam-splitter scene lands in ~1 s instead of
stalling on a full branched physics trace. The DIRECT face-assign path
(``Open3DFaceAssignmentService._promote_step_and_assign_face_function``) was
missing that clamp, so a right-click "Promote and set <function>" re-traced the
full ~3600-ray fan and froze the UI for ~44 s. This guard pins the clamp onto the
face-assign path and confirms the sampling layer honours the override.

``run_checks`` is display-free:

* a source check on the face-assign method -- the override is set to 3, the
  retrace runs while it is active, and it is cleared in a ``finally`` (so an
  exception can never leave the scene stuck at 3 rays);
* a behavioural check that ``TracePreviewSamplingMixin._current_ray_count``
  returns the clamped 3 when the override is set and the live ``ray_count_var``
  otherwise.

Penta phase 108 runs ``run_checks`` only.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def run_checks() -> list[tuple[str, bool, str]]:
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin

    results: list[tuple[str, bool, str]] = []

    # 1) the face-assign retrace is clamped to 3 and cleared in a finally: the
    #    override is set BEFORE the refresh, the refresh runs while it is active,
    #    and the clear sits in a finally that follows the set.
    src = inspect.getsource(
        Open3DFaceAssignmentService._promote_step_and_assign_face_function_inner
    )
    set_idx = src.find("_promote_preview_ray_count_override = 3")
    finally_idx = src.find("finally:", set_idx if set_idx >= 0 else 0)
    refresh_idx = src.find("refresh_from_editor(", set_idx if set_idx >= 0 else 0)
    clear_idx = src.find("_promote_preview_ray_count_override = None",
                         set_idx if set_idx >= 0 else 0)
    wired = (
        set_idx >= 0
        and refresh_idx > set_idx
        and finally_idx > refresh_idx
        and clear_idx > finally_idx
        and "force_retrace=True" in src
    )
    results.append(
        ("face-assign promote sets the 3-ray clamp, traces, clears it in finally",
         wired, f"set={set_idx}, refresh={refresh_idx}, finally={finally_idx}, "
                f"clear={clear_idx}")
    )

    # 2) the sampling layer honours the override -- _current_ray_count returns the
    #    clamped 3 while the promote override is set, and the live ray_count_var
    #    once it is cleared (so a later explicit trace restores full density).
    fake = SimpleNamespace(ray_count_var=SimpleNamespace(get=lambda: 41))
    fake._promote_preview_ray_count_override = 3
    clamped = TracePreviewSamplingMixin._current_ray_count(fake)
    fake.__dict__.pop("_promote_preview_ray_count_override", None)
    restored = TracePreviewSamplingMixin._current_ray_count(fake)
    honoured = clamped == 3 and restored == 41
    results.append(
        ("_current_ray_count returns 3 under the override, live count when cleared",
         honoured, f"clamped={clamped}, restored={restored}")
    )

    # 3) the drag-preview override path still wins independently (sanity: the two
    #    overrides are read from __dict__, not a recursing getattr) -- a missing
    #    override falls through to the live count without raising.
    fake_bare = SimpleNamespace(ray_count_var=SimpleNamespace(get=lambda: 7))
    bare = TracePreviewSamplingMixin._current_ray_count(fake_bare)
    results.append(
        ("no override falls through to the live ray count (no recursion/raise)",
         bare == 7, f"bare={bare}")
    )

    return results


def main() -> int:
    results = run_checks()
    ok = True
    for name, passed, det in results:
        print(f"{name} | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed
    print("[PASS] face-assign promote clamps its forced retrace to a sparse fan" if ok
          else "[FAIL] face-assign sparse-retrace clamp regressed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
