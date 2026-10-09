"""bugs/0997: what becomes of the optimizer's worker process when Stop follows Start?

Loads a lens, marks one variable, starts an optimization and stops it after a given delay, then
looks at the worker process: right after the editor shut it down, and in the end.

    python bugs/0997_stop_right_after_start.py [delay in seconds, default 0] [...more delays]

The editor is built without a Tk root (bugs/0993), so no display is needed.
"""
import os
import sys
import time
from pathlib import Path

LENS = Path("KrakenOS/common_optical_layouts/double_gauss_lens.py")


def main(delays) -> None:
    from KrakenOS.UI.layout_editor import OPERAND_REGISTRY, KrakenLayoutEditor
    from KrakenOS.UI.uihost import ScriptedUiHost

    host = ScriptedUiHost(answers={})
    editor = KrakenLayoutEditor(headless=True, ui=host, tk_root=False)
    editor.layout_files[LENS.stem] = LENS
    editor.load_layout_by_name(LENS.stem, refresh=False)
    host.run_due(200)
    editor._set_selected_operand_labels([list(OPERAND_REGISTRY.values())[2].label])
    editor.optimization_workers_var.set("1")
    editor.toggle_optimization_cell(3, "thickness")
    for delay in delays:
        editor.start_optimization()
        worker = editor._optimization_process
        pid = worker.pid
        end = time.time() + delay
        while time.time() < end:
            host.run_due(75)
            time.sleep(0.05)

        def state() -> str:
            try:
                if worker.is_alive():
                    return "ALIVE"
                return f"dead, exit code {worker.exitcode}"
            except ValueError:          # the process object was closed: it was dead and reaped by the editor
                return "stopped and reaped"

        seen = {}
        shut_down = editor._shutdown_optimization_worker

        def watched(*args, **kwargs):
            result = shut_down(*args, **kwargs)
            seen["after the shutdown"] = state()        # BEFORE the plot refresh that Stop goes on to do
            return result

        editor._shutdown_optimization_worker = watched
        try:
            editor.stop_optimization()
        finally:
            del editor._shutdown_optimization_worker
        stopped = time.time()
        while state() == "ALIVE" and time.time() - stopped < 20:
            time.sleep(0.1)
        print(f"STOP {delay:.1f} s after Start: worker {pid} right after the editor shut it down: "
              f"{seen.get('after the shutdown')}; in the end: {state()}; status {editor.status_var.get()!r}", flush=True)
        host.run_due(200)
    os._exit(0)


if __name__ == "__main__":
    main([float(arg) for arg in sys.argv[1:]] or [0.0])
