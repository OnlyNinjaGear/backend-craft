"""Verifier for drf-default-permission-unset (needs installed Django + djangorestframework).

Run:
  python -m pytest tests/cards/test_drf_permission_fail_open.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

REDUCER = Path(__file__).parent / "drf_permission_fail_open.py"


def _run(mode: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(REDUCER), mode],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_unset_default_permission_classes_fails_open():
    # no DEFAULT_PERMISSION_CLASSES in REST_FRAMEWORK -> DRF's own default is
    # AllowAny, so a view with no permission_classes is public with zero creds
    r = _run("unset")
    assert r["status_code"] == 200


def test_explicit_default_permission_classes_fails_closed():
    # same view, same zero-credential request; only the project-wide default
    # changed -> the forgotten permission_classes line now denies by default
    r = _run("fixed")
    assert r["status_code"] in (401, 403)
