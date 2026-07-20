"""Reducer for drf-authn-expansion-widens-authz (needs installed Django + djangorestframework).

Proves that adding a new authentication class to a Django REST Framework
project's `DEFAULT_AUTHENTICATION_CLASSES` silently widens every view guarded
only by `IsAuthenticated`. The view's `permission_classes` never changes; only
the set of principals that can satisfy "is authenticated" grows.

Django settings can only be configured once per process, so the two facts
below (before/after the new authenticator was added) run in separate
subprocesses via `run(mode)` -- exactly mirroring two different real
`settings.py` files.

Run directly:
  python3 tests/cards/drf_authn_expansion_widens_authz.py narrow
  python3 tests/cards/drf_authn_expansion_widens_authz.py widened
"""
import json
import sys


class _MachinePrincipal:
    # Duck-types just enough of a Django user for IsAuthenticated to pass.
    is_authenticated = True
    username = "machine-integrator"


class MachineApiKeyAuthentication:
    """Stand-in for an API-key authenticator added later for a machine integrator."""

    def authenticate(self, request):
        key = request.META.get("HTTP_X_API_KEY")
        if key != "expected-machine-key":
            return None
        return (_MachinePrincipal(), None)

    def authenticate_header(self, request):
        return "ApiKey"


def run(mode: str) -> dict:
    """mode: 'narrow' (no machine authenticator) or 'widened' (machine API key authenticator added)."""
    import django
    from django.conf import settings

    # DRF resolves DEFAULT_AUTHENTICATION_CLASSES entries as dotted import
    # paths (even when this module is a script, __name__ == "__main__"),
    # mirroring how a real settings.py names the class.
    authenticators = ("__main__.MachineApiKeyAuthentication",) if mode == "widened" else ()

    settings.configure(
        DEBUG=True,
        DATABASES={},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
        ],
        REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": authenticators},
    )
    django.setup()

    from rest_framework.permissions import IsAuthenticated
    from rest_framework.response import Response
    from rest_framework.test import APIRequestFactory
    from rest_framework.views import APIView

    class ProductTypeAdmin(APIView):
        permission_classes = [IsAuthenticated]  # meant for staff; never touched

        def get(self, request):
            return Response({"ok": True})

    view = ProductTypeAdmin.as_view()
    factory = APIRequestFactory()
    with_key = view(factory.get("/product-types/", HTTP_X_API_KEY="expected-machine-key"))
    without_key = view(factory.get("/product-types/"))
    return {
        "mode": mode,
        "status_with_machine_key": with_key.status_code,
        "status_without_any_credential": without_key.status_code,
    }


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1] if len(sys.argv) > 1 else "narrow")))
