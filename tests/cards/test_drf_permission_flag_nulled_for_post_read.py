"""Verifier for drf-permission-flag-nulled-for-post-read (needs installed
Django + djangorestframework).

Run:
  python -m pytest tests/cards/test_drf_permission_flag_nulled_for_post_read.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

REDUCER = Path(__file__).parent / "drf_permission_flag_nulled_for_post_read.py"


def _run() -> dict:
    result = subprocess.run(
        [sys.executable, str(REDUCER)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_buggy_mixin_lets_unprivileged_principal_through_on_misclassified_read():
    # nulling permission_flag for by_key/bulk_get removes the check entirely --
    # a principal with none of the view's permissions still gets 200
    r = _run()
    assert r["buggy_by_key_no_perms"] == 200


def test_buggy_mixin_still_guards_the_write_action():
    # the write branch is untouched by the bug -- same unprivileged principal
    # is denied there, which is what makes the read-branch bypass easy to miss
    r = _run()
    assert r["buggy_moderate_no_perms"] == 403


def test_fixed_mixin_denies_unprivileged_principal_on_the_read_action():
    # explicit action -> permission map: by_key still requires can_read
    r = _run()
    assert r["fixed_by_key_no_perms"] == 403


def test_fixed_mixin_allows_read_permission_on_read_action_only():
    r = _run()
    assert r["fixed_by_key_read_only"] == 200
    assert r["fixed_moderate_read_only"] == 403
