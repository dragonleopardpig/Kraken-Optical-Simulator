"""bugs/0997: does a COMPLETE optimization leave the same model with and without a Tk root?

The guard's session only starts an optimization and stops it (a whole run takes a minute and a
half). This runs one to the end -- 12 generations, one worker, the double Gauss, one thickness, the
focal length as the merit -- on an editor with a hidden Tk root and on one without, in processes
with different hash seeds, and compares every plain attribute of the two editors afterwards.

    python bugs/0997_full_optimization_both_editors.py <a scratch folder>
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

LENS = Path("KrakenOS/common_optical_layouts/double_gauss_lens.py")


def run(mode: str, out: str) -> None:
    sys.path.insert(0, ".")
    import KrakenOS.UI.validate_editor_without_tk_root as guard
    from KrakenOS.UI.layout_editor import OPERAND_REGISTRY, KrakenLayoutEditor
    from KrakenOS.UI.uihost import ScriptedUiHost

    host = ScriptedUiHost(answers={})
    editor = (KrakenLayoutEditor(headless=True, ui=host) if mode == "tk"
              else KrakenLayoutEditor(headless=True, ui=host, tk_root=False))
    editor.layout_files[LENS.stem] = LENS
    editor.load_layout_by_name(LENS.stem, refresh=False)
    host.run_due(200)
    editor._set_selected_operand_labels([list(OPERAND_REGISTRY.values())[2].label])
    editor.optimization_workers_var.set("1")
    editor.toggle_optimization_cell(3, "thickness")
    before = float(editor.rows[3].thickness)
    started = time.time()
    editor.start_optimization()
    while editor.optimization_running and time.time() - started < 500:
        host.run_due(75)
        time.sleep(0.05)
    host.run_due(500)
    plain = {}
    for key, value in list(editor.__dict__.items()):
        if key in guard.NOT_COMPARED or key.endswith("_instance"):
            continue
        item = guard._canon(value)
        plain[key] = item if item == "<object>" or len(json.dumps(item, default=str)) <= 4000 else {"<digest>": guard._digest(item)}
    plain["<rows>"] = [[row.surface, row.name, repr(float(row.thickness)), row.glass] for row in editor.rows]
    plain["<progress>"] = [str(line) for line in getattr(editor, "progress_lines", []) or []]
    Path(out).write_text(json.dumps({"plain": plain, "took": round(time.time() - started, 1), "before": before,
                                     "after": float(editor.rows[3].thickness), "status": str(editor.status_var.get()),
                                     "running": bool(editor.optimization_running)}), encoding="utf-8")
    print("DONE", mode, flush=True)
    os._exit(0)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--run":
        run(sys.argv[2], sys.argv[3])
    scratch = Path(sys.argv[1])
    scratch.mkdir(parents=True, exist_ok=True)
    records = {}
    for mode, seed in (("tk", "1"), ("none", "2")):
        out = scratch / f"optimized_{mode}.json"
        proc = subprocess.run([sys.executable, __file__, "--run", mode, str(out)], capture_output=True, text=True, timeout=900,
                              env=dict(os.environ, PYTHONHASHSEED=seed, KRAKEN_CONFIG_DIR=str(scratch / f"config_{mode}")))
        if "DONE" not in proc.stdout:
            print(mode, "FAILED:", (proc.stderr or proc.stdout)[-600:])
            raise SystemExit(1)
        records[mode] = json.loads(out.read_text(encoding="utf-8"))
        r = records[mode]
        print(f"{mode:5} hash seed {seed}: {r['took']} s; thickness {r['before']} -> {r['after']}; {r['status']!r}; "
              f"still running: {r['running']}; tracebacks on stderr: {proc.stderr.count('Traceback')}", flush=True)
    a, b = records["tk"]["plain"], records["none"]["plain"]
    compared = [key for key in sorted(set(a) & set(b)) if "<object>" not in (a[key], b[key])]
    differ = [key for key in compared if a[key] != b[key]]
    print(f"{len(compared)} plain attributes compared after the run; they differ in: {differ or 'none'}")
    print("only with a Tk root:", sorted(k for k in set(a) - set(b) if a[k] != "<object>"),
          "| only without:", sorted(k for k in set(b) - set(a) if b[k] != "<object>"))
    print("the progress lines:", len(b["<progress>"]), "| the last:", b["<progress>"][-3:])
