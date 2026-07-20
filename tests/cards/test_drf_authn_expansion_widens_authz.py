"""Verifier for drf-authn-expansion-widens-authz (needs installed Django + djangorestframework).

Run:
  python -m pytest tests/cards/test_drf_authn_expansion_widens_authz.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

REDUCER = Path(__file__).parent / "drf_authn_expansion_widens_authz.py"


def _run(mode: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(REDUCER), mode],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_narrow_authenticators_reject_machine_key():
    # before the machine authenticator exists, a request carrying only the
    # machine API key resolves to no principal -> IsAuthenticated denies it
    r = _run("narrow")
    assert r["status_with_machine_key"] in (401, 403)
    assert r["status_without_any_credential"] in (401, 403)


def test_widened_authenticators_let_machine_key_through_unchanged_view():
    # same view, same permission_classes=[IsAuthenticated]; only the global
    # authenticator list grew -> the machine principal now satisfies the
    # staff-only check it was never meant to reach
    r = _run("widened")
    assert r["status_with_machine_key"] == 200
    # a request with zero credentials must still be denied -- this is not
    # AllowAny, the gap is specific to the newly recognized principal
    assert r["status_without_any_credential"] in (401, 403)
