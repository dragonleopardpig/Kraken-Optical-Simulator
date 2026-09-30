# 0934 -- the CAD/STL face-roles editor in the Qt shell (phase 5g, part 2)

0933 made the editor a toolkit-neutral `FaceRolesSession` + `FaceRolesPreview`. This adds the Qt
view over them.

- **Dialog.** `qt/dialogs/face_roles_dialog.py` (`FaceRolesDialog`) has the Tk layout:
  - the face table;
  - the 3D preview;
  - the scrollable assignment form (choices, input snap + Pick / Zero, the text fields, coating +
    "Edit table…", Flip, Notes, auto-orient, the quick side / port buttons, the five actions,
    the virtual plane);
  - the footer.

  The per-face coating-table editor is a small Qt dialog validated by
  `parse_face_coating_table`, the Tk editor's own check.
- **Opening it.** Every route opens it: the inspector's "Faces", its face menu, and the new
  **Edit -> Assign CAD/STL Optical Faces...**. They all reach `_open_optical_solid_faces_for_row`,
  which hands its session to `editor.show_face_roles_dialog`, installed by the main window.
- **Preview input.** The preview is a `QVTKRenderWindowInteractor` running the same
  `FaceRolesPreview`. Left press / drag / release go to the preview in VTK display coordinates:
  a click picks, a drag orbits at the fixed Open 3D rate. A do-nothing interactor style keeps
  VTK's trackball from turning the camera as well. The wheel is still VTK's zoom.

## Rules it follows

- **The table's items are made once.** A sync only rewrites their texts and selection, with
  signals blocked, so no item a selection signal holds is ever deleted (the 0932 segfault).
- **The VTK widget is built after the dialog is shown** (`build_preview`). VTK takes the native
  window id in its constructor.
- **Commits.** `activated` (a user's choice) and `editingFinished` (Return or leaving the field)
  are the Tk `<<ComboboxSelected>>` / `<Return>` / `<FocusOut>` commits. A sync's own
  `setCurrentText` / `setText` fires neither.
- **Values not in the list.** A value a read-only combo does not list (a legacy load) is added
  and shown, as a Tk readonly combobox shows any value its variable holds, so it round-trips
  unchanged.
- **Closing does not cancel a pending debounced retrace.** An edit made just before closing still
  reaches Open 3D; the Tk dialog behaves the same.

## Guard

`validate_open3d_qt_5g_face_roles`, penta phase **713**. It runs in a real Qt shell on the Edmund
42779 prism, with real `QTest` input:
- **O**: Edit -> Assign opens the Qt dialog with its VTK preview; no Tk face window is shown.
- **V**: the table cells are `rows()`; a click on F003's row selects it and loads its form.
- **F**: choosing "Partial Reflecting / Transmitting" and typing loss 0.25 + Return persist at once
  (Beam Splitter, 0.25). The retrace fires once, on the Qt timer.
- **P**: a click on a face that is NOT selected selects the face the preview's pick names; a drag
  orbits the camera 28.5 mm and leaves the selection alone.
- **S**: the Save Roles button turns F005's world normal to -Z, and "Saved roles. Auto-oriented…"
  stays on screen.
- **T**: the same actions through the Tk view and the Qt view save identical metadata for all 7
  faces.

Mutation-checked:
- the retrace on Tk's own `editor.after`: F fails, since nothing pumps Tk under Qt;
- preview input not routed: P fails.

Found while writing it (guard mechanics, not product bugs):
- a `QTreeWidget` row rect spans every column, so its centre can lie outside the viewport;
- a synthetic Tk `<Return>` reaches only the FOCUSED entry, as a real keypress does.

A screenshot of the dialog on the prism with F005 selected was checked by eye: the table, the
preview with F005's edge, normal and U-V gizmo, the form with split / loss / phase disabled for
Uncoated, and the footer.
