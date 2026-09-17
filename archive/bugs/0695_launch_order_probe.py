"""0695: trap every write to _last_imaging_launch_bundles (the mirrored-launch
stash) and mark when the additive build reads it -- reveals which imaging pass
the faceB mirror actually reflects."""
from pathlib import Path

import numpy as np


def describe(bundles):
    try:
        total = sum(int(len(np.asarray(b[0]))) for b in bundles)
        D = np.concatenate([np.stack([np.asarray(b[3], float), np.asarray(b[4], float),
                                      np.asarray(b[5], float)], axis=1) for b in bundles])
        mean = D.mean(axis=0); mean /= max(np.linalg.norm(mean), 1e-12)
        ang = np.degrees(np.arccos(np.clip(D @ mean, -1, 1)))
        return f"rays={total} mean {np.round(mean, 3)} half-angle {ang.mean():.2f}/{ang.max():.2f}"
    except Exception as exc:
        return f"describe failed: {exc}"


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import source_modeling as sm

    writes = []

    class Trap:
        def __get__(self, obj, owner=None):
            return obj.__dict__.get("_stash_value")

        def __set__(self, obj, value):
            writes.append(len(writes) + 1)
            print(f"STASH WRITE {len(writes)}: {describe(value)}", flush=True)
            obj.__dict__["_stash_value"] = value

    KrakenLayoutEditor._last_imaging_launch_bundles = Trap()

    for name in dir(sm):
        obj = getattr(sm, name)
        if isinstance(obj, type) and hasattr(obj, "_build_additive_imaging_source_bundles"):
            real = obj._build_additive_imaging_source_bundles

            def marked(self, *a, **k):
                print("ADDITIVE BUILD NOW", flush=True)
                return real(self, *a, **k)

            obj._build_additive_imaging_source_bundles = marked
            print("patched additive on", name)
            break

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    stash = editor._last_imaging_launch_bundles
    print("post-build stash:", "None" if stash is None else describe(stash), flush=True)
    n_b = sum(1 for rp in (bundle.ray_paths or [])
              if str(getattr(rp, "source_id", "") or "") == "source:faceB")
    print(f"faceB rays in bundle: {n_b}", flush=True)
    editor.destroy()


if __name__ == "__main__":
    main()
