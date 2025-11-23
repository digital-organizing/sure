from functools import wraps
from typing import Any, Optional

from django.core.exceptions import PermissionDenied as Unauthorized
from django.http import HttpRequest
from ninja.security.apikey import APIKeyCookie


class Auth2FaOrTrusted(APIKeyCookie):
    "Reusing Django session authentication"

    def authenticate(self, request: HttpRequest, key: Optional[str]) -> Optional[Any]:
        return request.user.is_authenticated and (
            request.user.is_verified() or request.agent.is_trusted
        )


auth_2fa_or_trusted = Auth2FaOrTrusted()


class Auth2FA(APIKeyCookie):
    "Reusing Django session authentication"

    def authenticate(self, request: HttpRequest, key: Optional[str]) -> Optional[Any]:
        if request.user.is_authenticated and request.user.is_verified():
            return request.user

        return None


auth_2fa = Auth2FA()


def require_2fa(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not auth_2fa(request):
            raise Unauthorized("2FA required")
        return view_func(request, *args, **kwargs)

    return _wrapped_view
