# 0946 -- the build stamp could strand `.git/index.lock`: "can't git pull"

Reported 2026-10-03 on M90aPro: "can't git pull". It was also the unexplained failure of
2026-09-27 on the same machine.

```
error: Unable to create '.../Kraken-Optical-Simulator/.git/index.lock': File exists.
Another git process seems to be running in this repository ...
```

## What was on disk

- The lock was 0 bytes, dated 09-27 21:35, with no git process running and the machine booted 20
  minutes earlier. Removing it let the pull through (33 commits, fast-forward).
- Then it **came back**: a new 0-byte lock at 20:17:48, again with no git process alive, and the
  next `git commit` failed.
- It was not Filen. Its four sync roots do not include the repository, and its log never mentions
  the file.

## Root cause

`open3d_inspector._open3d_running_build_stamp()` runs **at import** (bugs/0501: the stamp must
describe the code that was loaded). It asks git four questions under `timeout=2.0`. One of them is
`git status --porcelain`.

- `git status` is not a pure read. It takes `.git/index.lock` and holds it for the whole of its
  working-tree walk, so that it can save a refreshed index afterwards.
- `subprocess.run(..., timeout=2.0)` **kills** a child that overruns (SIGKILL). A killed git cannot
  remove its lock.
- From then on every git command in the checkout fails until someone deletes the file.

So every app start, every validator and every guard subprocess rolled that die. It loses when the
walk is slow: a cold cache under disk pressure. At 20:17 the machine was 20 minutes past boot with
I/O pressure at 35% (`/proc/pressure/io`, Filen catching up), and a guard's subprocess was importing
the inspector.

**Reproduced** in a throwaway repository, killing `git status` part-way through its walk:

| Query | `index.lock` left behind |
|---|---|
| `git status --porcelain` | 4 of 5 kills |
| `git --no-optional-locks status --porcelain` | 0 of 5 kills |

## Fix

The stamp's queries go through one helper, `_build_stamp_git`, which runs
`git --no-optional-locks -C <repo> ...`. That is git's own switch for background callers: status
still answers, but never takes the lock, so there is nothing to leave behind.

Also: a status that does not answer is now recorded as `dirty: None` (unknown). Before, a timeout
read as `dirty: False`, which claims a clean tree.

## Guard: `validate_open3d_0946_build_stamp_takes_no_git_lock` (phase 720)

Display-free, in a throwaway repository:
- **N:** with a tracked file whose timestamp changed, the stamp's status answers "clean" and leaves
  `.git/index` byte- and mtime-identical, with no lock.
- **C:** the control. Plain `git status` in the same situation DOES rewrite the index, so it is a
  lock-taking query and N is a real test.
- **K:** a query killed at its timeout returns None, raises nothing and leaves no lock.
- **D:** the answers stay truthful: clean, an edited file's porcelain line, the commit hash.
- **U:** an unanswered status gives `dirty = None`.
- **R:** in the real checkout the stamp resolves HEAD and leaves no lock.

**Mutation-checked:** with the flag removed, N fails (the index is rewritten).

## If it happens on another host

A checkout that has not pulled this fix can still strand the lock. Check that the lock is stale,
then remove it:

```
ls -la .git/index.lock        # 0 bytes, and not from this minute
ps -e | grep -w git           # nothing running
rm .git/index.lock
```
