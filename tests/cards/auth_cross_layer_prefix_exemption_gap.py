"""Reducer for auth-cross-layer-prefix-exemption-gap (needs installed Django +
djangorestframework).

Proves that a global auth middleware exempting a URL prefix -- trusting the
framework mounted there (DRF) to authenticate every request itself -- leaves a
gap for any *non-framework* handler registered on the same prefix. The plain
handler inherits neither the middleware check (the prefix is exempted) nor the
framework's per-view auth (it never runs through DRF's dispatch), so it ships
fully unauthenticated while sibling DRF views on the same prefix, and plain
views outside the prefix, stay protected.

The middleware, the plain handler, and a real DRF view all run through one
`get_response` dispatcher standing in for the URL resolver -- this is the same
callable shape Django's own resolver has, so the middleware's `__call__`
behaves exactly as it would wired into `MIDDLEWARE`.

Run directly:
  python3 tests/cards/auth_cross_layer_prefix_exemption_gap.py
"""
import json


def run() -> dict:
    import django
    from django.conf import settings

    settings.configure(
        DEBUG=True,
        DATABASES={},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
        ],
        REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ()},
    )
    django.setup()

    from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
    from django.test import RequestFactory
    from rest_framework.permissions import IsAuthenticated
    from rest_framework.response import Response
    from rest_framework.views import APIView

    class AuthEverywhereExceptApi:
        """Mirrors the real middleware: trusts DRF to authenticate anything under /api/."""

        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            if request.path.startswith("/api/"):
                return self.get_response(request)
            if not getattr(request.user, "is_authenticated", False):
                return HttpResponseRedirect("/login/")
            return self.get_response(request)

    def list_internal_files(request):  # plain Django view, NOT a DRF view, under /api/
        return JsonResponse({"files": ["payroll_export.csv", "ssn_batch.csv"]})

    def list_internal_files_fixed(request):  # same handler, checks auth itself
        if not getattr(request.user, "is_authenticated", False):
            return HttpResponseForbidden()
        return JsonResponse({"files": ["payroll_export.csv", "ssn_batch.csv"]})

    class ProductTypeApi(APIView):  # a real DRF view under /api/, authenticates itself
        permission_classes = [IsAuthenticated]

        def get(self, request):
            return Response({"ok": True})

    def dashboard(request):  # a plain page NOT under /api/, relies on the middleware
        return JsonResponse({"ok": True})

    product_type_view = ProductTypeApi.as_view()

    def dispatch(request):
        routes = {
            "/api/check-files/": list_internal_files,
            "/api/check-files-fixed/": list_internal_files_fixed,
            "/api/product-types/": product_type_view,
            "/dashboard/": dashboard,
        }
        return routes[request.path](request)

    middleware = AuthEverywhereExceptApi(dispatch)
    factory = RequestFactory()

    class _Anon:
        is_authenticated = False

    def call(path):
        request = factory.get(path)
        request.user = _Anon()
        return middleware(request).status_code

    return {
        "anon_hits_plain_view_under_exempted_prefix": call("/api/check-files/"),
        "anon_hits_plain_view_outside_exempted_prefix": call("/dashboard/"),
        "anon_hits_drf_view_under_exempted_prefix": call("/api/product-types/"),
        "anon_hits_fixed_plain_view_under_exempted_prefix": call(
            "/api/check-files-fixed/"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run()))
