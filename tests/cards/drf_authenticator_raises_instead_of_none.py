"""Reducer for drf-authenticator-raises-instead-of-none (needs installed Django + djangorestframework).

Proves two bundled bugs in a custom DRF `BaseAuthentication`:

1. Raising `AuthenticationFailed` when this authenticator cannot find its own
   credentials, instead of returning `None`. DRF's `Request._authenticate()`
   stops the authenticator chain on the first raise (`exceptions.APIException`)
   -- it does not try the remaining authenticators. A legitimate
   session-authenticated request that simply lacks an API key never reaches
   the session authenticator.
2. Treating "the first header not on a deny-list of known names" as
   credentials. Any unrelated header the client happens to send (a tracing
   header, a new proxy header) gets parsed as a bogus credential and rejected,
   again short-circuiting the fallback to session auth.

Django settings can only be configured once per process, so the two
authenticator variants (buggy vs fixed) run in separate subprocesses via
`run(mode)`.

Run directly:
  python3 tests/cards/drf_authenticator_raises_instead_of_none.py buggy_plain_session
  python3 tests/cards/drf_authenticator_raises_instead_of_none.py buggy_unrelated_header
  python3 tests/cards/drf_authenticator_raises_instead_of_none.py buggy_valid_api_key
  python3 tests/cards/drf_authenticator_raises_instead_of_none.py fixed_plain_session
  python3 tests/cards/drf_authenticator_raises_instead_of_none.py fixed_unrelated_header
  python3 tests/cards/drf_authenticator_raises_instead_of_none.py fixed_valid_api_key
"""
import json
import sys

VALID_SESSION_COOKIE = "sessionid=valid-session-token"
EXPECTED_API_KEY = "expected-machine-key"

# Subset of header names a WSGI/DRF test request always carries -- mirrors
# the deny-list a real authenticator uses to skip "boring" headers.
KNOWN_STANDARD_HEADERS = {
    "cookie",
    "accept",
    "accept-encoding",
    "connection",
    "content-length",
    "content-type",
    "host",
    "user-agent",
}


class _MachinePrincipal:
    is_authenticated = True
    username = "machine-integrator"


class _HumanPrincipal:
    is_authenticated = True
    username = "human-session-user"


class SessionLikeAuthentication:
    """Stand-in for SessionAuthentication/JWTAuthentication: trusts a session cookie."""

    def authenticate(self, request):
        if VALID_SESSION_COOKIE not in request.META.get("HTTP_COOKIE", ""):
            return None
        return (_HumanPrincipal(), None)

    def authenticate_header(self, request):
        return "Session"


class BuggyMachineApiKeyAuthentication:
    """As reported: scans all headers, raises instead of returning None."""

    def authenticate(self, request):
        from rest_framework.exceptions import AuthenticationFailed

        username = secret = None
        for k, v in request.headers.items():
            if k.lower() in KNOWN_STANDARD_HEADERS:
                continue
            username, secret = k, v
            break
        if not username:
            raise AuthenticationFailed("no creds")  # BUG: should be `return None`
        if secret != EXPECTED_API_KEY:  # BUG: not constant-time either
            raise AuthenticationFailed("bad key")
        return (_MachinePrincipal(), None)

    def authenticate_header(self, request):
        return "ApiKey"


class FixedMachineApiKeyAuthentication:
    """Safe pattern: look only at this scheme's own named header."""

    def authenticate(self, request):
        import hmac

        from rest_framework.exceptions import AuthenticationFailed

        secret = request.META.get("HTTP_X_API_KEY")
        if secret is None:
            return None  # not our scheme -- let the chain continue
        if not hmac.compare_digest(secret, EXPECTED_API_KEY):
            raise AuthenticationFailed("bad key")
        return (_MachinePrincipal(), None)

    def authenticate_header(self, request):
        return "ApiKey"


SCENARIOS = {
    "plain_session": {},  # valid session cookie only, no api key, no extra headers
    "unrelated_header": {"HTTP_X_REQUEST_ID": "trace-123"},  # valid session + unrelated header
    "valid_api_key": {"HTTP_X_API_KEY": EXPECTED_API_KEY},  # correct api key, no session needed
}


def run(mode: str) -> dict:
    variant, _, scenario_name = mode.partition("_")
    scenario = SCENARIOS[scenario_name]

    import django
    from django.conf import settings

    authenticator = (
        "__main__.BuggyMachineApiKeyAuthentication"
        if variant == "buggy"
        else "__main__.FixedMachineApiKeyAuthentication"
    )

    settings.configure(
        DEBUG=True,
        DATABASES={},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
        ],
        REST_FRAMEWORK={
            "DEFAULT_AUTHENTICATION_CLASSES": (
                authenticator,
                "__main__.SessionLikeAuthentication",
            )
        },
    )
    django.setup()

    from rest_framework.permissions import IsAuthenticated
    from rest_framework.response import Response
    from rest_framework.test import APIRequestFactory
    from rest_framework.views import APIView

    class Protected(APIView):
        permission_classes = [IsAuthenticated]

        def get(self, request):
            return Response({"ok": True, "user": request.user.username})

    view = Protected.as_view()
    factory = APIRequestFactory()
    request = factory.get("/protected/", HTTP_COOKIE=VALID_SESSION_COOKIE, **scenario)
    response = view(request)
    return {
        "mode": mode,
        "status": response.status_code,
        "body": response.data,
    }


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1] if len(sys.argv) > 1 else "buggy_plain_session")))
