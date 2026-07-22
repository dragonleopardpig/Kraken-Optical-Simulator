# 0413 — Right-click popup "flashes and disappears" on the 3D scene

**Flag `flag_20260722_202748_266`** (build `edb1943b`, AZ85 RA-mirror scene):
> "I don't really know when this happen, sometime right click the pop up just flash and disappear."

Intermittent: a 3D right-click context menu opens and vanishes in the same instant, before the user can
click an entry.

## Root cause — focus churn the moment the menu posts

`_popup_context_menu` (the inspector's robust popup, shared by the Scene-Components menus and the
face-assignment menu) posts via `menu.tk_popup(...)`, which grabs pointer **and focus**. Since bugs/0336
(VTK swallows the click a held grab needs to self-unpost → menu sticks) it then released that grab
**synchronously** in the same `finally`.

On a **focus-follows-mouse** window manager, dropping the grab in the same breath as posting lets focus
bounce straight off the just-mapped menu. Tk's built-in `Menu` class has a `<FocusOut>` binding that
**auto-unposts** the menu on focus loss — so the menu appears and is torn down one event-loop turn later.
It "flashes and disappears." It's intermittent because whether focus bounces depends on WM timing and
pointer position at post time.

Our own `<FocusOut>` dismiss (added for click-onto-another-window) made it worse: it fired on that same
spurious post-time bounce.

## Fix — hold the grab through the settle, and ignore the churn focus-out

Two complementary guards (`open3d_face_assignment.py`):

1. **Defer the grab release.** Hold `tk_popup`'s grab for a short settle window
   (`_CONTEXT_MENU_GRAB_SETTLE_MS`, default **150 ms**, env-tunable) before releasing it, so focus stays
   pinned on the menu through the post-time churn and Tk's auto-unpost never triggers. Released
   afterwards so the bugs/0336 click-on-VTK dismiss still works. Existence-guarded — an entry-click
   teardown (bugs/0348) may already have destroyed the menu by the time the timer fires.

2. **Grace-guard our `<FocusOut>` dismiss.** A focus-out that lands **within** the settle window is
   ignored (the spurious bounce); a genuine later click-away still dismisses. `<Unmap>` — a real unpost
   or an entry-click invoke (bugs/0348) — is deliberately **left unguarded**, so menu-entry delivery is
   completely untouched.

Nothing else changes: the primary left/middle-press dismiss (bugs/0341) and the VTK-widget `<Button>`
binds are as before. The only behavioural cost is that a dismiss-click landing in the first ~150 ms may
need a second click — imperceptible in practice, and it self-heals.

## Verification (`validate_open3d_context_menu_no_flash`, penta phase 337)

Display-free (the live focus race is WM-specific and can't run headless — VTK segfaults under Xvfb — so
the guard pins the *mechanism*):

| check | asserts |
|---|---|
| SETTLE-POSITIVE | the default grab-settle window is > 0 (a 0 reinstates the synchronous-release flash) |
| GRAB-DEFERRED | the grab release is scheduled via `menu.after(settle, …)`, not dropped synchronously |
| FOCUSOUT-GUARDED | `<FocusOut>` binds the settle-guarded handler; `<Unmap>` stays the plain entry-safe dismiss |
| GRACE-LOGIC | a focus-out at +0 s is ignored; one well after the settle dismisses |

4/4 pass. Baseline records phase 337 = pass.

## Files

- `KrakenOS/UI/services/open3d_face_assignment.py` — deferred grab release + `<FocusOut>` settle grace + `_CONTEXT_MENU_GRAB_SETTLE_MS`.
- `KrakenOS/UI/validate_open3d_context_menu_no_flash.py` — guard (phase 337).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — register phase 337.
- `tools/penta_validator_baseline.json` — phase 337 = pass.

## In-app eyeball still owed / please confirm

Right-click repeatedly on the 3D scene (and on Scene-Components rows) → the menu **stays up** every time
until you click an entry or click away. Because the underlying trigger is a WM focus race I can't
reproduce headless — **and the flag build was `dirty`** — please pull this and confirm the flash is gone.
If it still flashes on a specific menu, capture a fresh recording: the residual would be a path the grab
hold didn't cover (I'd then trial `KRAKEN_CONTEXT_MENU_GRAB_SETTLE_MS` higher, e.g. 250).
