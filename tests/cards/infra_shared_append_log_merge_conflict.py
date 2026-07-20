"""Reducer for infra-shared-append-log-merge-conflict (git only, no network/DB).

Proves three facts about a multi-branch pipeline where every branch appends an
entry to the tail of the same tracked file (a changelog / evidence log /
registry):

  1. BASELINE: two branches, each appending a distinct block to the tail of
     the same file, merge cleanly one at a time but the *second* merge is a
     real git CONFLICT -- even though both appends are non-overlapping in
     intent ("keep both blocks" is always correct).

  2. UNION DRIVER FIX: the same two-branch scenario, but the shared file is
     marked `merge=union` in `.gitattributes` from the start. Both appends
     land with no conflict and no data loss.

  3. PER-ENTRY-FILE FIX: instead of one shared file, each branch adds its own
     file under `entries/`. Both merges are clean because the branches never
     touch the same path.

Run:
  python -m pytest tests/cards/test_infra_shared_append_log_merge_conflict.py -q
"""
import subprocess
import tempfile
from pathlib import Path


def _run(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
    )


def _init_repo(cwd):
    _run(["init", "-q", "-b", "main"], cwd)
    _run(["config", "user.email", "t@example.invalid"], cwd)
    _run(["config", "user.name", "test"], cwd)


def _commit_all(cwd, message):
    _run(["add", "-A"], cwd)
    _run(["commit", "-q", "-m", message], cwd)


def baseline_conflict() -> dict:
    """Two branches append to the tail of the same file -> second merge conflicts."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        _init_repo(repo)

        log = repo / "LOG.md"
        log.write_text("# Log\n\n## entry-0\ninit\n")
        _commit_all(repo, "init")

        _run(["checkout", "-q", "-b", "branchA"], repo)
        with log.open("a") as f:
            f.write("## entry-A\nfrom A\n")
        _commit_all(repo, "A appends")

        _run(["checkout", "-q", "main"], repo)
        _run(["checkout", "-q", "-b", "branchB"], repo)
        with log.open("a") as f:
            f.write("## entry-B\nfrom B\n")
        _commit_all(repo, "B appends")

        _run(["checkout", "-q", "main"], repo)
        merge_a = _run(["merge", "-q", "branchA", "--no-edit"], repo)
        merge_b = _run(["merge", "branchB", "--no-edit"], repo)
        status = _run(["status", "--short"], repo)

        return {
            "merge_a_returncode": merge_a.returncode,
            "merge_b_returncode": merge_b.returncode,
            "merge_b_stderr_or_stdout": merge_b.stdout + merge_b.stderr,
            "conflicted": "UU LOG.md" in status.stdout,
        }


def union_driver_fix() -> dict:
    """Same scenario, but `.gitattributes` sets `merge=union` on the shared file."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        _init_repo(repo)

        (repo / ".gitattributes").write_text("LOG.md merge=union\n")
        log = repo / "LOG.md"
        log.write_text("# Log\n\n## entry-0\ninit\n")
        _commit_all(repo, "init")

        _run(["checkout", "-q", "-b", "branchA"], repo)
        with log.open("a") as f:
            f.write("## entry-A\nfrom A\n")
        _commit_all(repo, "A appends")

        _run(["checkout", "-q", "main"], repo)
        _run(["checkout", "-q", "-b", "branchB"], repo)
        with log.open("a") as f:
            f.write("## entry-B\nfrom B\n")
        _commit_all(repo, "B appends")

        _run(["checkout", "-q", "main"], repo)
        merge_a = _run(["merge", "-q", "branchA", "--no-edit"], repo)
        merge_b = _run(["merge", "branchB", "--no-edit"], repo)

        return {
            "merge_a_returncode": merge_a.returncode,
            "merge_b_returncode": merge_b.returncode,
            "final_log": log.read_text(),
        }


def per_entry_file_fix() -> dict:
    """Instead of one shared file, each branch adds its own file under entries/."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        _init_repo(repo)

        entries = repo / "entries"
        entries.mkdir()
        (entries / "0000-init.md").write_text("init\n")
        _commit_all(repo, "init")

        _run(["checkout", "-q", "-b", "branchA"], repo)
        (entries / "2026-07-19-a.md").write_text("from A\n")
        _commit_all(repo, "A adds entry")

        _run(["checkout", "-q", "main"], repo)
        _run(["checkout", "-q", "-b", "branchB"], repo)
        (entries / "2026-07-19-b.md").write_text("from B\n")
        _commit_all(repo, "B adds entry")

        _run(["checkout", "-q", "main"], repo)
        merge_a = _run(["merge", "-q", "branchA", "--no-edit"], repo)
        merge_b = _run(["merge", "branchB", "--no-edit"], repo)

        return {
            "merge_a_returncode": merge_a.returncode,
            "merge_b_returncode": merge_b.returncode,
            "final_files": sorted(p.name for p in entries.iterdir()),
        }


def main():
    b = baseline_conflict()
    print(f"1 baseline: merge A rc={b['merge_a_returncode']}, "
          f"merge B rc={b['merge_b_returncode']}, conflicted={b['conflicted']}")

    u = union_driver_fix()
    print(f"2 union driver: merge A rc={u['merge_a_returncode']}, "
          f"merge B rc={u['merge_b_returncode']}, "
          f"both blocks present={'entry-A' in u['final_log'] and 'entry-B' in u['final_log']}")

    p = per_entry_file_fix()
    print(f"3 per-entry-file: merge A rc={p['merge_a_returncode']}, "
          f"merge B rc={p['merge_b_returncode']}, files={p['final_files']}")


if __name__ == "__main__":
    main()
