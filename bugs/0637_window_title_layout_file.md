# 0637 — the loaded layout file now shows in the window title (user report)

User: *"after loading a .py file, there is no mention anywhere of the loaded file name."*

The window title was set once to "KrakenOS Layout Editor" (layout_editor.py) and never
updated; `current_layout_file` was displayed nowhere. Added `_update_window_title()`
(layout_table_workbench) — sets the title to "KrakenOS Layout Editor — <file.py>", or
"… — <file.py> (unsaved import)" for a transient lens/camera import (bugs/0375), or the
base title when nothing is loaded. Called from every load/save/reset path:
`load_layout_by_name`, `open_layout`, the Zemax `.zmx`/rayfile loaders, `save_layout`,
`save_layout_as`, `reset_layout`.

Verified: guard phase 476 (`validate_open3d_0637_window_title`) — the title strings
(loaded / unsaved-import / base) via a stub, and the contract that all six paths update it.
