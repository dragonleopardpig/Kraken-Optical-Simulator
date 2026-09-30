# 0933 -- the CAD/STL face-roles editor becomes a session + preview (Qt phase 5g, part 1)

The face-roles editor ("Assign CAD/STL Optical Faces") was one 1 900-line Tk method. Its state
lived in closures and Tk variables: the records, the selection, the form, the messages. The VTK
preview was built inside it too. None of it could reach the Qt shell.

## The split

| Module | What it owns |
|---|---|
| `face_roles_session.py` (`FaceRolesSession`) | the records and groups, the selection, the form as plain values, the three message lines, every action (apply, auto-apply, persist, save + auto-orient, suggestions, clear, the virtual plane, input snap, source / illumination binding, summary) |
| `face_roles_preview.py` (`FaceRolesPreview`) | the VTK scene (body, faces, per-group edges, the selected face's normal / anchor / U-V gizmo, virtual planes), the pick, the fixed-speed drag orbit |
| `panels/main_optical_solid_face_roles_dialog.py` (`TkFaceRolesView`) | the Tk layout, the table's cell wrapping, the Matplotlib fallback preview, the `s` snapshot key |

How the pieces talk:
- The view writes the widgets into `session.form` before an action, and redraws on `notify`.
- The debounced retrace and the "no side labels" question go through `host_of(editor)`. A Tk
  `after` never fires under the Qt shell.
- `MainOpticalSolidFaceRolesDialog._open_optical_solid_faces_for_row` builds the session. It
  hands the session to `editor.show_face_roles_dialog` when a shell has installed one (0934),
  else it opens the Tk view.

## Proof that nothing changed

A widget-level script drove the OLD dialog (from HEAD) and the NEW one through the same 19 steps:
- select;
- change the function, loss and split, including an invalid split;
- the quick side and port buttons;
- multi-select + Apply;
- Suggest and Apply Suggestions;
- the cube plane;
- Pick In 3D + Zero;
- Save Roles, Auto Guess, Clear, Clear Virtual.

After every step it compared:
- the table cells and selection;
- the saved face metadata;
- the row pose after Save;
- the status line;
- which fields are enabled;
- the virtual planes.

All of these were **identical**. The preview renders are **pixel-identical** at three states: open,
F005 selected (normal arrow, anchor and U-V gizmo drawn) and with a virtual plane (0 of ~9 000
drawn pixels differ).

## Defects found

1. **Every action's message was invisible.** After an action the old dialog rebuilt its table.
   Tk then delivered `<<TreeviewSelect>>`, which re-ran `load_selected` and overwrote the message
   with the face's info line within milliseconds. So these were never readable:
   - "Saved roles. Auto-oriented F005 as the input face ... Tilt=(...)";
   - "Applied Right / Mirror to 3 selected faces";
   - "Updated 7 geometry suggestions";
   - and the rest.

   This was the only difference the parity run found. The new view shows the action's message,
   which is what the code was written to do.
2. **The Matplotlib fallback preview crashed.** It used `le.Poly3DCollection`, `le.MplPath` and
   `le.proj3d`, and `layout_editor` never exported any of them. Without VTK/Tk the editor could
   therefore not open at all: AttributeError on the first draw. The 0933 gate run found it,
   because a second Tk root in the harness process cannot load VTK's Tk package and falls back.
   - Fix: the fallback imports them itself.
   - Guard: M (below).

## Guard

`validate_open3d_face_roles_session`, penta phase **712**. It runs on the Edmund 42779 vendor prism,
with each part in its own process:
- **A**: three quick edits persist at once; no retrace until the host timer, then exactly one.
- **S**: Save cancels that pending retrace and retraces once. Auto-orient turns F005's normal to
  -Z.
- **C**: a custom coating table round-trips, and a preset drops it.
- **I**: Illumination Source (outward) binds with the outward aim; a coating again unbinds it.
- **N**: input snap:
  - arming off an Input Port is refused;
  - a pick on another face is refused;
  - U/V = (1.5, -0.75) for a point placed at (1.5, -0.75).
- **P**: seven preview clicks each select the face they hit, on its plane (0.05 mm max).
- **T**: the Tk table equals `rows()`, and "Applied Left / Uncoated to F005." stays on screen.
- **M**: with VTK/Tk off, the Matplotlib preview draws every face and a click selects.

Mutation-checked:
- an immediate (not debounced) retrace fails A and S;
- an off-by-one actor -> face map fails P.

## Source pins re-pointed

Phases 21, 100, 172, 233, 237, 238 and 655 read the old method's source. They now read the owner
of each claim:
- phase 21: the grouping in `FaceRolesSession._group_faces`, the per-group edges in
  `FaceRolesPreview.render`;
- phase 100: the scrolled form in `TkFaceRolesView`;
- the illumination and coating phases: dialog + session;
- phase 655 (the contract): dialog module + session.

The ungated `validate_open3d_face_assignment_sampling_stability` and `validate_vendor_prism_42779`
(40/40) were re-pointed the same way and pass.
