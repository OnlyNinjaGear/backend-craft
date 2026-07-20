"""Reducer for drf-permission-flag-nulled-for-post-read (needs installed
Django + djangorestframework).

Proves that "fixing" a method-based authorization mixin by nulling its guard
attribute for misclassified read-over-POST actions removes the permission
check entirely, instead of mapping those actions to the permission they
actually need.

Same Django settings, same permission class, same principals -- only the
viewset's `check_permissions` override differs (buggy: nulls the flag; fixed:
maps every action to its own required permission). Both variants fit in one
process since neither touches `django.conf.settings`.

Run directly:
  python3 tests/cards/drf_permission_flag_nulled_for_post_read.py
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

    from rest_framework.permissions import BasePermission, IsAuthenticated
    from rest_framework.response import Response
    from rest_framework.test import APIRequestFactory, force_authenticate
    from rest_framework.viewsets import ViewSet

    class _Principal:
        is_authenticated = True

        def __init__(self, perms):
            self._perms = set(perms)

        def has_perm(self, perm):
            return perm in self._perms

    class HasPermissionFlag(BasePermission):
        """Mirrors the real mixin's guard: no flag means no check."""

        def has_permission(self, request, view):
            flag = getattr(view, "permission_flag", None)
            if not flag:  # the bug surface: falsy/None flag == open
                return True
            return request.user.has_perm(flag)

    class _Base(ViewSet):
        permission_classes = [IsAuthenticated, HasPermissionFlag]
        permission_flag = "can_moderate"

        def by_key(self, request):  # semantically a read, exposed over POST
            return Response({"ok": True})

        def bulk_get(self, request):  # same
            return Response({"ok": True})

        def moderate(self, request):  # a genuine write action
            return Response({"ok": True})

    class BuggyImageLinkViewSet(_Base):
        def check_permissions(self, request):
            if self.action in {"by_key", "bulk_get"}:
                self.permission_flag = None  # disables the check, doesn't fix it
                super().check_permissions(request)
                self.permission_flag = "can_moderate"
                return
            super().check_permissions(request)

    class FixedImageLinkViewSet(_Base):
        ACTION_PERMISSION = {
            "by_key": "can_read",
            "bulk_get": "can_read",
            "moderate": "can_moderate",
        }

        def check_permissions(self, request):
            self.permission_flag = self.ACTION_PERMISSION[self.action]
            super().check_permissions(request)

    factory = APIRequestFactory()
    no_perms = _Principal(perms=())
    read_only = _Principal(perms=("can_read",))

    def call(viewset_cls, action, user):
        view = viewset_cls.as_view({"post": action})
        request = factory.post(f"/image-links/{action}/")
        force_authenticate(request, user=user)
        return view(request).status_code

    return {
        "buggy_by_key_no_perms": call(BuggyImageLinkViewSet, "by_key", no_perms),
        "buggy_moderate_no_perms": call(BuggyImageLinkViewSet, "moderate", no_perms),
        "fixed_by_key_no_perms": call(FixedImageLinkViewSet, "by_key", no_perms),
        "fixed_by_key_read_only": call(FixedImageLinkViewSet, "by_key", read_only),
        "fixed_moderate_read_only": call(FixedImageLinkViewSet, "moderate", read_only),
    }


if __name__ == "__main__":
    print(json.dumps(run()))
