"""Reducer for drf-default-permission-unset (needs installed Django + djangorestframework).

Proves that a Django REST Framework project which configures
`DEFAULT_AUTHENTICATION_CLASSES` but never sets `DEFAULT_PERMISSION_CLASSES`
does not fail closed. DRF's own built-in default for that setting is
`AllowAny`, so a view that forgets its own `permission_classes` is silently
public to a request carrying zero credentials.

Each Django settings configuration can only be applied once per process (and
`APIView.permission_classes` is bound to `api_settings.DEFAULT_PERMISSION_CLASSES`
at `rest_framework.views` import time, not re-read per request), so the two
facts below run in separate subprocesses via `run(mode)` -- exactly mirroring
two different real `settings.py` files.

Run directly:
  python3 tests/cards/drf_permission_fail_open.py unset
  python3 tests/cards/drf_permission_fail_open.py fixed
"""
import json
import sys


def run(mode: str) -> dict:
    """mode: 'unset' (no DEFAULT_PERMISSION_CLASSES) or 'fixed' (IsAuthenticated)."""
    import django
    from django.conf import settings

    rest_framework_settings = {"DEFAULT_AUTHENTICATION_CLASSES": ()}
    if mode == "fixed":
        rest_framework_settings["DEFAULT_PERMISSION_CLASSES"] = (
            "rest_framework.permissions.IsAuthenticated",
        )

    settings.configure(
        DEBUG=True,
        DATABASES={},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
        ],
        REST_FRAMEWORK=rest_framework_settings,
    )
    django.setup()

    from rest_framework.response import Response
    from rest_framework.test import APIRequestFactory
    from rest_framework.views import APIView

    class WhoAmI(APIView):
        # forgot permission_classes -- the real-world bug this card is about
        def get(self, request):
            return Response({"ok": True})

    view = WhoAmI.as_view()
    request = APIRequestFactory().get("/whoami/")
    response = view(request)
    return {"mode": mode, "status_code": response.status_code}


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1] if len(sys.argv) > 1 else "unset")))
