"""Measure MTF from a captured USAF-1951 image -- interactive "draw ROIs on the image" dialog.

The physics lives in :mod:`KrakenOS.USAFMTF` (each three-bar element -> 1D profile -> Fourier
fundamental -> pi/4 square-wave factor -> MTF). This dialog is the UI: load a captured raster image,
drag a rectangle over each three-bar element (set its group / element / orientation / cycles), then
Compute to fit every ROI and plot the MTF curve; Save CSV writes the per-ROI measurements.

Coordinate model: the image is displayed scaled-to-fit at ``state["scale"]``; ROIs are stored in
ORIGINAL image pixels (canvas coord / scale) so the fit always runs on the full-resolution capture.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np

_MAX_W, _MAX_H = 660, 560  # display cap; large captures are scaled down (analysis stays full-res)
_ORIENTATIONS = ("vertical", "horizontal")


def open_mtf_from_image_dialog(editor) -> None:
    """Open the interactive USAF-1951 "Measure MTF from Image" dialog on ``editor``."""
    try:
        from KrakenOS.USAFMTF import analyze_usaf_image, load_grayscale_image
    except Exception as exc:  # pragma: no cover - defensive
        messagebox.showerror("Measure MTF from Image", f"USAF MTF module unavailable:\n\n{exc}", parent=editor)
        return
    try:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        from PIL import Image, ImageTk
    except Exception as exc:  # pragma: no cover - defensive
        messagebox.showerror("Measure MTF from Image", f"Pillow + matplotlib are required:\n\n{exc}", parent=editor)
        return

    state: dict = {
        "path": None,      # Path of the loaded image
        "gray": None,      # full-res grayscale ndarray for the fit
        "scale": 1.0,      # display scale (canvas px / image px)
        "photo": None,     # ImageTk ref (keep alive vs Tk GC)
        "rois": [],        # [{group, element, orientation, cycles, roi:(x0,y0,x1,y1 image px), rect_id, label_id}]
        "result": None,
    }

    window = tk.Toplevel(editor)
    window.title("Measure MTF from Image (USAF-1951)")
    window.transient(editor)
    root = ttk.Frame(window, padding=8)
    root.grid(row=0, column=0, sticky="nsew")

    # --- top toolbar: import + the "settings for the NEXT drawn ROI" ---
    bar = ttk.Frame(root)
    bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
    ttk.Button(bar, text="Import Image...", command=lambda: _load_image()).grid(row=0, column=0)
    ttk.Label(bar, text="  Next ROI →  Group").grid(row=0, column=1, padx=(10, 2))
    group_var = tk.StringVar(value="2")
    ttk.Entry(bar, textvariable=group_var, width=4).grid(row=0, column=2)
    ttk.Label(bar, text="Element").grid(row=0, column=3, padx=(8, 2))
    element_var = tk.StringVar(value="1")
    ttk.Entry(bar, textvariable=element_var, width=4).grid(row=0, column=4)
    ttk.Label(bar, text="Bars").grid(row=0, column=5, padx=(8, 2))
    orient_var = tk.StringVar(value="vertical")
    ttk.Combobox(bar, textvariable=orient_var, values=list(_ORIENTATIONS), state="readonly", width=10).grid(row=0, column=6)
    ttk.Label(bar, text="Cycles").grid(row=0, column=7, padx=(8, 2))
    cycles_var = tk.StringVar(value="3")
    ttk.Entry(bar, textvariable=cycles_var, width=4).grid(row=0, column=8)

    # --- left: the image canvas (draw ROIs here) ---
    canvas = tk.Canvas(root, width=_MAX_W, height=_MAX_H, background="#20242b", highlightthickness=1, highlightbackground="#3a4150")
    canvas.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
    hint = canvas.create_text(_MAX_W // 2, _MAX_H // 2, text="Import a captured USAF-1951 image,\nthen drag a rectangle over each three-bar element.", fill="#8a93a3", justify="center")

    # --- right: ROI list + calibration + compute + plot ---
    right = ttk.Frame(root)
    right.grid(row=1, column=1, sticky="nsew")
    right.columnconfigure(0, weight=1)

    ttk.Label(right, text="ROIs (one three-bar element each):").grid(row=0, column=0, sticky="w")
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
    space_var = tk.StringVar(value="object")
    for r, (lbl, var, w) in enumerate((
        ("Magnification |m| (for image-space)", mag_var, 10),
        ("Pixel pitch [µm]", pitch_var, 10),
        ("Target contrast (0-1]", contrast_var, 10),
    )):
        ttk.Label(calib, text=lbl).grid(row=r, column=0, sticky="w", pady=1)
        ttk.Entry(calib, textvariable=var, width=w).grid(row=r, column=1, sticky="e", pady=1, padx=(8, 0))
    ttk.Label(calib, text="Frequency axis").grid(row=3, column=0, sticky="w", pady=1)
    ttk.Combobox(calib, textvariable=space_var, values=("object", "image"), state="readonly", width=10).grid(row=3, column=1, sticky="e", pady=1, padx=(8, 0))

    action = ttk.Frame(right)
    action.grid(row=4, column=0, sticky="ew", pady=(8, 4))
    ttk.Button(action, text="Compute MTF", command=lambda: _compute()).grid(row=0, column=0)
    ttk.Button(action, text="Save CSV...", command=lambda: _save_csv()).grid(row=0, column=1, padx=(6, 0))
    status = tk.StringVar(value="Import a captured USAF-1951 raster image to begin.")
    ttk.Label(right, textvariable=status, foreground="#475569", wraplength=320, justify="left").grid(row=5, column=0, sticky="ew", pady=(2, 6))

    figure = Figure(figsize=(3.6, 2.6), dpi=100)
    ax = figure.add_subplot(111)
    ax.set_title("USAF-1951 MTF")
    ax.set_xlabel("lp/mm")
    ax.set_ylabel("MTF")
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, alpha=0.25)
    plot_canvas = FigureCanvasTkAgg(figure, master=right)
    plot_canvas.get_tk_widget().grid(row=6, column=0, sticky="nsew")
    right.rowconfigure(6, weight=1)

    # ------------------------------------------------------------------ helpers
    def _load_image() -> None:
        path = filedialog.askopenfilename(
            title="Import captured USAF-1951 image",
            parent=window,
            filetypes=[("Images", "*.png *.tif *.tiff *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            gray = load_grayscale_image(path)          # full-res, for the fit
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
        status.set(f"Loaded {Path(path).name} ({w}×{h}px, shown at {scale:.2f}×). Drag a rectangle over a three-bar element.")

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
        if (cx1 - cx0) < 6 or (cy1 - cy0) < 6:
            status.set("ROI too small -- drag a larger rectangle over the whole three-bar element.")
            return
        s = state["scale"]
        roi_px = (round(cx0 / s, 1), round(cy0 / s, 1), round(cx1 / s, 1), round(cy1 / s, 1))
        try:
            group = int(group_var.get())
            element = int(element_var.get())
            cycles = float(cycles_var.get())
            orientation = str(orient_var.get()).strip().lower()
            if orientation not in _ORIENTATIONS or not 1 <= element <= 6 or cycles <= 0:
                raise ValueError
        except (TypeError, ValueError):
            status.set("Set a valid Group (int), Element (1-6), Bars, and Cycles (>0) before drawing.")
            return
        rect_id = canvas.create_rectangle(cx0, cy0, cx1, cy1, outline="#22d3ee", width=2)
        label_id = canvas.create_text(cx0 + 3, cy0 + 8, anchor="w", text=f"G{group}E{element} {orientation[0].upper()}", fill="#22d3ee", font=("TkDefaultFont", 8))
        state["rois"].append({
            "group": group, "element": element, "orientation": orientation, "cycles": cycles,
            "roi": roi_px, "label": f"G{group}E{element}", "rect_id": rect_id, "label_id": label_id,
        })
        # auto-advance element so drawing E1..E6 of a group is quick
        element_var.set(str(element + 1 if element < 6 else 1))
        _refresh_tree()
        status.set(f"Added ROI G{group}E{element} ({orientation}). {len(state['rois'])} ROI(s); Compute when ready.")

    canvas.bind("<ButtonPress-1>", _on_press)
    canvas.bind("<B1-Motion>", _on_motion)
    canvas.bind("<ButtonRelease-1>", _on_release)

    def _refresh_tree() -> None:
        tree.delete(*tree.get_children())
        for i, r in enumerate(state["rois"]):
            roi = r["roi"]
            m = r.get("_mtf")
            r2 = r.get("_r2")
            tree.insert("", "end", iid=str(i), values=(
                r["group"], r["element"], r["orientation"],
                f"{roi[0]:g},{roi[1]:g},{roi[2]:g},{roi[3]:g}",
                "" if m is None else f"{m:.3f}", "" if r2 is None else f"{r2:.3f}",
            ))

    def _delete_selected() -> None:
        sel = tree.selection()
        if not sel:
            return
        i = int(sel[0])
        r = state["rois"].pop(i)
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
        if not state["rois"]:
            status.set("Draw at least one ROI over a three-bar element first.")
            return
        mag = _opt_float(mag_var)
        pitch = _opt_float(pitch_var)
        contrast = _opt_float(contrast_var) or 1.0
        space = str(space_var.get())
        if space == "image" and mag is None:
            status.set("Image-space frequency needs a Magnification |m|.")
            return
        rois = [{"group": r["group"], "element": r["element"], "roi": r["roi"],
                 "orientation": r["orientation"], "cycles": r["cycles"], "label": r["label"]}
                for r in state["rois"]]
        try:
            result = analyze_usaf_image(state["gray"], rois, magnification=mag, pixel_pitch_um=pitch, target_contrast=contrast)
        except Exception as exc:
            status.set(f"Compute failed: {exc}")
            return
        state["result"] = result
        for r, meas in zip(state["rois"], result.measurements):
            r["_mtf"] = float(meas.mtf)
            r["_r2"] = float(meas.fit_r_squared)
        _refresh_tree()
        ax.clear()
        try:
            result.plot(frequency_space=space, ax=ax)
        except Exception as exc:
            status.set(f"Plotted 0 points: {exc}")
        ax.set_ylim(0.0, 1.05)
        figure.tight_layout()
        plot_canvas.draw()
        status.set(f"Computed {len(result.measurements)} point(s). Target contrast {contrast:g}; MTF = image contrast / target contrast.")

    def _save_csv() -> None:
        if state["result"] is None:
            status.set("Compute the MTF before saving.")
            return
        default = (state["path"].with_name(f"{state['path'].stem}_mtf.csv").name if state["path"] else "usaf_mtf.csv")
        path = filedialog.asksaveasfilename(title="Save MTF CSV", parent=window, defaultextension=".csv", initialfile=default, filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            state["result"].save_csv(path)
            status.set(f"Saved {Path(path).name}.")
        except Exception as exc:
            status.set(f"Save failed: {exc}")

    root.columnconfigure(1, weight=1)
    root.rowconfigure(1, weight=1)
    try:
        editor._show_centered_dialog(window)
    except Exception:
        pass
