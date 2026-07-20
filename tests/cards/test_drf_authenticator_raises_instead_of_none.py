"""Verifier for drf-authenticator-raises-instead-of-none (needs installed Django + djangorestframework).

Run:
  python -m pytest tests/cards/test_drf_authenticator_raises_instead_of_none.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

REDUCER = Path(__file__).parent / "drf_authenticator_raises_instead_of_none.py"


def _run(mode: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(REDUCER), mode],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_buggy_authenticator_401s_a_valid_session_with_no_api_key():
    # a legitimate session-authenticated request that simply has no API key
    # never reaches SessionLikeAuthentication -- the buggy authenticator
    # raises instead of returning None, killing the fallback
    r = _run("buggy_plain_session")
    assert r["status"] == 401


def test_buggy_authenticator_401s_a_valid_session_over_an_unrelated_header():
    # an unrelated header (e.g. a tracing header) gets parsed as bogus
    # credentials and rejected, again blocking the valid session fallback
    r = _run("buggy_unrelated_header")
    assert r["status"] == 401


def test_buggy_authenticator_still_accepts_its_own_valid_key():
    # the happy path is unaffected -- the bug is isolated to the fallback path
    r = _run("buggy_valid_api_key")
    assert r["status"] == 200


def test_fixed_authenticator_lets_valid_session_through_with_no_api_key():
    # safe pattern: returning None (not raising) lets the chain continue to
    # the session authenticator
    r = _run("fixed_plain_session")
    assert r["status"] == 200


def test_fixed_authenticator_ignores_unrelated_headers():
    # safe pattern: only looks at its own named header (X-Api-Key), so an
    # unrelated header cannot be mistaken for credentials
    r = _run("fixed_unrelated_header")
    assert r["status"] == 200


def test_fixed_authenticator_still_accepts_its_own_valid_key():
    r = _run("fixed_valid_api_key")
    assert r["status"] == 200
