"""Guard for bugs/0946: the build stamp must never leave `.git/index.lock` behind.

`open3d_inspector` stamps the running build at IMPORT with a few git queries under a 2-second
timeout. `git status` holds `.git/index.lock` for its whole tree walk so that it can save a refreshed
index; one that outlived the timeout was KILLED, the lock stayed, and every later git command in the
checkout failed -- "can't git pull" on M90aPro, twice (2026-09-27 and 2026-10-03). The queries now
run with `--no-optional-locks`. In a throwaway repository, display-free:

  N  with a tracked file whose timestamp changed (content the same), the stamp's own status query
     answers "clean" and leaves `.git/index` byte- and mtime-identical, with no `index.lock`
  C  the control that gives N its teeth: the SAME query with optional locks on does rewrite the
     index in that situation -- so it is a query that takes the lock
  K  a query killed at its timeout returns None, raises nothing, and leaves no lock
  D  the query still tells the truth: clean -> "", an edited file -> its porcelain line, and
     `rev-parse` -> the commit
  U  a status that did not answer is recorded as dirty = None (unknown), never as clean
  R  in the real checkout the stamp resolves HEAD's short hash and leaves no lock
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

GIT_ID = ("-c", "user.name=guard", "-c", "user.email=guard@example.invalid", "-c", "commit.gpgsign=false")


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", *GIT_ID, "-C", str(repo), *args], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout.strip()


def _index_state(repo: Path) -> tuple[int, bytes]:
    index = repo / ".git" / "index"
    return index.stat().st_mtime_ns, index.read_bytes()


def _stat_dirty(repo: Path, name: str, seconds: int) -> None:
    """Change a tracked file's timestamp only: git must re-check it, and finds it unchanged."""
    path = repo / name
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns - seconds * 10**9))


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI import open3d_inspector as inspector_module

    query = inspector_module._build_stamp_git
    rows: list = []
    with tempfile.TemporaryDirectory(prefix="guard_0946_") as folder:
        repo = Path(folder)
        _git(repo, "init", "-q")
        (repo / "a.txt").write_text("one\n", encoding="utf-8")
        (repo / "b.txt").write_text("two\n", encoding="utf-8")
        _git(repo, "add", "a.txt", "b.txt")
        _git(repo, "commit", "-q", "-m", "first")
        head = _git(repo, "rev-parse", "--short", "HEAD")
        lock = repo / ".git" / "index.lock"

        # N -- the stamp's query: no lock, the index is not rewritten
        _stat_dirty(repo, "a.txt", 3600)
        before = _index_state(repo)
        answer = query(str(repo), "status", "--porcelain")
        after = _index_state(repo)
        rows.append(["N", answer == "" and after == before and not lock.exists(),
                     f"status answered {answer!r}; index mtime and bytes unchanged: {after == before}; "
                     f"index.lock left: {lock.exists()}"])

        # C -- the control: with optional locks the same query rewrites the index
        before = _index_state(repo)
        plain = _git(repo, "status", "--porcelain")
        after = _index_state(repo)
        rows.append(["C", plain == "" and after != before,
                     f"plain `git status` answered {plain!r} and rewrote the index: {after != before} -- "
                     f"it is a lock-taking query, so N is a real test"])

        # K -- killed at the timeout
        _stat_dirty(repo, "b.txt", 7200)
        try:
            killed = query(str(repo), "status", "--porcelain", timeout=0.0)
            raised = ""
        except Exception as exc:  # the stamp runs at import: it must never raise
            killed, raised = "<raised>", repr(exc)
        rows.append(["K", killed is None and not raised and not lock.exists(),
                     f"a query with no time to run returned {killed!r} (raised: {raised or 'nothing'}); "
                     f"index.lock left: {lock.exists()}"])

        # D -- still truthful
        clean = query(str(repo), "status", "--porcelain")
        (repo / "a.txt").write_text("changed\n", encoding="utf-8")
        edited = query(str(repo), "status", "--porcelain")
        told = query(str(repo), "rev-parse", "--short", "HEAD")
        rows.append(["D", clean == "" and edited == "M a.txt" and told == head and not lock.exists(),
                     f"clean -> {clean!r}; after an edit -> {edited!r}; rev-parse -> {told!r} (the commit {head!r})"])

    # U -- unknown is not clean
    saved_query, saved_stamp = inspector_module._build_stamp_git, inspector_module._RUNNING_BUILD_STAMP
    try:
        inspector_module._RUNNING_BUILD_STAMP = None
        inspector_module._build_stamp_git = lambda repo_dir, *args, **kwargs: (
            None if args[:1] == ("status",) else saved_query(repo_dir, *args, **kwargs))
        unknown = inspector_module._open3d_running_build_stamp()
    finally:
        inspector_module._build_stamp_git = saved_query
        inspector_module._RUNNING_BUILD_STAMP = saved_stamp
    rows.append(["U", bool(unknown.get("git")) and unknown.get("dirty") is None,
                 f"with an unanswered status the stamp is git={unknown.get('git')!r}, dirty={unknown.get('dirty')!r}"])

    # R -- the real checkout
    checkout = Path(inspector_module.__file__).resolve().parent.parent.parent
    real_lock = checkout / ".git" / "index.lock"
    had_lock = real_lock.exists()
    inspector_module._RUNNING_BUILD_STAMP = None
    try:
        stamp = inspector_module._open3d_running_build_stamp()
    finally:
        inspector_module._RUNNING_BUILD_STAMP = saved_stamp
    expected = subprocess.run(["git", "--no-optional-locks", "-C", str(checkout), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=60).stdout.strip()
    rows.append(["R", bool(expected) and stamp.get("git") == expected and (had_lock or not real_lock.exists()),
                 f"stamp git={stamp.get('git')!r} (HEAD {expected!r}), dirty={stamp.get('dirty')!r}; "
                 f"index.lock before/after: {had_lock}/{real_lock.exists()}"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
