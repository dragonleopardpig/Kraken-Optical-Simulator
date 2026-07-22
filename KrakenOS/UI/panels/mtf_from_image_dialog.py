"""Measure MTF from a captured image -- interactive "draw a box on the image" dialog, two modes:

* **Slanted edge** (ISO 12233, :mod:`KrakenOS.EdgeMTF`) -- drag ONE box over a dark/bright edge and get
  a WHOLE MTF curve.  This is the simplest workflow and what most captured MTF targets are.
* **USAF three-bar** (:mod:`KrakenOS.USAFMTF`) -- drag a box over EACH three-bar element (set its
  group / element / bar orientation); every element contributes ONE point to the curve.

Coordinate model: the image is displayed scaled-to-fit; ROIs are stored in ORIGINAL image pixels
(``canvas coord / scale``) so the fit always runs on the full-resolution capture.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np

_MAX_W, _MAX_H = 660, 560
_ORIENTATIONS = ("vertical", "horizontal")


def _style_mtf_axes(ax) -> None:
    """Pin both axes to a common 0.0 origin (no matplotlib margin) and put the Y ticks at
    0.0, 0.2, ..., 1.0 (user request, bugs/0411)."""
    ax.set_xlim(left=0.0)
    ax.set_ylim(0.0, 1.05)
    ax.set_yticks(np.arange(0.0, 1.001, 0.2))
    ax.margins(x=0.0)


def open_mtf_from_image_dialog(editor) -> None:
    """Open the interactive "Measure MTF from Image" dialog on ``editor``."""
    try:
        from KrakenOS.USAFMTF import analyze_usaf_image, load_grayscale_image
        from KrakenOS.EdgeMTF import measure_slanted_edge_mtf
    except Exception as exc:  # pragma: no cover - defensive
        messagebox.showerror("Measure MTF from Image", f"MTF modules unavailable:\n\n{exc}", parent=editor)
        return
    try:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        from PIL import Image, ImageTk
    except Exception as exc:  # pragma: no cover - defensive
        messagebox.showerror("Measure MTF from Image", f"Pillow + matplotlib are required:\n\n{exc}", parent=editor)
        return

    state: dict = {"path": None, "gray": None, "scale": 1.0, "photo": None, "rois": [], "result": None}

    window = tk.Toplevel(editor)
    window.title("Measure MTF from Image")
    window.transient(editor)
    root = ttk.Frame(window, padding=8)
    root.grid(row=0, column=0, sticky="nsew")

    # --- top: import + target-type mode + the USAF "next ROI" fields ---
    bar = ttk.Frame(root)
    bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    ttk.Button(bar, text="Import Image...", command=lambda: _load_image()).grid(row=0, column=0)
    ttk.Label(bar, text="   Target:").grid(row=0, column=1, padx=(8, 2))
    mode_var = tk.StringVar(value="edge")
    ttk.Radiobutton(bar, text="Slanted edge", variable=mode_var, value="edge", command=lambda: _on_mode()).grid(row=0, column=2)
    ttk.Radiobutton(bar, text="USAF three-bar", variable=mode_var, value="usaf", command=lambda: _on_mode()).grid(row=0, column=3, padx=(4, 0))

    usaf_fields = ttk.Frame(root)
    usaf_fields.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 2))
    ttk.Label(usaf_fields, text="Next ROI →  Group").grid(row=0, column=0, padx=(0, 2))
    group_var = tk.StringVar(value="2")
    ttk.Entry(usaf_fields, textvariable=group_var, width=4).grid(row=0, column=1)
    ttk.Label(usaf_fields, text="Element").grid(row=0, column=2, padx=(8, 2))
    element_var = tk.StringVar(value="1")
    ttk.Entry(usaf_fields, textvariable=element_var, width=4).grid(row=0, column=3)
    ttk.Label(usaf_fields, text="Bars").grid(row=0, column=4, padx=(8, 2))
    orient_var = tk.StringVar(value="vertical")
    ttk.Combobox(usaf_fields, textvariable=orient_var, values=list(_ORIENTATIONS), state="readonly", width=10).grid(row=0, column=5)
    ttk.Label(usaf_fields, text="Cycles").grid(row=0, column=6, padx=(8, 2))
    cycles_var = tk.StringVar(value="3")
    ttk.Entry(usaf_fields, textvariable=cycles_var, width=4).grid(row=0, column=7)

    instruction = tk.StringVar(value="")
    ttk.Label(root, textvariable=instruction, foreground="#1d4ed8", wraplength=1000, justify="left").grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 4))

    canvas = tk.Canvas(root, width=_MAX_W, height=_MAX_H, background="#20242b", highlightthickness=1, highlightbackground="#3a4150")
    canvas.grid(row=3, column=0, sticky="nsew", padx=(0, 8))

    right = ttk.Frame(root)
    right.grid(row=3, column=1, sticky="nsew")
    right.columnconfigure(0, weight=1)

    ttk.Label(right, text="ROIs:").grid(row=0, column=0, sticky="w")
    cols = ("g", "e", "orient", "roi", "mtf", "r2")
    tree = ttk.Treeview(right, columns=cols, show="headings", height=7, selectmode="browse")
    for c, t, w in (("g", "Grp", 40), ("e", "El", 34), ("orient", "Bars", 74), ("roi", "ROI (px)", 150), ("mtf", "MTF", 60), ("r2", "R²", 56)):
        tree.heading(c, text=t)
        tree.column(c, width=w, anchor="w")
    tree.grid(row=1, column=0, sticky="ew")
    roi_btns = ttk.Frame(right)
    roi_btns.grid(row=2, column=0, sticky="w", pady=(3, 8))
    ttk.Button(roi_btns, text="Delete ROI", command=lambda: _delete_selected()).grid(row=0, column=0)
    ttk.Button(roi_btns, text="Clear All", command=lambda: _clear_rois()).grid(row=0, column=1, padx=(6, 0))

    calib = ttk.LabelFrame(right, text="Calibration (optional)", padding=6)
    calib.grid(row=3, column=0, sticky="ew")
    mag_var = tk.StringVar(value="")
    pitch_var = tk.StringVar(value="")
    contrast_var = tk.StringVar(value="1.0")
    space_var = tk.StringVar(value="pixel")
    mag_row = ttk.Frame(calib)
    ttk.Label(mag_row, text="Magnification |m| (USAF image-space)").grid(row=0, column=0, sticky="w")
    ttk.Entry(mag_row, textvariable=mag_var, width=10).grid(row=0, column=1, sticky="e", padx=(8, 0))
    contrast_row = ttk.Frame(calib)
    ttk.Label(contrast_row, text="Target contrast (USAF, 0-1]").grid(row=0, column=0, sticky="w")
    ttk.Entry(contrast_row, textvariable=contrast_var, width=10).grid(row=0, column=1, sticky="e", padx=(8, 0))
    pitch_row = ttk.Frame(calib)
    ttk.Label(pitch_row, text="Pixel pitch [µm] (for lp/mm)").grid(row=0, column=0, sticky="w")
    ttk.Entry(pitch_row, textvariable=pitch_var, width=10).grid(row=0, column=1, sticky="e", padx=(8, 0))
    space_row = ttk.Frame(calib)
    ttk.Label(space_row, text="Frequency axis").grid(row=0, column=0, sticky="w")
    space_combo = ttk.Combobox(space_row, textvariable=space_var, state="readonly", width=10)
    space_combo.grid(row=0, column=1, sticky="e", padx=(8, 0))
    for i, w in enumerate((mag_row, contrast_row, pitch_row, space_row)):
        w.grid(row=i, column=0, sticky="ew", pady=1)
        w.columnconfigure(0, weight=1)

    action = ttk.Frame(right)
    action.grid(row=4, column=0, sticky="ew", pady=(8, 4))
    ttk.Button(action, text="Compute MTF", command=lambda: _compute()).grid(row=0, column=0)
    ttk.Button(action, text="Save CSV...", command=lambda: _save_csv()).grid(row=0, column=1, padx=(6, 0))
    ttk.Button(action, text="Close", command=lambda: _close()).grid(row=0, column=2, padx=(6, 0))
    status = tk.StringVar(value="Import a captured image to begin.")
    ttk.Label(right, textvariable=status, foreground="#475569", wraplength=320, justify="left").grid(row=5, column=0, sticky="ew", pady=(2, 6))

    figure = Figure(figsize=(3.6, 2.6), dpi=100)
    ax = figure.add_subplot(111)
    ax.set_title("MTF")
    _style_mtf_axes(ax)
    ax.grid(True, alpha=0.25)
    plot_canvas = FigureCanvasTkAgg(figure, master=right)
    plot_widget = plot_canvas.get_tk_widget()
    plot_widget.grid(row=6, column=0, sticky="nsew")
    # bugs/0415: click the curve to enlarge it, matching the main-window Analysis curves (render a
    # high-res PNG + open in the system image viewer). The hand cursor signals it is clickable.
    plot_widget.configure(cursor="hand2")
    plot_widget.bind("<Button-1>", lambda _e: _enlarge_plot())
    ttk.Label(right, text="Click the plot to enlarge (opens in the image viewer).",
              foreground="#64748b", font=("TkDefaultFont", 8)).grid(row=7, column=0, sticky="w", pady=(1, 0))
    right.rowconfigure(6, weight=1)

    # ------------------------------------------------------------------ helpers
    def _on_mode() -> None:
        edge = mode_var.get() == "edge"
        for child in usaf_fields.winfo_children():
            try:
                child.configure(state="disabled" if edge else "normal")
            except tk.TclError:
                pass
        space_combo.configure(values=("pixel", "image") if edge else ("object", "image"))
        space_var.set("pixel" if edge else "object")
        if edge:
            instruction.set("Slanted edge: drag ONE box over a dark/bright edge, then Compute → full MTF curve (cycles/pixel; set pixel pitch for lp/mm).")
        else:
            instruction.set("USAF three-bar: set Group/Element/Bars, drag a box over EACH three-bar element (one point per element), then Compute.")
        _clear_rois(redraw_image=False)

    def _load_image() -> None:
        path = filedialog.askopenfilename(
            title="Import captured MTF-target image", parent=window,
            filetypes=[("Images", "*.png *.tif *.tiff *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            gray = load_grayscale_image(path)
            pil = Image.open(path).convert("RGB")
        except Exception as exc:
            status.set(f"Could not load image: {exc}")
            return
        w, h = pil.size
        scale = min(_MAX_W / w, _MAX_H / h, 1.0)
        disp = pil.resize((max(1, int(w * scale)), max(1, int(h * scale))))
        photo = ImageTk.PhotoImage(disp, master=window)
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=photo)
        state.update(path=Path(path), gray=gray, scale=scale, photo=photo)
        _clear_rois(redraw_image=False)
        status.set(f"Loaded {Path(path).name} ({w}×{h}px @ {scale:.2f}×). {'Drag one box over the edge.' if mode_var.get()=='edge' else 'Drag a box over each element.'}")

    def _on_press(event):
        if state["gray"] is None:
            return
        state["_drag"] = (canvas.canvasx(event.x), canvas.canvasy(event.y))
        state["_band"] = canvas.create_rectangle(*state["_drag"], *state["_drag"], outline="#22d3ee", width=2, dash=(3, 2))

    def _on_motion(event):
        if not state.get("_band"):
            return
        x0, y0 = state["_drag"]
        canvas.coords(state["_band"], x0, y0, canvas.canvasx(event.x), canvas.canvasy(event.y))

    def _on_release(event):
        band = state.pop("_band", None)
        if not band:
            return
        x0, y0 = state.pop("_drag")
        x1, y1 = canvas.canvasx(event.x), canvas.canvasy(event.y)
        canvas.delete(band)
        cx0, cx1 = sorted((x0, x1))
        cy0, cy1 = sorted((y0, y1))
        if (cx1 - cx0) < 8 or (cy1 - cy0) < 8:
            status.set("Box too small -- drag a larger rectangle.")
            return
        s = state["scale"]
        roi_px = (round(cx0 / s, 1), round(cy0 / s, 1), round(cx1 / s, 1), round(cy1 / s, 1))
        if mode_var.get() == "edge":
            _clear_rois(redraw_image=False)  # slanted edge uses a SINGLE ROI
            rect_id = canvas.create_rectangle(cx0, cy0, cx1, cy1, outline="#22d3ee", width=2)
            label_id = canvas.create_text(cx0 + 3, cy0 + 8, anchor="w", text="edge", fill="#22d3ee", font=("TkDefaultFont", 8))
            state["rois"].append({"kind": "edge", "roi": roi_px, "rect_id": rect_id, "label_id": label_id})
            _refresh_tree()
            status.set("Edge ROI set. Click Compute MTF.")
            return
        try:
            group = int(group_var.get())
            element = int(element_var.get())
            cycles = float(cycles_var.get())
            orientation = str(orient_var.get()).strip().lower()
            if orientation not in _ORIENTATIONS or not 1 <= element <= 6 or cycles <= 0:
                raise ValueError
        except (TypeError, ValueError):
            status.set("Set a valid Group (int), Element (1-6), Bars, Cycles (>0) before drawing.")
            return
        rect_id = canvas.create_rectangle(cx0, cy0, cx1, cy1, outline="#22d3ee", width=2)
        label_id = canvas.create_text(cx0 + 3, cy0 + 8, anchor="w", text=f"G{group}E{element} {orientation[0].upper()}", fill="#22d3ee", font=("TkDefaultFont", 8))
        state["rois"].append({"kind": "usaf", "group": group, "element": element, "orientation": orientation,
                              "cycles": cycles, "roi": roi_px, "label": f"G{group}E{element}", "rect_id": rect_id, "label_id": label_id})
        element_var.set(str(element + 1 if element < 6 else 1))
        _refresh_tree()
        status.set(f"Added ROI G{group}E{element}. {len(state['rois'])} ROI(s); Compute when ready.")

    canvas.bind("<ButtonPress-1>", _on_press)
    canvas.bind("<B1-Motion>", _on_motion)
    canvas.bind("<ButtonRelease-1>", _on_release)

    def _refresh_tree() -> None:
        tree.delete(*tree.get_children())
        for i, r in enumerate(state["rois"]):
            roi = r["roi"]
            m, r2 = r.get("_mtf"), r.get("_r2")
            tree.insert("", "end", iid=str(i), values=(
                r.get("group", ""), r.get("element", ""), r.get("orientation", "edge"),
                f"{roi[0]:g},{roi[1]:g},{roi[2]:g},{roi[3]:g}",
                "" if m is None else f"{m:.3f}", "" if r2 is None else f"{r2:.3f}",
            ))

    def _delete_selected() -> None:
        sel = tree.selection()
        if not sel:
            return
        r = state["rois"].pop(int(sel[0]))
        for key in ("rect_id", "label_id"):
            try:
                canvas.delete(r[key])
            except Exception:
                pass
        _refresh_tree()

    def _clear_rois(redraw_image: bool = True) -> None:
        for r in state["rois"]:
            for key in ("rect_id", "label_id"):
                try:
                    canvas.delete(r[key])
                except Exception:
                    pass
        state["rois"] = []
        state["result"] = None
        _refresh_tree()

    def _opt_float(var):
        text = str(var.get()).strip()
        if not text:
            return None
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    def _compute() -> None:
        if state["gray"] is None:
            status.set("Import an image first.")
            return
        pitch = _opt_float(pitch_var)
        space = str(space_var.get())
        if mode_var.get() == "edge":
            roi = state["rois"][0]["roi"] if state["rois"] else None  # whole image if none drawn
            try:
                result = measure_slanted_edge_mtf(state["gray"], roi, pixel_pitch_um=pitch)
            except Exception as exc:
                status.set(f"Edge MTF failed: {exc}")
                return
            state["result"] = result
            _refresh_tree()
            ax.clear()
            try:
                result.plot(frequency_space=("image" if space == "image" else "pixel"), ax=ax)
            except Exception as exc:
                status.set(f"Plot failed: {exc}")
                return
            _style_mtf_axes(ax)
            figure.tight_layout()
            plot_canvas.draw()
            mtf50 = result.mtf50_cycles_per_px()
            status.set(f"Edge MTF: angle {result.edge_angle_deg:.1f}°"
                       + (f", MTF50 {mtf50:.3f} cyc/px" if mtf50 else "")
                       + (f" ({mtf50*1000.0/pitch:.1f} lp/mm)" if (mtf50 and pitch) else "") + ".")
            return
        # USAF mode
        if not state["rois"]:
            status.set("Draw at least one ROI over a three-bar element first.")
            return
        mag = _opt_float(mag_var)
        contrast = _opt_float(contrast_var) or 1.0
        if space == "image" and mag is None:
            status.set("USAF image-space frequency needs a Magnification |m|.")
            return
        rois = [{"group": r["group"], "element": r["element"], "roi": r["roi"], "orientation": r["orientation"],
                 "cycles": r["cycles"], "label": r["label"]} for r in state["rois"]]
        try:
            result = analyze_usaf_image(state["gray"], rois, magnification=mag, pixel_pitch_um=pitch, target_contrast=contrast)
        except Exception as exc:
            status.set(f"Compute failed: {exc}")
            return
        state["result"] = result
        for r, meas in zip(state["rois"], result.measurements):
            r["_mtf"], r["_r2"] = float(meas.mtf), float(meas.fit_r_squared)
        _refresh_tree()
        ax.clear()
        try:
            result.plot(frequency_space=space, ax=ax)
        except Exception as exc:
            status.set(f"Plotted 0 points: {exc}")
        _style_mtf_axes(ax)
        figure.tight_layout()
        plot_canvas.draw()
        status.set(f"Computed {len(result.measurements)} point(s). MTF = image contrast / target contrast ({contrast:g}).")

    def _enlarge_plot() -> None:
        # bugs/0415: match the main-window Analysis curves -- render the current figure to a high-res PNG
        # and open it in the system image viewer (zoom / pan / save there). Works before Compute too
        # (opens the empty axes), but is most useful once a curve is drawn.
        try:
            from KrakenOS.UI.services.layout_import_export import SCREENSHOT_DIR as out_dir
        except Exception:
            out_dir = Path(".")
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        stem = state["path"].stem if state["path"] else "capture"
        image_path = Path(out_dir) / f"kraken_mtf_from_image_{stem}.png"
        try:
            figure.savefig(image_path, dpi=300, bbox_inches="tight")
        except Exception as exc:
            status.set(f"Could not render the enlarged plot: {exc}")
            return
        try:
            editor._open_image_with_system_viewer(image_path)
            status.set(f"Opened enlarged MTF plot in the image viewer: {image_path.name}")
        except Exception as exc:
            status.set(f"Saved {image_path.name}, but the system viewer failed: {exc}")

    def _close() -> None:
        # bugs/0415: explicit teardown -- clear the standalone Figure and destroy the Toplevel.
        try:
            figure.clf()
        except Exception:
            pass
        try:
            window.destroy()
        except Exception:
            pass

    def _save_csv() -> None:
        if state["result"] is None:
            status.set("Compute the MTF before saving.")
            return
        default = (state["path"].with_name(f"{state['path'].stem}_mtf.csv").name if state["path"] else "mtf.csv")
        path = filedialog.asksaveasfilename(title="Save MTF CSV", parent=window, defaultextension=".csv", initialfile=default, filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            state["result"].save_csv(path)
            status.set(f"Saved {Path(path).name}.")
        except Exception as exc:
            status.set(f"Save failed: {exc}")

    root.columnconfigure(1, weight=1)
    root.rowconfigure(3, weight=1)
    # bugs/0415: an explicit close path -- the window-manager close button (some tiling WMs / the
    # centered-dialog helper give no title-bar X) AND Escape both tear the dialog down cleanly.
    window.protocol("WM_DELETE_WINDOW", _close)
    window.bind("<Escape>", lambda _e: _close())
    _on_mode()  # initialise instruction + field enable-state for the default (edge) mode
    try:
        editor._show_centered_dialog(window)
    except Exception:
        pass
