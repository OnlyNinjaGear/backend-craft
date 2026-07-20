"""Verifier for drf-default-throttle-unset (needs installed Django + djangorestframework).

Run:
  python -m pytest tests/cards/test_drf_default_throttle_unset.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

REDUCER = Path(__file__).parent / "drf_default_throttle_unset.py"


def _run(mode: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(REDUCER), mode],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_no_default_throttle_classes_allows_unlimited_login_attempts():
    # no DEFAULT_THROTTLE_CLASSES in REST_FRAMEWORK -> DRF's own default is
    # [] (no throttling at all); ten rapid POSTs to the login endpoint from
    # the same caller all succeed -- unrestricted credential brute force
    r = _run("unset")
    assert r["login_statuses"] == [200] * 10


def test_shared_generic_anon_scope_conflates_login_with_unrelated_reads():
    # only the generic project-wide AnonRateThrottle scope is configured, no
    # scope of its own for the login endpoint -- three unrelated reads eat
    # into the same budget, so the attacker's very first three login
    # attempts (not the tenth, not the hundredth) already 429
    r = _run("shared")
    assert r["read_statuses"] == [200, 200, 200]
    assert r["login_statuses"] == [200, 200, 429]


def test_dedicated_login_scope_is_independent_of_read_traffic():
    # login endpoint has its own ScopedRateThrottle scope, distinct from the
    # scope guarding the unrelated read endpoint
    r = _run("dedicated")
    # exhausting the read scope does not touch the login budget
    assert r["read_statuses"] == [200, 200, 200, 200, 200]
    # login enforces its own strict cap regardless of read traffic
    assert r["login_statuses"] == [200, 200, 200, 429]
