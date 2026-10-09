"""bugs/0996: does the file a scene is saved to depend on the PROCESS that saves it?

Loads one scene and saves it, in fresh processes with different Python hash seeds, and prints each
file's SHA-1 and the order of the operands in it. Before the fix: a different file per process.

    python bugs/0996_save_across_processes.py <a scratch folder>

The editor is built without a Tk root (bugs/0993), so no display is needed.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")


def save(out: str) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
    from KrakenOS.UI.uihost import ScriptedUiHost

    host = ScriptedUiHost(answers={"asksaveasfilename": out})
    editor = KrakenLayoutEditor(headless=True, ui=host, tk_root=False)
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    host.run_due(200)
    editor.save_layout_as()
    print("ORDER", list(_load_python_data(Path(out))["settings"]["operands"]), flush=True)
    os._exit(0)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--save":
        save(sys.argv[2])
    scratch = Path(sys.argv[1])
    seen = {}
    for seed in ("1", "2", "3"):
        out = scratch / f"seed_{seed}" / "saved_scene.py"
        out.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run([sys.executable, __file__, "--save", str(out)], capture_output=True, text=True, timeout=600,
                              env=dict(os.environ, PYTHONHASHSEED=seed, KRAKEN_CONFIG_DIR=str(scratch / f"config_{seed}")))
        order = next((line[6:] for line in proc.stdout.splitlines() if line.startswith("ORDER ")), "FAILED " + proc.stderr[-300:])
        seen[seed] = hashlib.sha1(out.read_bytes()).hexdigest() if out.exists() else None
        print(f"hash seed {seed}: {seen[seed]}  operands {order[:110]}", flush=True)
    print("one file from every process:", len(set(seen.values())) == 1)
