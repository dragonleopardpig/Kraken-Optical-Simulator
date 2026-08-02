"""bugs/0508 A -- stage-bisect the writer of the built image's TRANS_2A slot.

One-line repro (rows[3].desp_x -= 23.4 on the AZ85 BS scene), with:
  * before/after image-transform snapshots around each _build_preview_system_rays_bundle stage
  * a spy on every build_optical_solid_output_port_pose_overrides call (caller, system?,
    override count, row-8 frame_source)
  * a spy on _apply_optical_solid_output_port_system_overrides_built (override keys)

    timeout 600 xvfb-run -a .devenv/state/venv/bin/python -u bugs/probe_0508a_writer_bisect.py [delta]
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI import nonseq_output_ports as ports

DELTA = float(sys.argv[1]) if len(sys.argv) > 1 else -23.4

editor = KrakenLayoutEditor()
editor.layout_files["probe"] = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
editor.load_layout_by_name("probe")
editor.rows[3].desp_x = float(editor.rows[3].desp_x) + DELTA
IMG = len(editor.rows) - 1


def img(system) -> str:
    try:
        t = np.asarray(system.TRANS_2A[IMG], dtype=float)[:3, 3]
        return f"({t[0]:.3f},{t[1]:.3f},{t[2]:.3f})"
    except Exception as exc:
        return f"ERR:{type(exc).__name__}"


def callers() -> str:
    names = [f.name for f in traceback.extract_stack()[:-2]]
    return ">".join(names[-4:])


_orig_builder = ports.build_optical_solid_output_port_pose_overrides


def _builder_spy(rows, *, system=None):
    out = _orig_builder(rows, system=system)
    r8 = (out or {}).get(IMG) or {}
    print(
        f"OVERRIDE-BUILD sys={'Y' if system is not None else 'n'} n={len(out or {})} "
        f"keys={sorted((out or {}).keys())} img_src={r8.get('frame_source', '-')} "
        f"via {callers()}",
        flush=True,
    )
    return out


ports.build_optical_solid_output_port_pose_overrides = _builder_spy

_orig_apply_built = ports._apply_optical_solid_output_port_system_overrides_built


def _apply_spy(system, overrides, *a, **k):
    print(
        f"APPLY-BUILT n={len(overrides or {})} keys={sorted((overrides or {}).keys())} "
        f"img_before={img(system)} via {callers()}",
        flush=True,
    )
    out = _orig_apply_built(system, overrides, *a, **k)
    print(f"APPLY-BUILT done img_after={img(system)}", flush=True)
    return out


ports._apply_optical_solid_output_port_system_overrides_built = _apply_spy

_orig_build = editor.build_system


def _build_spy(*a, **k):
    system = _orig_build(*a, **k)
    print(f"STAGE post-build_system   img={img(system)}", flush=True)
    return system


editor.build_system = _build_spy

_orig_trace = editor._trace_preview_rays_folded_aware


def _trace_spy(system, *a, **k):
    print(f"STAGE pre-folded-trace    img={img(system)}", flush=True)
    out = _orig_trace(system, *a, **k)
    print(f"STAGE post-folded-trace   img={img(system)}", flush=True)
    return out


editor._trace_preview_rays_folded_aware = _trace_spy

_orig_bundle = editor._build_scene_bundle


def _bundle_spy(system, *a, **k):
    print(f"STAGE pre-scene-bundle    img={img(system)}", flush=True)
    out = _orig_bundle(system, *a, **k)
    print(f"STAGE post-scene-bundle   img={img(system)}", flush=True)
    return out


editor._build_scene_bundle = _bundle_spy

print(f"CONFIG rows[3].desp_x{DELTA:+g}  IMG={IMG}", flush=True)
system, _, _ = editor._build_preview_system_rays_bundle(
    update_state=False, include_live_step_overlays=False
)
print(f"FINAL                     img={img(system)}", flush=True)
