"""Reducer for drf-default-throttle-unset (needs installed Django + djangorestframework).

Proves two distinct failures in one mechanism family:

1. `unset` -- a Django REST Framework project that never sets
   `DEFAULT_THROTTLE_CLASSES` (DRF's own built-in default is `[]`, i.e. no
   throttling runs at all) lets a token/login endpoint accept unlimited
   rapid requests: unrestricted credential brute force.
2. `shared` -- a project that *does* configure a project-wide throttle, but
   only the generic `AnonRateThrottle` scope, shared by every anonymous
   route. The login endpoint has no throttle scope of its own, so its
   request budget is conflated with unrelated anonymous read traffic:
   ordinary browsing on another endpoint can exhaust the very budget that
   was supposed to cap login attempts, and vice versa.
3. `dedicated` -- the fix: the login endpoint gets its own `ScopedRateThrottle`
   scope, independent of the scope guarding unrelated reads. Exhausting the
   read scope does not touch the login budget, and the login scope enforces
   its own strict cap regardless of read traffic.

Each Django settings configuration can only be applied once per process, so
the three variants run in separate subprocesses via `run(mode)`.

Run directly:
  python3 tests/cards/drf_default_throttle_unset.py unset
  python3 tests/cards/drf_default_throttle_unset.py shared
  python3 tests/cards/drf_default_throttle_unset.py dedicated
"""
import json
import sys


def run(mode: str) -> dict:
    """mode: 'unset', 'shared', or 'dedicated'."""
    import django
    from django.conf import settings

    rest_framework_settings = {}
    if mode == "shared":
        rest_framework_settings = {
            "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
            "DEFAULT_THROTTLE_RATES": {"anon": "5/min"},
        }
    elif mode == "dedicated":
        rest_framework_settings = {
            "DEFAULT_THROTTLE_RATES": {"reads": "5/min", "login": "3/min"},
        }

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
    from rest_framework.throttling import ScopedRateThrottle
    from rest_framework.views import APIView

    class ListView(APIView):
        # an unrelated, cheap read endpoint
        if mode == "dedicated":
            throttle_classes = [ScopedRateThrottle]
            throttle_scope = "reads"

        def get(self, request):
            return Response({"items": []})

    class LoginView(APIView):
        # the token/login endpoint -- the bug this card is about
        if mode == "dedicated":
            throttle_classes = [ScopedRateThrottle]
            throttle_scope = "login"

        def post(self, request):
            return Response({"token": "fake"})

    list_view = ListView.as_view()
    login_view = LoginView.as_view()
    factory = APIRequestFactory()
    ip = "203.0.113.7"

    def hit_list():
        req = factory.get("/list/", REMOTE_ADDR=ip)
        return list_view(req).status_code

    def hit_login():
        req = factory.post("/login/", {}, REMOTE_ADDR=ip)
        return login_view(req).status_code

    if mode == "unset":
        login_statuses = [hit_login() for _ in range(10)]
        return {"mode": mode, "login_statuses": login_statuses}

    if mode == "shared":
        # unrelated read traffic first, consuming most of the shared budget
        read_statuses = [hit_list() for _ in range(3)]
        # the attacker's very first three login attempts
        login_statuses = [hit_login() for _ in range(3)]
        return {
            "mode": mode,
            "read_statuses": read_statuses,
            "login_statuses": login_statuses,
        }

    if mode == "dedicated":
        # exhaust the reads scope entirely
        read_statuses = [hit_list() for _ in range(5)]
        # login scope is untouched by read traffic
        login_statuses = [hit_login() for _ in range(4)]
        return {
            "mode": mode,
            "read_statuses": read_statuses,
            "login_statuses": login_statuses,
        }

    raise ValueError(f"unknown mode: {mode}")


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1] if len(sys.argv) > 1 else "unset")))
