"""Verifier for auth-cross-layer-prefix-exemption-gap (needs installed Django +
djangorestframework).

Run:
  python -m pytest tests/cards/test_auth_cross_layer_prefix_exemption_gap.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

REDUCER = Path(__file__).parent / "auth_cross_layer_prefix_exemption_gap.py"


def _run() -> dict:
    result = subprocess.run(
        [sys.executable, str(REDUCER)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_plain_view_under_exempted_prefix_ships_unauthenticated():
    # the middleware steps aside for /api/*, and this handler is not a DRF
    # view, so nothing ever checks the anonymous caller
    r = _run()
    assert r["anon_hits_plain_view_under_exempted_prefix"] == 200


def test_middleware_still_protects_routes_outside_the_exempted_prefix():
    # same middleware, same anonymous caller -- outside /api/ it redirects,
    # proving the gap is specific to the exemption, not a broken middleware
    r = _run()
    assert r["anon_hits_plain_view_outside_exempted_prefix"] == 302


def test_real_drf_view_under_the_same_prefix_stays_protected():
    # the middleware's assumption ("DRF authenticates under /api/") holds for
    # actual DRF views -- the gap is specific to non-framework handlers
    r = _run()
    assert r["anon_hits_drf_view_under_exempted_prefix"] == 403


def test_fixed_plain_view_checks_auth_itself_and_is_protected():
    # safe pattern: the plain handler stops trusting the prefix and checks
    # request.user.is_authenticated itself
    r = _run()
    assert r["anon_hits_fixed_plain_view_under_exempted_prefix"] == 403
