"""Validate Optimization panel control contracts."""

from __future__ import annotations

import inspect

from KrakenOS.UI.panels.main_optimization_panel import MainOptimizationPanel
from KrakenOS.UI.services.analysis_compute_workflow import AnalysisComputeWorkflowMixin


def main() -> int:
    failures: list[str] = []
    panel_source = inspect.getsource(MainOptimizationPanel)
    workflow_source = inspect.getsource(AnalysisComputeWorkflowMixin)
    start_source = inspect.getsource(AnalysisComputeWorkflowMixin.start_optimization)

    if "optimization_start_stop_button" not in panel_source:
        failures.append("Optimization panel must keep a named stateful start/stop button.")
    if "Check Backend" in panel_source:
        failures.append("Optimization panel should not expose a separate Check Backend button.")
    if "text=\"Stop\"" in panel_source or "text='Stop'" in panel_source:
        failures.append("Optimization panel should not expose a separate Stop button.")
    if "_update_optimization_button_state" not in workflow_source:
        failures.append("Optimization workflow must update the stateful start/stop button.")
    if "Stop Optimization" not in workflow_source:
        failures.append("Running optimization button text must become Stop Optimization.")
    if "command=self.stop_optimization if running else self.start_optimization" not in workflow_source:
        failures.append("Running optimization button command must switch to stop_optimization.")
    if start_source.find("_optimization_preflight_messages") > start_source.find("self.optimization_running = True"):
        failures.append("Optimizer backend preflight must run before optimization_running becomes true.")

    if failures:
        print("Optimization control validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Optimization control validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
