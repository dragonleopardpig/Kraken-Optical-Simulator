"""Measure MTF from a captured image -- the Tk view (bugs/0411, 0938).

The image, the mode, the ROIs (in ORIGINAL image pixels), the fits, the plot and the CSV are
`mtf_from_image_session.MtfFromImageSession`; this lays it out in Tk and forwards the mouse. The Qt
shell renders the same session in `qt/dialogs/mtf_from_image_dialog.py`.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from KrakenOS.UI import mtf_from_image_session as mfs

#: kept under its old name: phase 335 styles an axis through it
_style_mtf_axes = mfs.style_mtf_axes


def open_mtf_from_image_dialog(editor) -> "TkMtfFromImageView | None":
    """Open the interactive "Measure MTF from Image" dialog on ``editor``."""
    try:
        import KrakenOS.EdgeMTF  # noqa: F401
        import KrakenOS.USAFMTF  # noqa: F401
    except Exception as exc:  # pragma: no cover - defensive
        messagebox.showerror(mfs.TITLE, f"MTF modules unavailable:\n\n{exc}", parent=editor)
        return None
    try:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: F401
        from PIL import ImageTk  # noqa: F401
    except Exception as exc:  # pragma: no cover - defensive
        messagebox.showerror(mfs.TITLE, f"Pillow + matplotlib are required:\n\n{exc}", parent=editor)
        return None
    view = TkMtfFromImageView(editor, mfs.MtfFromImageSession(editor))
    editor.__dict__["_mtf_from_image_view"] = view   # the open dialog, for a guard to drive
    return view


class TkMtfFromImageView:
    def __init__(self, editor, session) -> None:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        self.editor, self.session = editor, session
        self.photo = None
        self._drag = None
        self._band = None
        window = self.window = tk.Toplevel(editor)
        window.title(mfs.TITLE)
        window.transient(editor)
        root = ttk.Frame(window, padding=8)
        root.grid(row=0, column=0, sticky="nsew")

        # --- top: import + target-type mode + the USAF "next ROI" fields ---
        bar = ttk.Frame(root)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(bar, text="Import Image...", command=self.import_image).grid(row=0, column=0)
        ttk.Label(bar, text="   Target:").grid(row=0, column=1, padx=(8, 2))
        self.mode_var = tk.StringVar(master=window, value=session.mode)
        for column, (text, value) in enumerate((("Slanted edge", "edge"), ("USAF three-bar", "usaf")), start=2):
            ttk.Radiobutton(bar, text=text, variable=self.mode_var, value=value,
                            command=lambda: session.set_mode(self.mode_var.get())).grid(row=0, column=column, padx=(4 if column > 2 else 0, 0))

        self.usaf_fields = ttk.Frame(root)
        self.usaf_fields.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.field_vars = {key: tk.StringVar(master=window, value=value) for key, value in session.fields.items()}
        for column, (label, key, width) in enumerate((("Next ROI →  Group", "group", 4), ("Element", "element", 4),
                                                      ("Bars", "orientation", 10), ("Cycles", "cycles", 4))):
            ttk.Label(self.usaf_fields, text=label).grid(row=0, column=2 * column, padx=(8 if column else 0, 2))
            if key == "orientation":
                widget = ttk.Combobox(self.usaf_fields, textvariable=self.field_vars[key], values=list(mfs.ORIENTATIONS),
                                      state="readonly", width=width)
            else:
                widget = ttk.Entry(self.usaf_fields, textvariable=self.field_vars[key], width=width)
            widget.grid(row=0, column=2 * column + 1)

        self.instruction_var = tk.StringVar(master=window, value=session.instruction)
        ttk.Label(root, textvariable=self.instruction_var, foreground="#1d4ed8", wraplength=1000, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 4))
        canvas = self.canvas = tk.Canvas(root, width=mfs.MAX_DISPLAY[0], height=mfs.MAX_DISPLAY[1], background="#20242b",
                                         highlightthickness=1, highlightbackground="#3a4150")
        canvas.grid(row=3, column=0, sticky="nsew", padx=(0, 8))
        canvas.bind("<ButtonPress-1>", self._on_press)
        canvas.bind("<B1-Motion>", self._on_motion)
        canvas.bind("<ButtonRelease-1>", self._on_release)

        right = ttk.Frame(root)
        right.grid(row=3, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="ROIs:").grid(row=0, column=0, sticky="w")
        tree = self.tree = ttk.Treeview(right, columns=[c for c, _t, _w in mfs.ROI_COLUMNS], show="headings",
                                        height=7, selectmode="browse")
        for column, title, width in mfs.ROI_COLUMNS:
            tree.heading(column, text=title)
            tree.column(column, width=width, anchor="w")
        tree.grid(row=1, column=0, sticky="ew")
        roi_buttons = ttk.Frame(right)
        roi_buttons.grid(row=2, column=0, sticky="w", pady=(3, 8))
        ttk.Button(roi_buttons, text="Delete ROI", command=self.delete_selected).grid(row=0, column=0)
        ttk.Button(roi_buttons, text="Clear All", command=lambda: session.clear_rois()).grid(row=0, column=1, padx=(6, 0))

        calib = ttk.LabelFrame(right, text="Calibration (optional)", padding=6)
        calib.grid(row=3, column=0, sticky="ew")
        self.calibration_vars = {key: tk.StringVar(master=window, value=value) for key, value in session.calibration.items()}
        rows = [(label, ttk.Entry, key) for key, label in mfs.CALIBRATION_FIELDS] + [("Frequency axis", ttk.Combobox, "space")]
        for index, (label, kind, key) in enumerate(rows):
            row = ttk.Frame(calib)
            ttk.Label(row, text=label).grid(row=0, column=0, sticky="w")
            if kind is ttk.Combobox:
                widget = self.space_combo = ttk.Combobox(row, textvariable=self.calibration_vars[key], state="readonly", width=10)
            else:
                widget = ttk.Entry(row, textvariable=self.calibration_vars[key], width=10)
            widget.grid(row=0, column=1, sticky="e", padx=(8, 0))
            row.grid(row=index, column=0, sticky="ew", pady=1)
            row.columnconfigure(0, weight=1)

        action = ttk.Frame(right)
        action.grid(row=4, column=0, sticky="ew", pady=(8, 4))
        ttk.Button(action, text="Compute MTF", command=lambda: self._act(session.compute)).grid(row=0, column=0)
        ttk.Button(action, text="Save CSV...", command=self.save_csv).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(action, text="Close", command=lambda: self._close()).grid(row=0, column=2, padx=(6, 0))
        self.status_var = tk.StringVar(master=window, value=session.status)
        ttk.Label(right, textvariable=self.status_var, foreground="#475569", wraplength=320, justify="left").grid(
            row=5, column=0, sticky="ew", pady=(2, 6))

        self.figure = Figure(figsize=(3.6, 2.6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.plot_canvas = FigureCanvasTkAgg(self.figure, master=right)
        plot_widget = self.plot_widget = self.plot_canvas.get_tk_widget()
        plot_widget.grid(row=6, column=0, sticky="nsew")
        # bugs/0415: click the curve to enlarge it, matching the main-window Analysis curves (render a
        # high-res PNG + open in the system image viewer). The hand cursor signals it is clickable.
        plot_widget.configure(cursor="hand2")
        plot_widget.bind("<Button-1>", lambda _e: session.enlarge(self.figure))
        ttk.Label(right, text=mfs.ENLARGE_HINT, foreground="#64748b", font=("TkDefaultFont", 8)).grid(
            row=7, column=0, sticky="w", pady=(1, 0))
        right.rowconfigure(6, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(3, weight=1)
        # bugs/0415: an explicit close path -- the window-manager close button (some tiling WMs / the
        # centered-dialog helper give no title-bar X) AND Escape both tear the dialog down cleanly.
        window.protocol("WM_DELETE_WINDOW", self._close)
        window.bind("<Escape>", lambda _e: self._close())
        session.listeners.append(self.sync)
        session.set_mode(session.mode)   # instruction + field enable-state for the default (edge) mode
        try:
            editor._show_centered_dialog(window)
        except Exception:
            pass

    # ---- widgets <-> session ---------------------------------------------------------------------
    def _push(self) -> None:
        for key, var in self.field_vars.items():
            self.session.fields[key] = str(var.get())
        for key, var in self.calibration_vars.items():
            self.session.calibration[key] = str(var.get())

    def _act(self, action, *args):
        self._push()
        return action(*args)

    def sync(self) -> None:
        session = self.session
        try:
            if not self.window.winfo_exists():
                return
        except tk.TclError:
            return
        self.mode_var.set(session.mode)
        edge = session.mode == "edge"
        for child in self.usaf_fields.winfo_children():
            try:
                child.configure(state="disabled" if edge else ("readonly" if isinstance(child, ttk.Combobox) else "normal"))
            except tk.TclError:
                pass
        for key, var in self.field_vars.items():
            if var.get() != session.fields[key]:
                var.set(session.fields[key])
        self.space_combo.configure(values=session.frequency_spaces())
        for key, var in self.calibration_vars.items():
            if var.get() != session.calibration[key]:
                var.set(session.calibration[key])
        self.instruction_var.set(session.instruction)
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(session.roi_rows()):
            self.tree.insert("", "end", iid=str(index), values=row)
        self._draw_image_and_rois()
        session.draw(self.ax)
        self.figure.tight_layout()
        self.plot_canvas.draw()
        self.status_var.set(session.status)

    def _draw_image_and_rois(self) -> None:
        from PIL import ImageTk

        canvas, session = self.canvas, self.session
        canvas.delete("all")
        if session.path is None:
            self.photo = None
            return
        if self.photo is None or getattr(self, "_photo_path", None) != session.path:
            self.photo = ImageTk.PhotoImage(session.display_rgb(), master=self.window)
            self._photo_path = session.path
        canvas.create_image(0, 0, anchor="nw", image=self.photo)
        for index in range(len(session.rois)):
            x0, y0, x1, y1 = session.roi_display_box(index)
            canvas.create_rectangle(x0, y0, x1, y1, outline="#22d3ee", width=2)
            canvas.create_text(x0 + 3, y0 + 8, anchor="w", text=session.roi_caption(index), fill="#22d3ee",
                               font=("TkDefaultFont", 8))

    # ---- actions -------------------------------------------------------------------------------------
    def import_image(self) -> None:
        path = filedialog.askopenfilename(title="Import captured MTF-target image", parent=self.window,
                                          filetypes=mfs.IMAGE_FILETYPES)
        if path:
            self._act(self.session.load_image, path)

    def _on_press(self, event):
        if self.session.gray is None:
            return
        self._drag = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        self._band = self.canvas.create_rectangle(*self._drag, *self._drag, outline="#22d3ee", width=2, dash=(3, 2))

    def _on_motion(self, event):
        if self._band is None:
            return
        x0, y0 = self._drag
        self.canvas.coords(self._band, x0, y0, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def _on_release(self, event):
        band, self._band = self._band, None
        if band is None:
            return
        self.canvas.delete(band)
        x0, y0 = self._drag
        self._act(self.session.add_roi_display, x0, y0, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def delete_selected(self) -> None:
        selection = self.tree.selection()
        if selection:
            self.session.delete_roi(int(selection[0]))

    def save_csv(self) -> None:
        if self.session.result is None:
            self.session.save_csv("")          # sets "Compute the MTF before saving."
            return
        path = filedialog.asksaveasfilename(title="Save MTF CSV", parent=self.window, defaultextension=".csv",
                                            initialfile=self.session.default_csv_name(), filetypes=[("CSV", "*.csv")])
        if path:
            self.session.save_csv(path)

    def _close(self) -> None:
        # bugs/0415: explicit teardown -- clear the standalone Figure and destroy the Toplevel.
        if self.sync in self.session.listeners:
            self.session.listeners.remove(self.sync)
        try:
            self.figure.clf()
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass
