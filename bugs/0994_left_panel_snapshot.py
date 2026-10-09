"""bugs/0994: record what the Tk left panel does when the inputs that apply change.

On a real Tk editor, through a walk over every source model, every scene-trace mode and both
object modes: for each registered input its widget's state, whether and where it is gridded, the
flag the reflow uses; the model's variables for those inputs; what is set aside; and a screenshot
at the end. Run at the commit before (twice) and after, and compare.

    python bugs/0994_left_panel_snapshot.py <output path without extension>
"""
import json
import os
import subprocess
import sys
import time


def main(out: str) -> None:
    from KrakenOS.UI import system_controls
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.geometry("1700x950+0+0")

    def settle(seconds: float = 0.6) -> None:
        end = time.time() + seconds
        while time.time() < end:
            editor.update()
            time.sleep(0.02)

    settle(2.5)

    def snapshot() -> dict:
        rows = []
        for control in editor._left_mode_controls:
            widget = control["widget"]
            try:
                state = str(widget.cget("state"))
            except Exception:
                state = "-"
            info = widget.grid_info()
            rows.append([str(control["var_name"]), state, bool(widget.winfo_ismapped()), str(info.get("row", "")),
                         str(info.get("column", "")), bool(control.get("visible", True)),
                         len(control.get("managed_widgets") or ())])
        names = [str(control["var_name"]) for control in editor._left_mode_controls if control["var_name"]]
        return {"controls": rows, "values": {name: str(getattr(editor, name).get()) for name in names},
                "set aside": dict(sorted(editor._left_mode_saved_values.items())),
                "source panel": [str(editor.source_model_label.grid_info().get("columnspan")),
                                 str(editor.source_model_menu.grid_info().get("columnspan"))],
                "field panel shown": bool(editor.field_panel.winfo_ismapped())}

    def control(name: str, value: str) -> None:
        getattr(editor, name).set(value)
        getattr(editor, system_controls.control_for(name).commit)()
        settle()

    record = {"start": snapshot()}
    for model in system_controls.control_for("source_model_var").choices:
        control("source_model_var", model)
        record[f"source model {model}"] = snapshot()
    control("source_model_var", system_controls.control_for("source_model_var").choices[0])
    record["source model back"] = snapshot()
    for mode in system_controls.TRACE_MODES:
        control("trace_mode_var", mode)
        record[f"trace mode {mode}"] = snapshot()
    control("trace_mode_var", system_controls.TRACE_MODES[0])
    for mode in system_controls.OBJECT_MODES:
        control("object_mode_var", mode)
        record[f"object mode {mode}"] = snapshot()
    control("field_value_var", "3.0")
    record["a field"] = snapshot()
    control("field_count_var", "5")
    control("field_value_var", "0")
    record["the field zeroed"] = snapshot()
    control("field_value_var", "2.0")
    record["the field back"] = snapshot()
    editor.field_count_var.set("NA")
    editor._left_mode_saved_values.pop("field_count_var", None)
    editor._sync_left_mode_controls()
    settle()
    record["NA with nothing set aside"] = snapshot()
    subprocess.run(["import", "-display", os.environ["DISPLAY"], "-window", "root", out + ".png"], check=False)
    with open(out + ".json", "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=1, sort_keys=True)
    print("written", out, len(record), "snapshots", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main(sys.argv[1])
