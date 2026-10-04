# 0957 -- one `s` in the Qt shell wrote two flag bundles

Reported 2026-10-04: "I recorded 1 flag, but 2 flags are shown, something wrong with the bug
recording."

## What was on disk

Two bundles, 217 ms apart, with the same cursor position (`vtk_xy [1079, 772]`):

| Bundle | Description |
|---|---|
| `flag_20261004_165651_890` | empty (the extra one) |
| `flag_20261004_165652_107` | the user's text |

217 ms is how long the first flag took to capture its screenshot; the second ran straight after.

## Root cause

Under Qt a key press on the 3D view went down **two routes**:

1. it was forwarded to VTK (`widget.keyPressEvent`), whose interactor observer `_on_key_press`
   handles `s`, Escape and Delete itself;
2. then it was run through the shell's key table (`dispatch_viewport_key`), which binds the same
   three keys.

In the Tk app only one fires: the specific binding (`<KeyPress-s>`) shadows VTK's generic
`<KeyPress>` on the same widget. The Qt route was written to "do both, in Tk's order" for mouse
moves, and keys copied that.

So in the Qt shell, every bound key ran twice:

| Key | Effect of the second run |
|---|---|
| `s` | a second, empty flag bundle |
| Escape | the first run cancelled the active operation, the second cleared the selection |
| Delete | a second delete with nothing selected (no visible effect) |

It dates from the first Qt key routing (bugs/0906). It went unnoticed because bugs were flagged in
the Tk app until the inspector became the Qt shell's own 3D scene (bugs/0951).

## Fix

`InspectorView.handle_event`: a key the inspector binds runs its handler and stops there. Any
other key goes on to VTK, as before.

## Guard

`validate_open3d_0906_qt_hosts_inspector` (phase 694), new claim **K2**: `s`, Escape and Delete
pressed once each on the Qt widget run `['flag', 'cancel', 'delete']` and do not reach VTK's key
observer; an unbound key (F9) runs nothing more and does reach VTK.

**Mutation-checked:** with the forward to VTK restored, K2 reports
`['flag', 'flag', 'cancel', 'cancel', 'delete', 'delete']`.

The older claim K ("Escape cancels an armed pick") passed with the bug in place: it checked that
Escape had an effect, not how many times.

## The extra bundle

`attachment/recorded_bug_repros/flag_20261004_165651_890` is the empty duplicate. It is left on
disk (it is the user's data); it can be deleted.
