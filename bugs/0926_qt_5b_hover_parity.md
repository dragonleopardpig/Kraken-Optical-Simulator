# 0926 -- hover and pick results match Tk in the Qt shell (phase 5b)

5b was scoped as "the event half landed with 0906; prove the RESULTS match Tk":
- face vs edge highlight;
- the hover status text;
- the thickness-handle and nav-cube hovers;
- moving the inspector's hidden Tk status line into the shell.

## Measured -- no port needed

**The status line.** The inspector's only Tk-displayed variables are `status_var` and the CAD/STL
placement panel's (moved in 0925). `status_var` has reached the shell's status bar since 0906
(`InspectorView(..., status=statusBar().showMessage)`). The hover text is a VTK text actor in the
viewport itself, so it shows in Qt as-is.

**The results.** Each scene is swept twice along the identical path:
- with real Qt input;
- with the Tk bindings' own sequence (the VTK interactor gets the motion first, which runs its
  hover-pick observer and the nav cube, then the `hover` handler is dispatched; Alt via
  `alt_press` plus the state bit).

After every move the full hover state is snapshotted.

| scene | pixels | hovered | Qt vs Tk | notes |
|---|---|---|---|---|
| om05a_folded + thickness dims | 217 | 60 scene features, cube cells 1/3/4/12/16/24/25, 5 thickness handles | 0 differ | |
| vendor LED STEP, plain | 216 | 192 | 0 differ | |
| vendor LED STEP, Alt | 216 | 192 | 0 differ | Alt changes the highlight at 190 pixels |

## Three measurement traps (all in the guard, none in the product)

1. **Class names alone pass vacuously.** A face outline and an edge highlight are both a
   `vtkOpenGLActor`. The first probe saw "Alt changes nothing" everywhere. The outline's GEOMETRY
   tells them apart: plain = (212 polys ...), Alt = (0 polys, N lines).
2. **Sticky status.** A thickness handle's status message ("S10 Thickness handle -- drag to
   adjust...") stays after the pointer leaves it, IN BOTH SHELLS. So the second sweep inherited the
   first's last message. The guard resets the status before each sweep. (UX nit, both shells, not
   changed here.)
3. **Lazily created attributes.** Hover attributes are created the first time they are used, so
   the sweep that runs first lacks keys the second has. The inspector reads them with
   `__dict__.get()`, so an absent attribute IS None. The guard also compares as JSON, because a
   field can hold a float NaN, and NaN != NaN.

**Mutation check:** dropping the Qt shell's `hover` dispatch makes H fail with 217/217 steps
different, no cube cell and no thickness handle hovered.

## Guard

`validate_open3d_qt_5b_hover_parity`, penta phase **705**. Two Qt subprocesses:
- **H**: om05a with thickness dimensions: raster + nav-cube corner + each handle's projected
  centre.
- **E**: the LED, plain and Alt.

It has non-vacuity floors: at least 20 hovered, at least 3 cube cells, at least 1 thickness handle;
and Alt must change the highlight at half of the hovered pixels or more.
