"""Verifier for infra-shared-append-log-merge-conflict (git only, no network/DB).

Run:
  python -m pytest tests/cards/test_infra_shared_append_log_merge_conflict.py -q
"""
from infra_shared_append_log_merge_conflict import (  # noqa: E402
    baseline_conflict,
    per_entry_file_fix,
    union_driver_fix,
)


def test_baseline_second_append_merge_conflicts():
    r = baseline_conflict()
    assert r["merge_a_returncode"] == 0
    assert r["merge_b_returncode"] != 0
    assert r["conflicted"] is True


def test_union_merge_driver_keeps_both_appends_with_no_conflict():
    r = union_driver_fix()
    assert r["merge_a_returncode"] == 0
    assert r["merge_b_returncode"] == 0
    assert "entry-A" in r["final_log"]
    assert "entry-B" in r["final_log"]


def test_per_entry_file_layout_merges_cleanly():
    r = per_entry_file_fix()
    assert r["merge_a_returncode"] == 0
    assert r["merge_b_returncode"] == 0
    assert r["final_files"] == ["0000-init.md", "2026-07-19-a.md", "2026-07-19-b.md"]
