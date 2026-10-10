"""bugs/1002, an observation the every-command survey led to: in the Qt shell, Trace Now traces
and the 3D scene draws no rays.

A load says "rays not traced -- fast load. Click Trace Now for rays". This starts the Qt shell as
the app does, loads a scene, triggers the ribbon's Trace Now and then Show Rays, and after each
step prints the Show Rays check mark, the inspector's own box, how many ray cells the 3D scene
draws and every status text -- and writes the 3D scene itself as a picture.

Usage (needs a display):  python bugs/1002_trace_now_probe.py <folder for the pictures>
"""
import os, sys, time
def main():
    out = sys.argv[1]
    from KrakenOS.UI.qt.app import build
    import KrakenOS.UI.qt.app as where
    app, window = build(["probe"])
    window.show(); window.build_scene(); app.processEvents()
    def settle(s=1.0):
        end = time.time() + s
        while time.time() < end:
            app.processEvents(); time.sleep(0.01)
    texts = []
    window.statusBar().messageChanged.connect(lambda text: texts.append("bar: " + text) if text else None)
    window.editor.status_var.trace_add("write", lambda *_a: texts.append("status: " + str(window.editor.status_var.get())))
    inspector = window._scene_inspector()
    action = window.action_manager["show_rays"]
    def rays_drawn():
        index = inspector.__dict__.get("_merged_ray_cell_index")
        return len(index) if index else 0
    def say(label, picture):
        settle()
        from vtkmodules.vtkIOImage import vtkPNGWriter
        from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter
        render_window = window.inspector_view.widget.GetRenderWindow()
        render_window.Render()
        grab = vtkWindowToImageFilter(); grab.SetInput(render_window); grab.ReadFrontBufferOff(); grab.Update()
        writer = vtkPNGWriter(); writer.SetFileName(os.path.join(out, picture)); writer.SetInputConnection(grab.GetOutputPort()); writer.Write()
        seen = []
        for text in texts:
            if text not in seen:
                seen.append(text)
        print(f"== {label}: Show Rays check {action.isChecked()} | inspector box {bool(inspector.show_rays_var.get())} | "
              f"rays drawn in 3D {rays_drawn()} | deferred {bool(getattr(window.editor, '_preview_trace_deferred_until_requested', False))}", flush=True)
        for text in seen:
            print("     " + text[:230], flush=True)
        texts.clear()
    print("code from", os.path.dirname(where.__file__), flush=True)
    window.load_layout_path("KrakenOS/common_optical_layouts/native_variable_breadth_example.py"); say("after load", "1_after_load.png")
    window.action_manager["trace_now"].trigger(); say("after the ribbon's Trace Now", "2_after_trace_now.png")
    action.trigger(); say("after Show Rays", "3_after_show_rays.png")
    os._exit(0)
if __name__ == "__main__":
    main()
